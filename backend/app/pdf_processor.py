"""
PDF text extraction + chunking.

Two design choices worth being able to explain in an interview:

1. We extract page-by-page (not the whole doc as one blob) so every chunk
   can be traced back to a page number for citations.

2. Chunking is "recursive" in the LangChain sense: we try to split on the
   biggest, most semantically meaningful separator first (paragraph
   breaks), and only fall back to smaller separators (sentences, then
   words) if a piece is still too big. This keeps related sentences
   together far more often than a naive fixed-width slice would, which
   directly improves retrieval quality. Overlap between consecutive
   chunks (chunk_overlap) prevents an answer-relevant sentence from being
   split across a chunk boundary and losing context on both sides.
"""
from dataclasses import dataclass

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


@dataclass
class TextChunk:
    page_number: int
    text: str


def extract_pages(pdf_path: str) -> list[PageText]:
    pages: list[PageText] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page_number=i + 1, text=text))
    return pages


def chunk_pages(pages: list[PageText]) -> list[TextChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[TextChunk] = []
    for page in pages:
        for piece in splitter.split_text(page.text):
            piece = piece.strip()
            if piece:
                chunks.append(TextChunk(page_number=page.page_number, text=piece))
    return chunks


def process_pdf(pdf_path: str) -> tuple[int, list[TextChunk]]:
    """Returns (page_count, chunks) for a PDF on disk."""
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)
    return len(pages), chunks
