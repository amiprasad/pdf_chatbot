"""
services/embedding_service.py
──────────────────────────────
Uses HuggingFace Inference API for embeddings.
Model: sentence-transformers/all-MiniLM-L6-v2
Uses Google Gemini API for embeddings — works on any server, no local model needed.
Uses PyMuPDF (fitz) directly for text extraction
"""

import time
from typing import List
from pathlib import Path

import requests as req
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

from backend.core.config import settings

HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"


def _hf_headers():
    return {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}


def load_pdf_chunks(file_path: str) -> List[LCDocument]:
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    print(f"[Extraction] Reading: {Path(file_path).name}")
    all_text = []

    # Primary: PyMuPDF
    try:
        import fitz
        doc = fitz.open(file_path)
        print(f"[Extraction] PDF has {len(doc)} pages")

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            page_text = []
            for block in blocks:
                text = block[4].strip()
                if block[6] == 0 and text:  # text blocks only
                    page_text.append(text)
            if page_text:
                all_text.append(f"[Page {page_num + 1}]\n" + "\n".join(page_text))

        doc.close()
        full_text = "\n\n".join(all_text)
        print(f"[Extraction] Extracted {len(full_text)} characters ✓")

    except Exception as e:
        print(f"[Extraction] PyMuPDF failed: {e}")
        full_text = ""

    # Fallback: pypdf
    if len(full_text.strip()) < 200:
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            texts = [f"[Page {i+1}]\n{p.page_content}"
                     for i, p in enumerate(pages) if p.page_content.strip()]
            full_text = "\n\n".join(texts)
            print(f"[Extraction] pypdf: {len(full_text)} chars ✓")
        except Exception as e:
            print(f"[Extraction] pypdf failed: {e}")

    if len(full_text.strip()) < 100:
        raise ValueError("Could not extract text. Use a PDF with selectable text.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_doc = LCDocument(
        page_content=full_text,
        metadata={"source": file_path}
    )
    chunks = splitter.split_documents([raw_doc])
    chunks = [c for c in chunks if len(c.page_content.strip()) > 30]

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    print(f"[Extraction] {len(chunks)} chunks ready ✓")
    return chunks


def _embed_batch(texts: List[str]) -> List[List[float]]:
    """Call HuggingFace API for one batch with retry logic."""
    for attempt in range(5):
        response = req.post(
            HF_API_URL,
            headers=_hf_headers(),
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            wait = 20 * (attempt + 1)
            print(f"[Embedding] Model loading, waiting {wait}s...")
            time.sleep(wait)
        elif response.status_code == 429:
            print("[Embedding] Rate limited, waiting 30s...")
            time.sleep(30)
        else:
            raise ValueError(f"HuggingFace API error {response.status_code}: {response.text}")

    raise ValueError("HuggingFace API failed after 5 attempts.")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed all chunks in batches of 32."""
    all_vectors = []
    batch_size = 32
    total_batches = (len(texts) - 1) // batch_size + 1

    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        batch_num = i // batch_size + 1
        print(f"[Embedding] Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
        vectors = _embed_batch(batch)
        all_vectors.extend(vectors)

    print(f"[Embedding] Done — {len(all_vectors)} vectors ✓")
    return all_vectors


def embed_query(query: str) -> List[float]:
    """Embed a single search query."""
    result = _embed_batch([query])
    return result[0]