"""Auth endpoints: login, me, register (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.orm_models import User
from app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Schemas ───────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: str
    physician_id: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(..., examples=["dr.smith@clinic.com"])
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = Field(default="front_desk", pattern="^(admin|physician|front_desk)$")
    physician_id: str | None = Field(default=None)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    physician_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter_by(email=form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        physician_id=user.physician_id,
    )


@router.get("/me", response_model=UserOut, summary="Get current user info")
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only)",
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> User:
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        physician_id=body.physician_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
