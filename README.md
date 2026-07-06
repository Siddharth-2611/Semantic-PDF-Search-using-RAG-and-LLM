# Docsift — Semantic PDF Search Engine (RAG + LLM)

A full-stack Retrieval-Augmented Generation (RAG) search engine over your own PDFs.
Upload documents, then ask questions in plain English and get answers grounded in
your files, with page-level citations, streamed token-by-token.

## Architecture

```
┌────────────┐      ┌─────────────────────────────────────────────┐
│  React 18  │◄────►│                  FastAPI                     │
│  (Vite)    │ SSE  │                                               │
└────────────┘      │  auth.py      JWT auth (passlib/bcrypt)      │
                     │  pdf_processor.py   PyMuPDF extraction +     │
                     │                     LangChain recursive      │
                     │                     chunking                 │
                     │  embeddings.py      SentenceTransformers      │
                     │                     (all-MiniLM-L6-v2)        │
                     │  vector_store.py    FAISS (IndexFlatIP)       │
                     │  rag.py             retrieval + LangChain     │
                     │                     ChatOpenAI → OpenRouter   │
                     │  models.py          SQLAlchemy ORM            │
                     └──────────────┬────────────────────────────────┘
                                    │
                             ┌──────▼──────┐
                             │ PostgreSQL  │  (or SQLite for local dev)
                             └─────────────┘
```

**Retrieval flow:** PDF → PyMuPDF text extraction (per page) → LangChain
`RecursiveCharacterTextSplitter` (overlapping chunks) → SentenceTransformers embeddings
(384-dim, normalized) → FAISS index (cosine similarity via inner product) → on query,
embed the question, search FAISS, join hits back to Postgres for page numbers +
ownership checks → build a grounded prompt → LangChain `ChatOpenAI` (pointed at
OpenRouter) streams the answer back over Server-Sent Events.

## Why these choices (for interview prep)

- **FAISS `IndexFlatIP` over normalized vectors** = exact cosine similarity search,
  without computing a square root per comparison. Exact (flat) search is used
  instead of an approximate index (IVF/HNSW) because at portfolio/small-corpus scale,
  flat search is already fast and has no recall loss.
- **Global FAISS index + per-user isolation at the SQL layer.** Rather than one FAISS
  index per user, every vector lives in one index under a stable integer id
  (`Chunk.vector_id`). Ownership is enforced by joining FAISS hits back to
  `Chunk → Document → owner_id` in Postgres. This scales better than N separate
  indexes as the user base grows.
- **Recursive, overlapping chunking.** `RecursiveCharacterTextSplitter` tries the
  largest semantic separator first (paragraph breaks) and only falls back to smaller
  ones, keeping related sentences together far more often than a fixed-width slice.
  Overlap between chunks prevents an answer-relevant sentence from being cut in half
  at a chunk boundary.
- **LangChain `ChatOpenAI` against OpenRouter's OpenAI-compatible endpoint**, instead
  of a provider-specific SDK. OpenRouter fronts many models (Gemini, Claude, Llama,
  etc.) behind one API, so swapping `OPENROUTER_MODEL` is enough to change providers
  with zero code changes.
- **JWT auth with bcrypt hashing.** Stateless auth suitable for a horizontally
  scaled API; passwords are never stored in plaintext or reversibly.

## Project structure

```
backend/
  app/
    main.py            FastAPI app, CORS, router registration
    config.py           Centralized settings (env-driven)
    database.py          SQLAlchemy engine/session
    models.py             User, Document, Chunk ORM models
    schemas.py             Pydantic request/response models
    auth.py                  JWT + bcrypt password hashing
    pdf_processor.py          PyMuPDF extraction + LangChain chunking
    embeddings.py               SentenceTransformers wrapper
    vector_store.py               FAISS index management
    rag.py                          Retrieval + LangChain LLM streaming
    routers/
      auth.py       /auth/register, /auth/login
      documents.py  /documents (upload, list, delete)
      chat.py       /chat, /chat/stream (SSE)
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx, api.js, styles.css
    components/  Login, Upload, DocumentList, Chat
  package.json
  vite.config.js
```

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- Set `OPENROUTER_API_KEY` (get one at https://openrouter.ai).
- For local dev without Postgres installed, set:
  `DATABASE_URL=sqlite:///./app.db`
- Otherwise, point `DATABASE_URL` at a running Postgres instance.

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

The first request that touches embeddings will download `all-MiniLM-L6-v2`
(~90MB) from Hugging Face — this requires internet access on first run only;
it's cached locally afterward.

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to
`http://localhost:8000` (see `vite.config.js`), so both servers need to be running.

## Notes / things to be upfront about in interviews

- **Email verification + login notifications are implemented via smtplib.**
  Registration sends a 4-digit code (10 min expiry) that must be verified
  before login is allowed; every successful login sends a notification email
  with device name (parsed from User-Agent) and approximate location
  (IP geolocation via ip-api.com, free/no-key). See `email_utils.py` and
  `device_info.py`. Requires a Gmail **App Password** in `.env` — see the
  `.env.example` comments. If SMTP isn't configured, emails are skipped
  with a log warning instead of failing the request, so the app still runs
  without it for quick local testing.
- **Vector id allocation** (`_next_vector_id` in `documents.py`) uses a simple
  max+1 strategy, which is fine for a single-process app but isn't atomic under
  concurrent writers. A production version would use a Postgres sequence.
- **`Base.metadata.create_all`** creates tables on startup instead of using
  Alembic migrations — appropriate for a project this size, but worth mentioning
  as a known simplification if asked.
