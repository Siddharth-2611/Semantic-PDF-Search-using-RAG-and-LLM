# Docsift — Semantic PDF Search Engine (RAG + LLM)

A full-stack Retrieval-Augmented Generation (RAG) search engine over your own PDFs.
Upload documents, then ask questions in plain English and get answers grounded in
your files, with page-level citations, streamed token-by-token.

## Features

- **Semantic search over PDFs** — upload a document, ask questions in plain English
- **RAG answers with page-level citations** — every claim is traceable to a source
  excerpt and page number; citations render as inline `[1]` chips, with a
  collapsible "Sources" panel showing the underlying excerpts
- **Persistent chat history** — every conversation is saved (Postgres), auto-titled
  from its first message, shown in a sidebar, and can be reopened, renamed, or
  deleted; reopening a past conversation shows the exact same answers and
  citations without re-running retrieval
- **JWT authentication** with bcrypt password hashing
- **Email verification on signup** — 4-digit code, 10-minute expiry, required
  before first login
- **Login notification emails** — device name (parsed from User-Agent) + approximate
  location (IP geolocation), sent on every login
- **Streaming responses** over Server-Sent Events — tokens appear as the LLM
  generates them, not after a long wait
- **Provider-agnostic LLM layer** — currently wired to OpenRouter (OpenAI-compatible),
  swappable to any OpenAI-compatible endpoint via one `.env` value

---

## Tech Stack

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

---

## System Design

**Core flow — asking a question:**

1. User uploads a PDF → text is extracted per page (PyMuPDF) → split into
   overlapping chunks (LangChain) → each chunk is embedded (SentenceTransformers)
   → embeddings are added to a FAISS index, and chunk metadata (text, page number,
   owning document) is saved to Postgres.
2. User asks a question → the question is embedded the same way → FAISS returns
   the nearest chunks by cosine similarity → those FAISS hits are joined back to
   Postgres to fetch the actual text, page number, and to enforce that the chunk
   belongs to a document the user actually owns.
3. The retrieved excerpts are assembled into a grounded prompt and sent to the LLM
   (via LangChain, through OpenRouter) → the answer streams back token-by-token
   over SSE, with citation markers tied to the retrieved excerpts.
4. Both the question and the answer (with its sources) are saved to the
   conversation's message history, so reopening the conversation later
   reconstructs the same view without re-running retrieval.

**Key system design decisions:**

- **Single global FAISS index, not one per user.** Every embedding is stored under
  a stable integer id (`Chunk.vector_id`). Per-user isolation is enforced at the
  SQL layer (`Chunk → Document → owner_id`), not by partitioning FAISS itself —
  this scales better as the user base grows than maintaining N separate indexes.
- **Exact search over approximate search.** `IndexFlatIP` (exact, brute-force
  cosine similarity via inner product on normalized vectors) is used instead of
  an approximate index like IVF or HNSW, since at portfolio/small-corpus scale
  exact search is already fast and loses no recall.
- **Stateless auth.** JWTs mean the API can be horizontally scaled without a
  shared session store.
- **Fail-soft external dependencies.** SMTP and IP-geolocation calls run as
  FastAPI `BackgroundTasks` and catch their own exceptions — a slow or failing
  email/geolocation call never blocks or fails the actual API response.
- **Provider-agnostic LLM layer.** The LLM is called through LangChain's
  `ChatOpenAI` pointed at OpenRouter's OpenAI-compatible endpoint, so switching
  models or providers is a one-line `.env` change, not a code change.

---

## Architecture

