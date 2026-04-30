"""
services/vector_service.py
───────────────────────────
All Qdrant vector database operations:
  - create_collection      : make a new collection for a document
  - index_document         : embed PDF chunks and store in Qdrant
  - search_similar         : retrieve top-k similar chunks for a query
  - delete_collection      : remove all vectors for a document (on PDF delete)
  - collection_exists      : check if already indexed

Each user-document pair gets its own Qdrant collection:
  Collection name = "user_{user_id}_doc_{document_id}"
  This gives perfect user-level data isolation.
"""

from typing import List, Optional
from langchain_core.documents import Document as LCDocument

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from backend.core.config import settings
from backend.services.embedding_service import (
    load_pdf_chunks,
    get_embedding_model,
    embed_texts,
    embed_query,
)

# ── Qdrant client (local file-based, no server needed) ───────────────
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Singleton Qdrant client using local file storage."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(path=settings.QDRANT_PATH)
    return _qdrant_client


def collection_name(user_id: int, document_id: int) -> str:
    return f"user_{user_id}_doc_{document_id}"


# ── Core CRUD operations ─────────────────────────────────────────────

def collection_exists(user_id: int, document_id: int) -> bool:
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)
    existing = [c.name for c in client.get_collections().collections]
    return col in existing


def create_collection(user_id: int, document_id: int, vector_size: int = 384) -> str:
    """
    Create a new Qdrant collection for this user+document.
    Gemini 'embedding-001' produces 768-dimension vectors.
    """
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)

    if not collection_exists(user_id, document_id):
        client.create_collection(
            collection_name=col,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    return col


def index_document(user_id: int, document_id: int, file_path: str) -> int:
    """
    Full pipeline: load PDF → chunk → embed → store in Qdrant.
    Returns the number of chunks indexed.
    """
    # 1. Load and chunk the PDF
    chunks: List[LCDocument] = load_pdf_chunks(file_path)
    if not chunks:
        raise ValueError("No text could be extracted from the PDF.")

    # 2. Embed all chunks (batch call)
    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)

    # 3. Create the collection (768 dims for Gemini embedding-001)
    col = create_collection(user_id, document_id, vector_size=len(vectors[0]))

    # 4. Build Qdrant points and upload
    points = [
        PointStruct(
            id=i,
            vector=vectors[i],
            payload={
                "text": chunks[i].page_content,
                "page": chunks[i].metadata.get("page", 0),
                "source": chunks[i].metadata.get("source", file_path),
            },
        )
        for i in range(len(chunks))
    ]
    client = get_qdrant_client()
    client.upsert(collection_name=col, points=points)

    return len(chunks)


def search_similar(
    user_id: int,
    document_id: int,
    query: str,
    top_k: int = 4,
) -> List[dict]:
    if not collection_exists(user_id, document_id):
        return []

    col = collection_name(user_id, document_id)
    query_vector = embed_query(query)
    client = get_qdrant_client()

    # qdrant-client v1.7+ uses query_points instead of search
    try:
        from qdrant_client.models import QueryRequest
        results = client.query_points(
            collection_name=col,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points
    except AttributeError:
        # Fallback for older qdrant-client versions
        results = client.search(
            collection_name=col,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    return [
        {
            "text": hit.payload.get("text", ""),
            "page": hit.payload.get("page", 0),
            "score": round(hit.score, 4),
        }
        for hit in results
    ]


def delete_collection(user_id: int, document_id: int) -> bool:
    """
    Delete the Qdrant collection for this document.
    Called when a user deletes a PDF — cleans up all vectors.
    Returns True if deleted, False if it didn't exist.
    """
    client = get_qdrant_client()
    col = collection_name(user_id, document_id)

    if collection_exists(user_id, document_id):
        client.delete_collection(collection_name=col)
        return True
    return False