# 🚀 Semantic PDF Search Engine

A full-stack RAG application that enables users to upload PDFs and ask questions in natural language, returning context-aware answers with source citations.

## ✨ Features

- Semantic PDF Search
- RAG-based Question Answering
- Page-level Citations
- Persistent Chat History
- JWT Authentication
- Email Verification
- Streaming Responses (SSE)

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, plain CSS (no UI framework) |
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL (SQLite supported for local dev), SQLAlchemy ORM |
| Auth | JWT (python-jose), bcrypt password hashing (passlib) |
| Vector search | FAISS (`IndexFlatIP`) |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`, 384-dim) |
| PDF processing | PyMuPDF (text extraction) |
| Text chunking | LangChain `RecursiveCharacterTextSplitter` |
| LLM orchestration | LangChain `ChatOpenAI` → OpenRouter (OpenAI-compatible API) |
| Email | Python `smtplib` (SMTP, e.g. Gmail App Password) |
| Device/location metadata | `user-agents` (User-Agent parsing), ip-api.com (IP geolocation) |
| Streaming transport | Server-Sent Events (SSE) |

## 🏗 Architecture

```text
React → FastAPI → FAISS + PostgreSQL → OpenRouter LLM
```

## ⚡ Run Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 📌 Workflow

```text
PDF Upload
    ↓
Text Extraction
    ↓
Chunking + Embeddings
    ↓
FAISS Retrieval
    ↓
LLM Generation
    ↓
Answer + Citations
```

## 📄 License

Educational & Portfolio Project.
