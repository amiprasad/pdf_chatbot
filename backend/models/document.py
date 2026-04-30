"""
models/document.py
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, List

from backend.core.database import Base


# ── ORM Models ──────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename          = Column(String(200), nullable=False)
    stored_name       = Column(String(200), nullable=False)
    file_path         = Column(String(500), nullable=False)
    file_size_kb      = Column(Integer, default=0)
    qdrant_collection = Column(String(200), nullable=True)   # ← fixed spelling
    uploaded_at       = Column(DateTime, default=datetime.utcnow)

    owner        = relationship("User", back_populates="documents")
    messages     = relationship("ChatMessage", back_populates="document",
                               cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    role        = Column(String(20), nullable=False)
    content     = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="messages")


# ── Pydantic Schemas ─────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id:                int
    filename:          str
    file_size_kb:      int
    qdrant_collection: Optional[str] = None   # ← fixed spelling, removed duplicate
    uploaded_at:       datetime               # ← only once

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    role:       str
    content:    str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    document_id: int
    question:    str


class ChatResponse(BaseModel):
    answer:  str
    sources: List[str] = []