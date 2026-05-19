"""User management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_admin
from app.core.security import hash_password, verify_password
from app.core.audit import log_action
from app.models.user import User
from app.schemas.user import UserOut, UserListItem, UserUpdate, UserAdminUpdate, PasswordChange


router = APIRouter()


@router.get("", response_model=List[UserListItem], dependencies=[Depends(require_admin)])
def list_users(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Admin-only listing. Optional case-insensitive search on email or name."""
    stmt = select(User)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
    stmt = stmt.order_by(User.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Anyone can read their own record; only admins read others."""
    if user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    patch: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update fields the user is allowed to change on their own record."""
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    log_action(db, user_id=current_user.id, action="user.update_self", ip_address=client_ip(request))
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: PasswordChange,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Self-service password change. Old password is verified."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    # Revoke all sessions for safety.
    for r in current_user.refresh_tokens:
        r.revoked = True
    log_action(db, user_id=current_user.id, action="user.password_change", ip_address=client_ip(request))
    db.commit()
    return None


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def admin_update_user(
    user_id: int,
    patch: UserAdminUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin can edit role, active flag, department, etc."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    log_action(
        db,
        user_id=current_user.id,
        action="user.admin_update",
        target_type="user",
        target_id=user.id,
        detail=str(patch.model_dump(exclude_unset=True)),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def admin_delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Hard-delete. The first admin (id=1) cannot be deleted."""
    if user_id == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the system admin")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    log_action(
        db,
        user_id=current_user.id,
        action="user.delete",
        target_type="user",
        target_id=user.id,
        detail=f"Deleted {user.email}",
        ip_address=client_ip(request),
    )
    db.delete(user)
    db.commit()
    return None
