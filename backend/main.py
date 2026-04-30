"""
backend/main.py
───────────────
FastAPI application entry point.
Registers all routers, sets up CORS, and initialises the database on startup.

Run with:
  cd pdf_chatbot
  uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import init_db
from backend.routers import auth, documents, chat

# ── App instance ─────────────────────────────────────────────────────
app = FastAPI(
    title="PDF Chatbot API",
    description="Multi-user RAG chatbot — upload PDFs, ask questions, get answers powered by Groq + Gemini.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow Streamlit frontend on port 8501) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup event ─────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Validate config and create DB tables on first run."""
    settings.validate()
    init_db()
    print("✅ PDF Chatbot API started. Docs at http://localhost:8000/docs")


# ── Register routers ──────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "PDF Chatbot API is running 🚀"}