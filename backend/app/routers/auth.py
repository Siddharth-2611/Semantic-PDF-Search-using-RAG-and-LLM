import random
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.device_info import get_client_ip, get_device_name, get_location
from app.email_utils import send_login_notification_email, send_verification_email
from app.models import User
from app.schemas import (
    RegisterResponse,
    ResendVerificationRequest,
    Token,
    UserCreate,
    UserLogin,
    VerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_code() -> str:
    return f"{random.randint(0, 9999):04d}"


def _issue_verification_code(user: User, db: Session, background_tasks: BackgroundTasks):
    code = _generate_code()
    user.verification_code = code
    user.verification_code_expires_at = datetime.utcnow() + timedelta(
        minutes=settings.verification_code_expire_minutes
    )
    db.commit()
    background_tasks.add_task(send_verification_email, user.email, code)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _issue_verification_code(user, db, background_tasks)

    return RegisterResponse(
        message="Account created. Check your email for a 4-digit verification code.",
        email=user.email,
    )


@router.post("/verify", response_model=Token)
def verify_email(payload: VerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account is already verified")
    if not user.verification_code or user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Incorrect verification code")
    if not user.verification_code_expires_at or user.verification_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code has expired")

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    db.commit()

    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@router.post("/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account is already verified")

    _issue_verification_code(user, db, background_tasks)
    return {"message": "A new verification code has been sent."}


@router.post("/login", response_model=Token)
def login(
    payload: UserLogin,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Use /auth/resend-verification if needed.",
        )

    # Login notification: resolving geolocation is a network call, so it
    # runs as a background task after the token is already returned —
    # the user isn't kept waiting on it.
    ip_address = get_client_ip(request)
    device_name = get_device_name(request.headers.get("user-agent"))
    background_tasks.add_task(
        _send_login_notification, user.email, device_name, ip_address
    )

    token = create_access_token(subject=user.id)
    return Token(access_token=token)


def _send_login_notification(email: str, device_name: str, ip_address: str):
    location = get_location(ip_address)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    send_login_notification_email(email, device_name, location, ip_address, timestamp)
