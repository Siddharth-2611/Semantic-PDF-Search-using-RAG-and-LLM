"""
The actual RAG pipeline: retrieve -> build a grounded prompt -> stream the
LLM's answer back token by token.

The LLM call goes through LangChain's `ChatOpenAI` chat model, pointed at
OpenRouter's OpenAI-compatible endpoint via `base_url`. OpenRouter exposes
Google Gemini (and many other models) behind a single OpenAI-style API,
so a single LangChain chat model class covers all of them — swapping
`OPENROUTER_MODEL` in .env (e.g. to an Anthropic or Gemini model id) is
enough to change providers with no code change.
"""
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.embeddings import embed_query
from app.models import Chunk, Document
from app.vector_store import search as vector_search

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    """Lazily-constructed singleton so we don't rebuild the client per request."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            streaming=True,
        )
    return _llm


SYSTEM_PROMPT = (
    "You are a precise assistant that answers questions using ONLY the "
    "provided document excerpts. When you use a fact from an excerpt, cite "
    "it using EXACTLY the format [1], [2], etc. — a number in plain square "
    "brackets matching the excerpt's number. Do not invent any other "
    "citation style. Example of correct citation: 'The CGPA is 8.00 [1].' "
    "If the excerpts don't contain the answer, say so plainly instead of "
    "guessing."
)


def retrieve(
    db: Session, query: str, top_k: int = 5, document_id: str | None = None
) -> list[dict]:
    """
    Embeds the query, searches FAISS, then joins hits back to SQL to get
    the chunk text, page number, and parent document/owner info.

    Note: FAISS itself has no notion of "user" — access control happens
    here, by only resolving vector_ids whose Chunk belongs to a document
    the caller is allowed to see (enforced by the caller passing a
    document_id it already verified, or by filtering across all of a
    user's own documents upstream).
    """
    query_vec = embed_query(query)
    # Over-fetch a bit since some hits may get filtered out below.
    vector_ids, scores = vector_search(query_vec, top_k=top_k * 3)
    if not vector_ids:
        return []

    chunks = (
        db.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.vector_id.in_(vector_ids))
        .all()
    )
    score_by_id = dict(zip(vector_ids, scores))

    results = []
    for chunk, document in chunks:
        if document_id and document.id != document_id:
            continue
        results.append(
            {
                "document_id": document.id,
                "filename": document.filename,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "score": float(score_by_id.get(chunk.vector_id, 0.0)),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def build_prompt(query: str, sources: list[dict]) -> list[SystemMessage | HumanMessage]:
    context = "\n\n".join(
        f"[{i + 1}] (p.{s['page_number']}, {s['filename']}): {s['text']}"
        for i, s in enumerate(sources)
    )
    user_content = (
        f"Document excerpts:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the excerpts above, citing sources like [1], [2]."
    )
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]


async def stream_answer(query: str, sources: list[dict]) -> AsyncGenerator[str, None]:
    """
    Streams the LLM's answer as raw text chunks (SSE-friendly), using
    LangChain's async streaming (astream) under the hood.
    """
    if not sources:
        yield "I couldn't find anything relevant in your documents to answer that."
        return

    messages = build_prompt(query, sources)
    llm = get_llm()
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content


async def generate_answer(query: str, sources: list[dict]) -> str:
    """Non-streaming variant, used where a single JSON response is needed."""
    chunks = [c async for c in stream_answer(query, sources)]
    return "".join(chunks)
