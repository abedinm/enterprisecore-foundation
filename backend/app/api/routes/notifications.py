"""Notification routes (per-user CRUD + admin broadcast)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_admin
from app.core.notifications import notify, push_realtime
from app.core.audit import log_action
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationOut, NotificationsBatch


router = APIRouter()


@router.get("", response_model=List[NotificationOut])
def list_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Most recent first. `unread_only=true` for the bell-badge dropdown."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(min(max(limit, 1), 200))
    return list(db.scalars(stmt))


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Cheap polling endpoint for the bell badge."""
    count = db.scalar(
        select(Notification).where(
            (Notification.user_id == current_user.id) & (Notification.read.is_(False))
        )
    )
    n = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read.is_(False)
    ).count()
    return {"count": n}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    n.read = True
    db.commit()
    return None


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    db.execute(
        update(Notification)
        .where((Notification.user_id == current_user.id) & (Notification.read.is_(False)))
        .values(read=True)
    )
    db.commit()
    return None


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(n)
    db.commit()
    return None


# ── Admin-only: send to a user, or broadcast ────────────────────────────────
@router.post("/send", response_model=NotificationOut, dependencies=[Depends(require_admin)])
def send_notification(
    payload: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Admin pushes a notification to a specific user."""
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="Target user not found")
    n = notify(
        db,
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        type=payload.type,
        link=payload.link,
    )
    log_action(
        db,
        user_id=current_user.id,
        action="notification.send",
        target_type="user",
        target_id=payload.user_id,
        detail=payload.title,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(n)
    push_realtime(n)
    return n


@router.post("/broadcast", dependencies=[Depends(require_admin)])
def broadcast(
    payload: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send the same notification to every active user."""
    users = list(db.scalars(select(User).where(User.is_active.is_(True))))
    created = [
        notify(db, user_id=u.id, title=payload.title, message=payload.message, type=payload.type, link=payload.link)
        for u in users
    ]
    log_action(
        db,
        user_id=current_user.id,
        action="notification.broadcast",
        detail=f"To {len(users)} users: {payload.title}",
        ip_address=client_ip(request),
    )
    db.commit()
    for n in created:
        db.refresh(n)
        push_realtime(n)
    return {"sent": len(users)}
