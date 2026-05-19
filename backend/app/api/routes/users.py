"""User management routes."""

import csv
import io
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_admin
from app.core.security import hash_password, verify_password
from app.core.audit import log_action
from app.models.user import User
from app.schemas.user import (
    UserOut, UserListItem, UserUpdate, UserAdminUpdate, UserAdminCreate, PasswordChange,
)


router = APIRouter()


@router.get("", response_model=List[UserListItem], dependencies=[Depends(require_admin)])
def list_users(
    q: Optional[str] = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    """Admin-only listing. Excludes archived by default; pass include_archived=true to see them."""
    stmt = select(User)
    if not include_archived:
        stmt = stmt.where(User.deleted_at.is_(None))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
    stmt = stmt.order_by(User.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/export", dependencies=[Depends(require_admin)])
def export_users(
    format: str = "csv",
    db: Session = Depends(get_db),
):
    """Admin-only export. `format=csv` (default) or `format=json`.
    Includes everything safe to export — never password hashes."""
    users = list(db.scalars(select(User).order_by(User.id)))
    rows = [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "department_id": u.department_id,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else "",
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]

    if format == "json":
        buf = io.BytesIO(json.dumps(rows, indent=2).encode("utf-8"))
        return StreamingResponse(
            buf, media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="users.json"'},
        )

    # CSV (default)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["id"])
    writer.writeheader()
    writer.writerows(rows)
    csv_bytes = io.BytesIO(buf.getvalue().encode("utf-8"))
    return StreamingResponse(
        csv_bytes, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="users.csv"'},
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def admin_create_user(
    payload: UserAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin-only: create a user with a specific role bypassing self-registration."""
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        is_verified=payload.is_verified,
        department_id=payload.department_id,
    )
    db.add(user)
    db.flush()
    log_action(
        db,
        user_id=current_user.id,
        action="user.admin_create",
        target_type="user",
        target_id=user.id,
        detail=f"Created {user.email} as {user.role.value}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


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


@router.post("/{user_id}/archive", response_model=UserOut, dependencies=[Depends(require_admin)])
def archive_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft-delete a user. Sets deleted_at and is_active=False, revokes sessions.
    Use /restore to bring them back. The system admin (id=1) cannot be archived."""
    if user_id == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot archive the system admin")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.deleted_at = datetime.utcnow()
    user.is_active = False
    for r in user.refresh_tokens:
        r.revoked = True
    log_action(
        db, user_id=current_user.id, action="user.archive",
        target_type="user", target_id=user.id,
        detail=f"Archived {user.email}", ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/restore", response_model=UserOut, dependencies=[Depends(require_admin)])
def restore_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reverse an archive. The user is reactivated."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not archived")
    user.deleted_at = None
    user.is_active = True
    log_action(
        db, user_id=current_user.id, action="user.restore",
        target_type="user", target_id=user.id,
        detail=f"Restored {user.email}", ip_address=client_ip(request),
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
