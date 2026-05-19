"""
API key management.

Flow:
- POST  /api-keys          → returns the raw key ONCE; stores only its hash.
- GET   /api-keys          → list your own keys (admin sees all).
- POST  /api-keys/{id}/revoke → revoke (soft-delete; can't be un-revoked).
- DELETE /api-keys/{id}    → hard delete.

Users with role Developer or Admin may create keys.
Once created, a key may be used as `Authorization: Bearer <raw_key>` against
endpoints that accept it (see app/api/deps.py `get_api_key_user`).
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_developer
from app.core.security import generate_api_key
from app.core.audit import log_action
from app.models.user import User, UserRole
from app.models.apikey import APIKey
from app.schemas.apikey import APIKeyCreate, APIKeyOut, APIKeyCreateResponse


router = APIRouter()


@router.get("", response_model=List[APIKeyOut])
def list_my_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admins see all keys; everyone else only sees their own."""
    stmt = select(APIKey)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(APIKey.user_id == current_user.id)
    return list(db.scalars(stmt.order_by(APIKey.created_at.desc())))


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_developer)])
def create_key(
    payload: APIKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new API key. The raw value is shown ONCE here — never again."""
    raw, prefix, hashed = generate_api_key()
    row = APIKey(
        user_id=current_user.id,
        name=payload.name,
        hashed_key=hashed,
        prefix=prefix,
    )
    db.add(row)
    db.flush()
    log_action(
        db,
        user_id=current_user.id,
        action="apikey.create",
        target_type="apikey",
        target_id=row.id,
        detail=f"name={payload.name} prefix={prefix}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(row)

    # Stitch together the response: persisted row fields + raw_key (returned exactly once).
    return APIKeyCreateResponse(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        prefix=row.prefix,
        last_used_at=row.last_used_at,
        revoked=row.revoked,
        created_at=row.created_at,
        raw_key=raw,
    )


@router.post("/{key_id}/revoke", response_model=APIKeyOut)
def revoke_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(APIKey, key_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if row.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your key")
    row.revoked = True
    log_action(
        db,
        user_id=current_user.id,
        action="apikey.revoke",
        target_type="apikey",
        target_id=row.id,
        detail=f"prefix={row.prefix}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(APIKey, key_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if row.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your key")
    log_action(
        db,
        user_id=current_user.id,
        action="apikey.delete",
        target_type="apikey",
        target_id=row.id,
        detail=f"prefix={row.prefix}",
        ip_address=client_ip(request),
    )
    db.delete(row)
    db.commit()
    return None
