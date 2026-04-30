"""
services/embedding_service.py
──────────────────────────────
Uses PyMuPDF (fitz) directly for text extraction — most reliable
for academic/research PDFs with mixed content.
Uses local sentence-transformers for embeddings.
"""

from typing import List
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument
from backend.core.config import settings

# ── Local embedding model ─────────────────────────────────────────────
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("[Embedding] Loading local model...")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Embedding] Model ready ✓")
    return _embedding_model


def load_pdf_chunks(file_path: str) -> List[LCDocument]:
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    print(f"[Extraction] Reading: {Path(file_path).name}")

    all_text = []

    # ── Primary: PyMuPDF direct text extraction ──────────────────────
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        print(f"[Extraction] PDF has {len(doc)} pages")

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text blocks with their positions
            blocks = page.get_text("blocks")
            # blocks = list of (x0, y0, x1, y1, text, block_no, block_type)

            page_text = []
            for block in blocks:
                text = block[4].strip()
                block_type = block[6]  # 0=text, 1=image
                if block_type == 0 and text:  # only text blocks, skip image blocks
                    page_text.append(text)

            if page_text:
                combined = "\n".join(page_text)
                all_text.append(f"[Page {page_num + 1}]\n{combined}")

        doc.close()
        full_text = "\n\n".join(all_text)
        print(f"[Extraction] Extracted {len(full_text)} characters from {len(all_text)} pages ✓")

    except Exception as e:
        print(f"[Extraction] PyMuPDF failed: {e}")
        full_text = ""

    # ── Fallback: pypdf ───────────────────────────────────────────────
    if len(full_text.strip()) < 200:
        print("[Extraction] Trying pypdf fallback...")
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            texts = [f"[Page {i+1}]\n{p.page_content}" 
                     for i, p in enumerate(pages) 
                     if p.page_content.strip()]
            full_text = "\n\n".join(texts)
            print(f"[Extraction] pypdf extracted {len(full_text)} characters ✓")
        except Exception as e:
            print(f"[Extraction] pypdf failed: {e}")

    if len(full_text.strip()) < 100:
        raise ValueError(
            "Could not extract text from this PDF. "
            "The file may be corrupted or fully image-based."
        )

    # ── Split into chunks ─────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
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


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    print(f"[Embedding] Embedding {len(texts)} chunks...")
    vectors = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        convert_to_numpy=True,
    )
    print("[Embedding] Done ✓")
    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    model = get_embedding_model()
    vector = model.encode([query], convert_to_numpy=True)
    return vector[0].tolist()