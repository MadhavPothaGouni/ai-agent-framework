"""Authentication routes: signup, login, token issuance.

Phase 1 stub — replace the in-memory user store with a real DB-backed
user model once app/db is wired up.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

# TODO(phase1): replace with a real user table
_FAKE_USER_DB: dict[str, str] = {}


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@router.post("/signup", response_model=TokenResponse)
def signup(req: SignupRequest) -> TokenResponse:
    if req.email in _FAKE_USER_DB:
        raise HTTPException(status_code=400, detail="User already exists")
    _FAKE_USER_DB[req.email] = req.password  # TODO: hash with passlib
    return TokenResponse(access_token=_create_access_token(req.email))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    stored = _FAKE_USER_DB.get(req.email)
    if stored is None or stored != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=_create_access_token(req.email))
