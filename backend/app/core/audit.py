"""Small helper for writing audit log rows from any service or route."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def log_action(
    db: Session,
    *,
    user_id: Optional[int],
    action: str,
    target_type: str = "",
    target_id: str = "",
    detail: str = "",
    ip_address: str = "",
) -> AuditLog:
    """Record an action. Caller is responsible for commit (usually piggybacks on existing tx)."""
    row = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        detail=detail,
        ip_address=ip_address,
    )
    db.add(row)
    return row
