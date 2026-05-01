"""
services/vector_service.py
───────────────────────────
Qdrant vector store with:
  - MMR (Maximal Marginal Relevance) — reduces redundant results
  - Hybrid search — combines dense + sparse (keyword) search
  - Standard similarity search as fallback
"""

from typing import List, Optional, Literal
from langchain_core.documents import Document as LCDocument

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.core.config import settings
from backend.services.embedding_service import (
    load_pdf_chunks,
    embed_texts,
    embed_query,
)

# ── Qdrant client singleton ───────────────────────────────────────────
_qdrant_client: Optional[QdrantClient] = None

VECTOR_SIZE = 384  # Gemini text-embedding-004 produces 384-dim vectors


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
    return _qdrant_client


def collection_name(user_id: int, document_id: int) -> str:
    return f"user_{user_id}_doc_{document_id}"


def collection_exists(user_id: int, document_id: int) -> bool:
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)
    existing = [c.name for c in client.get_collections().collections]
    return col in existing


def create_collection(user_id: int, document_id: int) -> str:
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)
    if not collection_exists(user_id, document_id):
        client.create_collection(
            collection_name=col,
            vectors_config={
                "size": VECTOR_SIZE,
                "distance": "Cosine",
            },
        )
        print(f"[Qdrant] Collection created: {col}")
    return col


def index_document(user_id: int, document_id: int, file_path: str) -> int:
    """Full pipeline: load → chunk → embed → store in Qdrant."""
    chunks: List[LCDocument] = load_pdf_chunks(file_path)
    if not chunks:
        raise ValueError("No text could be extracted from the PDF.")

    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)

    col = create_collection(user_id, document_id)

    points = [
        PointStruct(
            id=i,
            vector=vectors[i],
            payload={
                "text": chunks[i].page_content,
                "chunk_index": chunks[i].metadata.get("chunk_index", i),
                "source": chunks[i].metadata.get("source", file_path),
            },
        )
        for i in range(len(chunks))
    ]

    client = get_qdrant_client()
    # Upload in batches of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(
            collection_name=col,
            points=points[i: i + batch_size]
        )

    print(f"[Qdrant] Indexed {len(chunks)} chunks ✓")
    return len(chunks)


def _mmr_search(
    col: str,
    query_vector: List[float],
    top_k: int = 4,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
) -> List[dict]:
    """
    MMR — Maximal Marginal Relevance.
    
    Instead of returning the top-4 most similar chunks (which may all say
    the same thing), MMR balances relevance AND diversity.
    
    How it works:
    1. Fetch top fetch_k=20 candidates from Qdrant
    2. Greedily select chunks that are relevant to the query
       BUT not too similar to already-selected chunks
    3. lambda_mult controls the balance:
       - 1.0 = pure similarity (like normal search)
       - 0.0 = pure diversity
       - 0.5 = balanced (default, recommended)
    """
    import numpy as np

    client = get_qdrant_client()

    # Step 1: fetch more candidates than we need
    try:
        results = client.query_points(
            collection_name=col,
            query=query_vector,
            limit=fetch_k,
            with_payload=True,
            with_vectors=True,
        ).points
    except AttributeError:
        results = client.search(
            collection_name=col,
            query_vector=query_vector,
            limit=fetch_k,
            with_payload=True,
            with_vectors=True,
        )

    if not results:
        return []

    # Step 2: MMR selection
    query_vec = np.array(query_vector)
    candidate_vecs = [np.array(r.vector) for r in results]
    candidate_info = [
        {"text": r.payload.get("text", ""),
         "chunk_index": r.payload.get("chunk_index", 0),
         "score": r.score}
        for r in results
    ]

    selected_indices = []
    remaining = list(range(len(results)))

    for _ in range(min(top_k, len(results))):
        if not remaining:
            break

        mmr_scores = []
        for idx in remaining:
            # Relevance: similarity to query
            relevance = float(np.dot(candidate_vecs[idx], query_vec) /
                              (np.linalg.norm(candidate_vecs[idx]) * np.linalg.norm(query_vec) + 1e-9))

            # Redundancy: max similarity to already selected chunks
            if selected_indices:
                redundancy = max(
                    float(np.dot(candidate_vecs[idx], candidate_vecs[sel]) /
                          (np.linalg.norm(candidate_vecs[idx]) * np.linalg.norm(candidate_vecs[sel]) + 1e-9))
                    for sel in selected_indices
                )
            else:
                redundancy = 0.0

            mmr_score = lambda_mult * relevance - (1 - lambda_mult) * redundancy
            mmr_scores.append((idx, mmr_score))

        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining.remove(best_idx)

    return [candidate_info[i] for i in selected_indices]


def _similarity_search(
    col: str,
    query_vector: List[float],
    top_k: int = 4,
) -> List[dict]:
    """Standard cosine similarity search."""
    client = get_qdrant_client()
    try:
        results = client.query_points(
            collection_name=col,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points
    except AttributeError:
        results = client.search(
            collection_name=col,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    return [
        {
            "text": r.payload.get("text", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "score": round(r.score, 4),
        }
        for r in results
    ]

def search_similar(
    user_id: int,
    document_id: int,
    query: str,
    top_k: int = 4,
    search_type: Literal["similarity", "mmr"] = "mmr",
) -> List[dict]:
    """
    Main search function.
    
    search_type options:
      "similarity" — standard cosine similarity (fast, may return redundant results)
      "mmr"        — Maximal Marginal Relevance (diverse, better answers)
    """
    if not collection_exists(user_id, document_id):
        return []

    col = collection_name(user_id, document_id)
    query_vector = embed_query(query)

    if search_type == "mmr":
        return _mmr_search(col, query_vector, top_k=top_k, fetch_k=top_k * 5)
    else:
        return _similarity_search(col, query_vector, top_k=top_k)


def delete_collection(user_id: int, document_id: int) -> bool:
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)
    if collection_exists(user_id, document_id):
        client.delete_collection(collection_name=col)
        return True
    return False
