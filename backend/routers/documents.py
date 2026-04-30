"""
routers/documents.py
─────────────────────
CRUD endpoints for PDF documents (per-user isolated):

  POST   /documents/upload          - upload a PDF and index it
  GET    /documents/                 - list all PDFs for the current user
  GET    /documents/{doc_id}         - get metadata for one document
  DELETE /documents/{doc_id}         - delete PDF + vectors + chat history
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.models.users import User
from backend.models.document import Document, DocumentOut
from backend.services.file_service import save_pdf, delete_pdf
from backend.services.vector_service import index_document, delete_collection
from backend.utils.deps import get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


def _do_indexing(file_path: str, user_id: int, document_id: int, db_url: str):
    """
    Background task: embed the PDF and store vectors in Qdrant.
    Runs after the HTTP response is sent so the upload feels instant.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Open a fresh DB session for the background thread
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    BgSession = sessionmaker(bind=engine)
    bg_db = BgSession()

    try:
        chunk_count = index_document(user_id, document_id, file_path)
        # Update collection name in DB
        col = f"user_{user_id}_doc_{document_id}"
        doc = bg_db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.qdrant_collection = col
            bg_db.commit()
        print(f"[Indexing] doc_id={document_id} indexed {chunk_count} chunks ✓")
    except Exception as e:
        print(f"[Indexing ERROR] doc_id={document_id}: {e}")
    finally:
        bg_db.close()


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF. Steps:
    1. Save file to disk (user-specific folder)
    2. Create DB record
    3. Kick off background indexing (embed + store in Qdrant)
    4. Return immediately — no waiting for indexing
    """
    # Save to disk
    saved = save_pdf(current_user.id, file)

    # Create DB record
    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        stored_name=saved["stored_name"],
        file_path=saved["file_path"],
        file_size_kb=saved["file_size_kb"],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Kick off background indexing
    from backend.core.config import settings
    background_tasks.add_task(
        _do_indexing,
        saved["file_path"],
        current_user.id,
        doc.id,
        settings.DATABASE_URL,
    )

    return doc


@router.get("/", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all PDFs uploaded by the current user."""
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata for a single document. Only returns docs owned by the user."""
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{doc_id}", status_code=200)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document and all related data:
    1. Delete vectors from Qdrant
    2. Delete file from disk
    3. Delete DB record (cascades to chat_messages)
    """
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 1. Delete Qdrant vectors
    deleted_vectors = delete_collection(current_user.id, doc_id)

    # 2. Delete file from disk
    delete_pdf(doc.file_path)

    # 3. Delete DB record (ChatMessages cascade automatically)
    db.delete(doc)
    db.commit()

    return {
        "message": f"Document '{doc.filename}' deleted successfully.",
        "vectors_deleted": deleted_vectors,
    }