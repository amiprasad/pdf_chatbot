"""
services/chat_service.py
────────────────────────
RAG (Retrieval-Augmented Generation) pipeline:
  1. Retrieve relevant chunks from Qdrant
  2. Build a prompt with retrieved context + chat history
  3. Call Groq LLM (free, fast llama3)
  4. Return answer + source excerpts

This is the brain of the chatbot.
"""

from typing import List, Tuple

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.core.config import settings
from backend.services.vector_service import search_similar


# System prompt for the chatbot
SYSTEM_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided PDF document context.

Rules:
- Only answer from the given context. If the answer isn't in the context, say "I couldn't find that information in the document."
- Be concise and accurate.
- Cite the page number when you know it (e.g., "According to page 3...").
- Never make up information.
"""


def get_llm() -> ChatGroq:
    """Return a Groq LLM instance. Free tier: generous rate limits."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.2,          # low temp for factual responses
        max_tokens=1024,
    )


def format_chat_history(history: List[Tuple[str, str]]) -> List:
    """
    Convert list of (role, content) tuples to LangChain message objects.
    history = [("user", "What is X?"), ("assistant", "X is ..."), ...]
    """
    messages = []
    for role, content in history:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def generate_answer(
    user_id: int,
    document_id: int,
    question: str,
    chat_history: List[Tuple[str, str]],
) -> dict:
    """
    Full RAG pipeline for one question.

    Args:
        user_id:      Needed to scope the Qdrant collection
        document_id:  Needed to scope the Qdrant collection
        question:     The user's question
        chat_history: List of (role, content) tuples from DB

    Returns:
        {"answer": str, "sources": [str, ...]}
    """
    # ── Step 1: Retrieve relevant chunks ────────────────────────────
    hits = search_similar(user_id, document_id, question, top_k=4)

    if not hits:
        return {
            "answer": "I couldn't find any relevant content in this document. Please make sure the PDF was processed successfully.",
            "sources": [],
        }

    # ── Step 2: Build context string ────────────────────────────────
    context_parts = []
    sources = []
    for hit in hits:
        page_num = hit["page"] + 1  # 0-indexed → human-readable
        excerpt = hit["text"][:300]  # first 300 chars as source snippet
        context_parts.append(f"[Page {page_num}]\n{hit['text']}")
        sources.append(f"Page {page_num}: {excerpt}...")

    context = "\n\n---\n\n".join(context_parts)

    # ── Step 3: Build messages for LLM ──────────────────────────────
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add last 6 turns of history (3 pairs) to keep context window small
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    messages.extend(format_chat_history(recent_history))

    # Add the current question with context injected
    user_message = f"""Context from the document:
{context}

Question: {question}"""
    messages.append(HumanMessage(content=user_message))

    # ── Step 4: Call Groq LLM ────────────────────────────────────────
    llm = get_llm()
    response = llm.invoke(messages)
    answer = response.content

    return {"answer": answer, "sources": sources}