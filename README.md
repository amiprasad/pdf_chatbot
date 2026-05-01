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

* Upload any PDF and ask questions about it in natural language
* Get AI-powered answers grounded in the document content
* Every user's data is completely private and isolated
* Chat history is saved and persistent across sessions
* Full CRUD — upload, view, delete documents and clear chat history

---

## 🏗️ Tech Stack

| Layer        | Technology                                        | Purpose                      |
| ------------ | ------------------------------------------------- | ---------------------------- |
| Frontend     | Streamlit                                         | Web UI                       |
| Backend      | FastAPI                                           | REST API                     |
| Database     | SQLite + SQLAlchemy                               | User, document, chat storage |
| Vector DB    | Qdrant (local)                                    | Semantic search              |
| Embeddings   | HuggingFace Inference API (sentence-transformers) | Convert text to vectors      |
| LLM          | Groq — LLaMA 3.1                                  | Generate answers             |
| Auth         | JWT + bcrypt                                      | Secure user authentication   |
| PDF Parsing  | PyMuPDF                                           | Extract text from PDFs       |
| AI Framework | LangChain                                         | RAG pipeline orchestration   |

---

## ✨ Features

* 🔐 **JWT Authentication** — register, login, token-based security
* 👤 **Multi-user isolation** — each user sees only their own documents
* 📤 **PDF Upload** — drag and drop, background indexing
* 🧠 **RAG Pipeline** — retrieves relevant chunks, answers from context
* 💬 **Chat History** — persistent per user per document
* 🗑️ **Full Delete** — removes file, vectors, and chat history completely
* ⚡ **Fast Embeddings** — API-based (HuggingFace), no local model needed
* 📖 **Source Citations** — shows which page the answer came from

---

## 🗂️ Project Structure

```
pdf_chatbot/
├── backend/
├── frontend/
├── data/
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/pdf-chatbot.git
cd pdf-chatbot
```

---

### 2. Create virtual environment

```bash
python -m venv venv

# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Get free API keys

| Service     | URL                                    | Purpose    |
| ----------- | -------------------------------------- | ---------- |
| Groq        | https://console.groq.com               | LLM        |
| HuggingFace | https://huggingface.co/settings/tokens | Embeddings |

---

### 5. Configure environment

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Fill in your keys in `.env`

---

### 6. Run the app

**Terminal 1 — Backend:**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**

```bash
streamlit run frontend/app.py
```

---

Open:

* Frontend → http://localhost:8501
* Backend docs → http://localhost:8000/docs

---

## 🧠 How RAG Works

```
User question
   ↓
Converted to embedding
   ↓
Qdrant retrieves relevant chunks
   ↓
Chunks passed to LLM
   ↓
LLM generates contextual answer
```

---

## 🔒 Security

* Passwords hashed with bcrypt
* JWT authentication with expiration
* User-level data isolation
* Separate storage per user
* Full deletion removes all related data

---

## 🚢 Deployment

### Backend → Render

* Build: `pip install -r requirements.txt`
* Start:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Frontend → Streamlit Cloud

* Deploy `frontend/app.py`

---

## 👨‍💻 Author

Ami

---

## 📄 License

MIT License
