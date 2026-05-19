"""Audit log read-only endpoint (admin)."""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db
from app.core.permissions import require_admin
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogOut


router = APIRouter()


@router.get("", response_model=List[AuditLogOut], dependencies=[Depends(require_admin)])
def list_audit(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 1000))
    return list(db.scalars(stmt))
