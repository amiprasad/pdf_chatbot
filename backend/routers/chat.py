"""
routers/chat.py
────────────────
Chat endpoints (all scoped to the authenticated user):

  POST /chat/ask                     - ask a question about a PDF
  GET  /chat/history/{doc_id}        - get full chat history for a document
  DELETE /chat/history/{doc_id}      - clear chat history for a document
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.models.users import User
from backend.models.document import Document, ChatMessage, ChatRequest, ChatResponse, ChatMessageOut
from backend.services.chat_service import generate_answer
from backend.utils.deps import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question about a PDF using RAG.
    Steps:
    1. Verify the user owns this document
    2. Check indexing is complete
    3. Load chat history from DB
    4. Run RAG pipeline (vector search + Groq LLM)
    5. Save the new Q&A pair to DB
    """
    # 1. Verify ownership
    doc = (
        db.query(Document)
        .filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 2. Check indexing
    if not doc.qdrant_collection:
        raise HTTPException(
            status_code=425,  # Too Early
            detail="Document is still being indexed. Please wait a moment and try again.",
        )

    # 3. Load chat history (list of (role, content) tuples)
    history_records = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.document_id == request.document_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    chat_history = [(msg.role, msg.content) for msg in history_records]

    # 4. Run RAG
    result = generate_answer(
        user_id=current_user.id,
        document_id=request.document_id,
        question=request.question,
        chat_history=chat_history,
    )

    # 5. Persist the new exchange
    db.add(ChatMessage(
        document_id=request.document_id,
        user_id=current_user.id,
        role="user",
        content=request.question,
    ))
    db.add(ChatMessage(
        document_id=request.document_id,
        user_id=current_user.id,
        role="assistant",
        content=result["answer"],
    ))
    db.commit()

    return ChatResponse(answer=result["answer"], sources=result["sources"])


@router.get("/history/{doc_id}", response_model=List[ChatMessageOut])
def get_chat_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the full chat history for a document (current user only)."""
    # Verify ownership
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.document_id == doc_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


@router.delete("/history/{doc_id}", status_code=200)
def clear_chat_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all chat messages for a specific document.
    This is a HARD DELETE — messages are removed from the database.
    """
    # Verify ownership
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    deleted_count = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.document_id == doc_id,
            ChatMessage.user_id == current_user.id,
        )
        .delete()
    )
    db.commit()

    return {"message": f"Cleared {deleted_count} messages from chat history."}