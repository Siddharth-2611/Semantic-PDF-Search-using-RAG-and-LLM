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

**Frontend:** React, Vite  
**Backend:** FastAPI, PostgreSQL  
**AI:** LangChain, FAISS, Sentence Transformers, OpenRouter  
**Auth:** JWT, bcrypt

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
