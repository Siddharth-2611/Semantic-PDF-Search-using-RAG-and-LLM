import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, User
from app.rag import generate_answer, retrieve, stream_answer
from app.schemas import ChatRequest, ChatResponse, SourceChunk

router = APIRouter(prefix="/chat", tags=["chat"])


def _authorize_scope(db: Session, current_user: User, document_id: str | None):
    """If a document_id is given, make sure the caller actually owns it —
    otherwise a user could probe another user's documents by id."""
    if document_id is None:
        return
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Non-streaming variant: returns the full answer + sources in one JSON body."""
    _authorize_scope(db, current_user, payload.document_id)

    sources = retrieve(db, payload.query, payload.top_k, payload.document_id)
    answer = await generate_answer(payload.query, sources)
    return ChatResponse(
        answer=answer,
        sources=[SourceChunk(**s) for s in sources],
    )


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events stream: first a `sources` event with citation
    metadata, then a sequence of `token` events as the LLM generates the
    answer, then a final `done` event. This lets the UI show "Sources"
    immediately while the answer is still being written, and render each
    token as it arrives instead of waiting for the full response.
    """
    _authorize_scope(db, current_user, payload.document_id)
    sources = retrieve(db, payload.query, payload.top_k, payload.document_id)

    async def event_stream():
        yield f"event: sources\ndata: {json.dumps([s for s in sources])}\n\n"
        async for token in stream_answer(payload.query, sources):
            yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