```
┌────────────┐      ┌─────────────────────────────────────────────┐
│  React 18  │◄────►│                  FastAPI                     │
│  (Vite)    │ SSE  │                                               │
└────────────┘      │  auth.py         JWT auth (passlib/bcrypt)   │
                     │  email_utils.py  smtplib verification +     │
                     │                  login-notification emails  │
                     │  device_info.py  User-Agent parsing +       │
                     │                  IP geolocation             │
                     │  pdf_processor.py   PyMuPDF extraction +     │
                     │                     LangChain recursive      │
                     │                     chunking                 │
                     │  embeddings.py      SentenceTransformers      │
                     │                     (all-MiniLM-L6-v2)        │
                     │  vector_store.py    FAISS (IndexFlatIP)       │
                     │  rag.py             retrieval + LangChain     │
                     │                     ChatOpenAI → OpenRouter   │
                     │  models.py          SQLAlchemy ORM            │
                     │                     (incl. Conversation/      │
                     │                      Message for chat history)│
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

---

## Folder Structure

```
semantic-pdf-search/
├── README.md
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py            FastAPI app, CORS, router registration
│       ├── config.py          Centralized settings (env-driven)
│       ├── database.py        SQLAlchemy engine/session
│       ├── models.py          User, Document, Chunk, Conversation, Message ORM models
│       ├── schemas.py         Pydantic request/response models
│       ├── auth.py            JWT + bcrypt password hashing
│       ├── email_utils.py     smtplib: verification + login-notification emails
│       ├── device_info.py     User-Agent parsing + IP geolocation
│       ├── pdf_processor.py   PyMuPDF extraction + LangChain chunking
│       ├── embeddings.py      SentenceTransformers wrapper
│       ├── vector_store.py    FAISS index management
│       ├── rag.py             Retrieval + LangChain LLM streaming
│       └── routers/
│           ├── auth.py            /auth/register, /verify, /resend-verification, /login
│           ├── documents.py       /documents (upload, list, delete)
│           ├── chat.py            /chat, /chat/stream (SSE) — auto-creates/continues a conversation
│           └── conversations.py   /conversations (list, get detail, rename, delete)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        ├── styles.css
        └── components/
            ├── Login.jsx              Login/register + email verification step
            ├── Upload.jsx             Drag-and-drop PDF upload
            ├── DocumentList.jsx       Sidebar list of uploaded documents
            ├── ConversationList.jsx   Sidebar list of saved chat threads
            └── Chat.jsx               Streaming chat with citations
```

---

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- **Database** — for local dev without Postgres installed:
  `DATABASE_URL=sqlite:///./app.db`
  Otherwise point it at a running Postgres instance (must already have the
  target database created, e.g. `CREATE DATABASE pdf_search;`).
- **LLM** — set `OPENROUTER_API_KEY` (get one at https://openrouter.ai/keys).
  `OPENROUTER_MODEL` can be any model OpenRouter serves, e.g.
  `openai/gpt-oss-120b:free` (free tier — rate-limited and can 429 under load)
  or a paid model for reliability.
- **Email** — set `SMTP_USERNAME` / `SMTP_PASSWORD` to send real verification
  and login-notification emails. For Gmail: enable 2-Step Verification, then
  generate an **App Password** at https://myaccount.google.com/apppasswords
  and paste it **without spaces**. If left blank, the app still runs —
  emails are skipped with a log warning instead of failing requests.

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

The first request that touches embeddings downloads `all-MiniLM-L6-v2` (~90MB)
from Hugging Face — needs internet on first run only, then it's cached locally.

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to
`http://localhost:8000` (see `vite.config.js`), so both servers need to be running.

---

## Notes / things to be upfront about in interviews

- **Vector search struggles with exact-match lookups in tabular/list-style PDFs**
  (e.g. "find this specific name in a 500-row roster"). Semantic embeddings match
  by *meaning*, not exact string identity, so proper-noun lookups in dense lists
  are unreliable with pure vector search — this is a known, explainable limitation,
  and the standard production fix is hybrid search (keyword/BM25 + vector), not a
  bug in the implementation.
- **Vector id allocation** (`_next_vector_id` in `documents.py`) uses a simple
  max+1 strategy, fine for a single-process app but not atomic under concurrent
  writers. A production version would use a Postgres sequence.
- **`Base.metadata.create_all`** creates tables on startup instead of using Alembic
  migrations — appropriate for a project this size, worth mentioning as a known
  simplification if asked.
- **Free OpenRouter models are rate-limited** and can return 429s under load;
  fine for development, but for a live demo consider adding OpenRouter credits
  or using a paid model for reliability.
- **Persistent chat history is implemented and tested, but walk through it
  yourself before claiming it on a resume or in an interview.** It touches
  more moving parts than the rest of the app (`Conversation`/`Message` tables,
  auto-titling, the `_get_or_create_conversation` flow in `chat.py`, and the
  `ConversationList` sidebar in the frontend) — read those files and try
  renaming/continuing/deleting a conversation yourself so you can actually
  explain the design if asked, rather than citing a feature you haven't
  exercised firsthand.
