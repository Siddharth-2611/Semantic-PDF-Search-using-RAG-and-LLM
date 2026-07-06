from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Documents ----------

class DocumentOut(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Chat / RAG ----------

class ChatRequest(BaseModel):
    query: str
    document_id: str | None = None  # optional: scope search to one document
    top_k: int = 5


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    page_number: int
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
