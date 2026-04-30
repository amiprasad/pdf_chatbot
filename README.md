# 📄 PDF Chatbot — RAG-Powered Multi-User System

A full-stack AI chatbot that lets users upload PDFs and ask questions about them.
Built with FastAPI, LangChain, Qdrant, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![LangChain](https://img.shields.io/badge/LangChain-0.2-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 What It Does

- Upload any PDF and ask questions about it in natural language
- Get AI-powered answers grounded in the document content
- Every user's data is completely private and isolated
- Chat history is saved and persistent across sessions
- Full CRUD — upload, view, delete documents and clear chat history

---

## 🏗️ Tech Stack

| Layer        | Technology            | Purpose                               |
|--------------|-----------------------|---------------------------------------|
| Frontend     | Streamlit             | Web UI                                |
| Backend      | FastAPI               | REST API                              |
| Database     | SQLite + SQLAlchemy   | User, document, chat storage          |
| Vector DB    | Qdrant (local)        | Semantic search                       |
| Embeddings   | sentence-transformers | Convert text to vectors (local, free) |
| LLM          | Groq — LLaMA 3.1      | Generate answers (free API)           |
| Auth         | JWT + bcrypt          | Secure user authentication            |
| PDF Parsing  | PyMuPDF               | Extract text from PDFs                |
| AI Framework | LangChain             | RAG pipeline orchestration            |

---

## ✨ Features

- 🔐 **JWT Authentication** — register, login, token-based security
- 👤 **Multi-user isolation** — each user sees only their own documents
- 📤 **PDF Upload** — drag and drop, background indexing
- 🧠 **RAG Pipeline** — retrieves relevant chunks, answers from context
- 💬 **Chat History** — persistent per user per document
- 🗑️ **Full Delete** — removes file, vectors, and chat history completely
- ⚡ **Fast Embeddings** — local model, no API calls, no rate limits
- 📖 **Source Citations** — shows which page the answer came from

---

## 🗂️ Project Structure

```
pdf_chatbot/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/
│   │   ├── config.py              # Environment variables
│   │   ├── database.py            # SQLite setup
│   │   └── security.py            # JWT + bcrypt
│   ├── models/
│   │   ├── user.py                # User table + schemas
│   │   └── document.py            # Document + ChatMessage tables
│   ├── routers/
│   │   ├── auth.py                # /auth endpoints
│   │   ├── documents.py           # /documents endpoints
│   │   └── chat.py                # /chat endpoints
│   ├── services/
│   │   ├── file_service.py        # PDF file handling
│   │   ├── embedding_service.py   # PDF extraction + embeddings
│   │   ├── vector_service.py      # Qdrant CRUD
│   │   └── chat_service.py        # RAG + LLM
│   └── utils/
│       └── deps.py                # Auth dependency injection
├── frontend/
│   └── app.py                     # Streamlit UI
├── data/
│   ├── uploads/                   # PDF files (per user)
│   └── qdrant_storage/            # Vector DB files
├── .env.example                   # Environment template
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/pdf-chatbot.git
cd pdf-chatbot
```

### 2. Create virtual environment

```bash
python -m venv venv

# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get free API keys

| Service           | URL                         | What it's used for         |
|-------------------|-----------------------------|----------------------------|
| **Groq**          | https://console.groq.com    | LLM for generating answers |
| **Google Gemini** | https://aistudio.google.com | Optional — embeddings      |

### 5. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here
SECRET_KEY=any_random_long_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./pdf_chatbot.db
UPLOAD_DIR=./data/uploads
QDRANT_PATH=./data/qdrant_storage
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_EMBEDDING_MODEL=models/embedding-001
CHUNK_SIZE=500
CHUNK_OVERLAP=80
```

### 6. Create data folders

```bash
mkdir -p data/uploads data/qdrant_storage
```

---

## 🚀 Running the App

Open **two terminals**, both with venv activated:

**Terminal 1 — Backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
streamlit run frontend/app.py
```

Open your browser at **http://localhost:8501**

API docs available at **http://localhost:8000/docs**

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint         | Description-----------|
|--------|------------------|-----------------------|
| POST   | `/auth/register` | Create new account    |
| POST   | `/auth/login`    | Login, get JWT token  |
| GET    | `/auth/me`       | Get current user info |

### Documents
| Method | Endpoint            | Description                         |
|--------|---------------------|-------------------------------------|
| POST   | `/documents/upload` | Upload and index a PDF              |
| GET    | `/documents/`       | List all your documents             |
| GET    | `/documents/{id}`   | Get one document                    |
| DELETE | `/documents/{id}`   | Delete document + vectors + history |

### Chat
| Method | Endpoint             | Description                |
|--------|----------------------|----------------------------|
| POST   | `/chat/ask`          | Ask a question about a PDF |
| GET    | `/chat/history/{id}` | Get chat history           |
| DELETE | `/chat/history/{id}` | Clear chat history         |

---

## 🧠 How RAG Works

```
User asks a question
        ↓
Question is converted to a vector (embedding)
        ↓
Qdrant finds the 4 most similar chunks from the PDF
        ↓
Retrieved chunks are injected into the LLM prompt
        ↓
Groq LLaMA 3.1 generates an answer based on the context
        ↓
Answer + source pages returned to user
```

---

## 🔒 Security

- Passwords are hashed with bcrypt — never stored as plain text
- JWT tokens expire after 30 minutes
- Every database query filters by `user_id` — users cannot access each other's data
- Each user gets a separate folder on disk for their PDFs
- Each user-document pair gets a separate Qdrant collection for their vectors
- Deleting a document removes the file, vectors, and all chat history permanently

---

## 🐛 Common Issues

| Error                       | Cause                   | Fix                                         |
|-----------------------------|-------------------------|---------------------------------------------|
| `GROQ_API_KEY not set`      | Missing .env file       | Copy `.env.example` to `.env` and fill keys |
| `Cannot connect to backend` | uvicorn not running     | Start Terminal 1                            |
| `Document still indexing`   | Background task running | Wait 30 sec, click Refresh                  |
| `Model decommissioned`      | Groq model retired      | Change `GROQ_MODEL` in `.env`               |
| `0 characters extracted`    | Scanned/image PDF       | Use a PDF with selectable text              |

---

## 📦 Requirements

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
sqlalchemy==2.0.30
langchain==0.2.1
langchain-community==0.2.1
langchain-groq==0.1.3
langchain-google-genai==1.0.5
qdrant-client==1.9.1
pypdf==4.2.0
pymupdf
pymupdf4llm
sentence-transformers
python-dotenv==1.0.1
streamlit==1.35.0
requests==2.32.3
```

---

## 🚢 Deployment

### Deploy on Render (free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables from `.env`
7. Deploy — get a live URL in ~5 minutes

---

## 👨‍💻 Author

**Ami** — Built as an internship-level full-stack AI project

---

## 📄 License

MIT License — free to use, modify, and distribute.