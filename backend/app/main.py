from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, documents, chat

# Creates tables on startup if they don't exist yet. For a real production
# deployment you'd swap this for Alembic migrations, but for a project of
# this size, create_all keeps setup to a single command.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Semantic PDF Search Engine",
    description="RAG-powered semantic search and Q&A over your PDF documents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
