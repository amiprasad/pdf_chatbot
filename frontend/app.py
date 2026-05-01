"""
frontend/app.py
───────────────
Streamlit UI for the PDF Chatbot.
Communicates with the FastAPI backend via HTTP.

Run with:
  streamlit run frontend/app.py
"""

import streamlit as st
import requests
import time
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────
import os
API_BASE = os.getenv("API_BASE", "http://localhost:8000")


# ── Session state helpers ─────────────────────────────────────────────

def init_session():
    defaults = {
        "token": None,
        "user": None,
        "documents": [],
        "selected_doc": None,
        "chat_history": [],
        "page": "login",   # login | register | main
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


# ── API call helpers ──────────────────────────────────────────────────

def api_post(endpoint: str, json=None, files=None, auth=False) -> tuple:
    """Returns (data_or_none, error_message_or_none)"""
    headers = auth_headers() if auth else {}
    try:
        resp = requests.post(
            f"{API_BASE}{endpoint}",
            json=json,
            files=files,
            headers=headers,
            timeout=60,
        )
        if resp.ok:
            return resp.json(), None
        return None, resp.json().get("detail", "Unknown error")
    except requests.ConnectionError:
        return None, "Cannot connect to the backend. Is it running on port 8000?"
    except Exception as e:
        return None, str(e)


def api_get(endpoint: str) -> tuple:
    if not st.session_state.get("token"):
        return None, "Not logged in"
    try:
        resp = requests.get(
            f"{API_BASE}{endpoint}",
            headers=auth_headers(),
            timeout=30
        )
        try:
            data = resp.json()
        except Exception:
            return None, f"Backend error (status {resp.status_code})"
        if resp.ok:
            return data, None
        return None, data.get("detail", f"Error {resp.status_code}")
    except requests.ConnectionError:
        return None, "Cannot connect to backend."
    except Exception as e:
        return None, str(e)


def api_delete(endpoint: str) -> tuple:
    if not st.session_state.get("token"):
        return None, "Not logged in"
    try:
        resp = requests.delete(
            f"{API_BASE}{endpoint}",
            headers=auth_headers(),
            timeout=30
        )
        try:
            data = resp.json()
        except Exception:
            return None, f"Backend error (status {resp.status_code})"
        if resp.ok:
            return data, None
        return None, data.get("detail", f"Error {resp.status_code}")
    except requests.ConnectionError:
        return None, "Cannot connect to backend."
    except Exception as e:
        return None, str(e)


# ── Page: Login ───────────────────────────────────────────────────────

def render_login():
    st.markdown("## 🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Please fill in both fields.")
            return
        data, err = api_post("/auth/login", json={"username": username, "password": password})
        if err:
            st.error(f"Login failed: {err}")
        else:
            st.session_state.token = data["access_token"]
            st.session_state.user = data["user"]
            st.session_state.page = "main"
            st.rerun()

    st.markdown("---")
    if st.button("Don't have an account? Register →", use_container_width=True):
        st.session_state.page = "register"
        st.rerun()


# ── Page: Register ────────────────────────────────────────────────────

def render_register():
    st.markdown("## 📝 Create Account")
    with st.form("register_form"):
        username = st.text_input("Username")
        email    = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm  = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register", use_container_width=True)

    if submitted:
        if not all([username, email, password, confirm]):
            st.error("Please fill in all fields.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        data, err = api_post("/auth/register", json={"username": username, "email": email, "password": password})
        if err:
            st.error(f"Registration failed: {err}")
        else:
            st.success(f"Account created! Welcome, {data['username']} 🎉")
            time.sleep(1)
            st.session_state.page = "login"
            st.rerun()

    st.markdown("---")
    if st.button("← Back to Login", use_container_width=True):
        st.session_state.page = "login"
        st.rerun()


# ── Sidebar: Document Management ─────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.caption(st.session_state.user["email"])
        st.markdown("---")

        # ── Upload PDF ──────────────────────────────────────────────
        st.markdown("#### 📤 Upload PDF")
        uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded_file and st.button("Upload & Index", use_container_width=True):
            with st.spinner("Uploading…"):
                data, err = api_post(
                    "/documents/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    auth=True,
                )
            if err:
                st.error(f"Upload failed: {err}")
            else:
                st.success(f"'{uploaded_file.name}' uploaded! Indexing in background…")
                time.sleep(1)
                st.rerun()

        st.markdown("---")

        # ── Document List ───────────────────────────────────────────
        st.markdown("#### 📚 Your Documents")
        docs, err = api_get("/documents/")
        if err:
            if "expired" in str(err).lower() or "invalid" in str(err).lower() or "401" in str(err):
                st.warning("Session expired. Please log in again.")
                st.session_state.token = None
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error(err)
            st.session_state.documents = []

        else:
            st.session_state.documents = docs

        if not st.session_state.documents:
            st.info("No PDFs uploaded yet.")
        else:
            for doc in st.session_state.documents:
                col1, col2 = st.columns([3, 1])
                with col1:
                    is_indexed = doc.get("qdrant_collection") is not None
                    status_icon = "✅" if is_indexed else "⏳"
                    if st.button(
                        f"{status_icon} {doc['filename'][:22]}",
                        key=f"select_{doc['id']}",
                        use_container_width=True,
                        help=f"{doc['file_size_kb']} KB | {doc['filename']}",
                    ):
                        st.session_state.selected_doc = doc
                        # Load chat history for this doc
                        history, _ = api_get(f"/chat/history/{doc['id']}")
                        st.session_state.chat_history = history or []
                        st.rerun()
                with col2:
                    if st.button("🗑", key=f"del_{doc['id']}", help="Delete document"):
                        data, err = api_delete(f"/documents/{doc['id']}")
                        if err:
                            st.error(err)
                        else:
                            st.success("Deleted!")
                            if st.session_state.selected_doc and st.session_state.selected_doc["id"] == doc["id"]:
                                st.session_state.selected_doc = None
                                st.session_state.chat_history = []
                            time.sleep(0.5)
                            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["token", "user", "documents", "selected_doc", "chat_history"]:
                st.session_state[key] = None if key not in ["documents", "chat_history"] else []
            st.session_state.page = "login"
            st.rerun()


# ── Main Chat Area ────────────────────────────────────────────────────

def render_chat():
    doc = st.session_state.selected_doc

    if not doc:
        # Welcome screen
        st.markdown("## 👋 Welcome to PDF Chatbot")
        st.markdown("""
        **How to get started:**
        1. 📤 Upload a PDF using the sidebar
        2. ✅ Wait for indexing (the ⏳ turns to ✅)
        3. 📄 Click on a document to open chat
        4. 💬 Ask questions about your PDF!
        
        ---
        **Features:**
        - 🔒 Your documents are private — only you can see them
        - 🧠 Powered by Groq (LLaMA 3) + Google Gemini embeddings
        - 💾 Chat history is saved across sessions
        - 🗑 Delete documents to permanently remove all data
        """)
        return

    # ── Document header ─────────────────────────────────────────────
    is_indexed = doc.get("qdrant_collection") is not None
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        st.markdown(f"### 📄 {doc['filename']}")
        st.caption(f"{doc['file_size_kb']} KB | Uploaded {doc['uploaded_at'][:10]}")
    with col2:
        if st.button("🔄 Refresh", help="Refresh indexing status"):
            # Fetch fresh document data from backend
            fresh_doc, err = api_get(f"/documents/{doc['id']}")
            if fresh_doc:
                st.session_state.selected_doc = fresh_doc
                st.rerun()
            else:
                # Fallback: refresh full list
                docs, _ = api_get("/documents/")
                for d in (docs or []):
                    if d["id"] == doc["id"]:
                        st.session_state.selected_doc = d
                        break
                st.rerun()
    with col3:
        if st.button("🗑 Clear Chat", help="Delete all chat messages for this document"):
            _, err = api_delete(f"/chat/history/{doc['id']}")
            if not err:
                st.session_state.chat_history = []
                st.success("Chat cleared!")
                st.rerun()

    if not is_indexed:
        st.warning("⏳ Document is still being indexed. Please wait a moment, then click Refresh.")
        return

    st.markdown("---")

    # ── Chat history display ─────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.info("No messages yet. Ask a question below!")
        else:
            for msg in st.session_state.chat_history:
                role = msg["role"]
                content = msg["content"]
                with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
                    st.markdown(content)

    # ── Input box ────────────────────────────────────────────────────
    question = st.chat_input("Ask a question about this PDF…")

    if question:
        # Show user message immediately
        with st.chat_message("user", avatar="🧑"):
            st.markdown(question)

        # Call API
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                data, err = api_post(
                    "/chat/ask",
                    json={"document_id": doc["id"], "question": question},
                    auth=True,
                )

            if err:
                if "425" in str(err) or "still being indexed" in str(err).lower():
                    st.warning("⏳ Document is still indexing. Please wait and try again.")
                else:
                    st.error(f"Error: {err}")
            else:
                st.markdown(data["answer"])

                # Show source excerpts in expander
                if data.get("sources"):
                    with st.expander(f"📖 Sources ({len(data['sources'])} chunks used)"):
                        for i, src in enumerate(data["sources"], 1):
                            st.text(f"[{i}] {src[:200]}…")

                # Reload full history from API to stay in sync
                history, _ = api_get(f"/chat/history/{doc['id']}")
                st.session_state.chat_history = history or []
                st.rerun()


# ── Main App ──────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="PDF Chatbot",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for cleaner look
    st.markdown("""
        <style>
        .stChatMessage { border-radius: 12px; padding: 8px; }
        [data-testid="stSidebar"] { background-color: #1a1a2e; }
        [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
        </style>
    """, unsafe_allow_html=True)

    init_session()

    page = st.session_state.page

    if page == "login":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("# 📄 PDF Chatbot")
            st.caption("Ask questions about your PDF documents using AI")
            st.markdown("---")
            render_login()

    elif page == "register":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("# 📄 PDF Chatbot")
            st.markdown("---")
            render_register()

    elif page == "main":
        if not st.session_state.token:
            st.session_state.page = "login"
            st.rerun()
        render_sidebar()
        render_chat()


if __name__ == "__main__":
    main()