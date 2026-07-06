import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.embeddings import embed_texts
from app.models import Chunk, Document, User
from app.pdf_processor import process_pdf
from app.schemas import DocumentOut
from app.vector_store import add_vectors, remove_vectors

router = APIRouter(prefix="/documents", tags=["documents"])


def _next_vector_id(db: Session) -> int:
    """
    Simplest possible strategy for a global, ever-increasing vector id:
    one more than the current max. Fine for a single-process demo app;
    a production version would use a DB sequence to make this atomic
    under concurrent writers.
    """
    max_id = db.query(Chunk.vector_id).order_by(Chunk.vector_id.desc()).first()
    return (max_id[0] + 1) if max_id else 0


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    os.makedirs(settings.upload_dir, exist_ok=True)
    saved_name = f"{uuid.uuid4()}.pdf"
    saved_path = os.path.join(settings.upload_dir, saved_name)
    with open(saved_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    document = Document(
        owner_id=current_user.id, filename=file.filename, status="processing"
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        page_count, chunks = process_pdf(saved_path)
        if not chunks:
            document.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=422, detail="No extractable text found in this PDF"
            )

        vectors = embed_texts([c.text for c in chunks])
        start_id = _next_vector_id(db)
        vector_ids = list(range(start_id, start_id + len(chunks)))

        for chunk, vid in zip(chunks, vector_ids):
            db.add(
                Chunk(
                    document_id=document.id,
                    vector_id=vid,
                    page_number=chunk.page_number,
                    text=chunk.text,
                )
            )

        add_vectors(vector_ids, vectors)

        document.page_count = page_count
        document.chunk_count = len(chunks)
        document.status = "ready"
        db.commit()
        db.refresh(document)
        return document

    except HTTPException:
        raise
    except Exception as exc:
        document.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
    finally:
        file.file.close()


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    vector_ids = [c.vector_id for c in document.chunks]
    if vector_ids:
        remove_vectors(vector_ids)

    db.delete(document)
    db.commit()
    return None
