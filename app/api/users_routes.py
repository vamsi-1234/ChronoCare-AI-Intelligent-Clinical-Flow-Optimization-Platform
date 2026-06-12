"""User management endpoints (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.orm_models import User
from app.services.auth import hash_password, require_roles

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    physician_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|physician|front_desk)$")
    physician_id: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


@router.get("", response_model=list[UserOut], summary="List all users (admin only)")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[User]:
    return db.query(User).order_by(User.full_name).all()


@router.patch("/{user_id}", response_model=UserOut, summary="Update user (admin only)")
def update_user(
    user_id: int,
    body: UpdateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.physician_id is not None:
        user.physician_id = body.physician_id
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204, summary="Deactivate user (admin only)")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
) -> None:
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
