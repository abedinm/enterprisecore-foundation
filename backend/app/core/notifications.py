"""Server-side helper for pushing notifications to a user.

Creates the DB row AND fans out over WebSocket if any clients are connected.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.core.ws_manager import manager as ws_manager


def notify(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    type: NotificationType = NotificationType.INFO,
    link: Optional[str] = None,
) -> Notification:
    """Create a notification row. Caller commits.

    After commit (when the row is durable), call `push_realtime` to fan out
    over WebSocket. We do NOT push here because the row isn't visible to other
    sessions until commit — pushing pre-commit can cause the client to re-fetch
    before the row is queryable.
    """
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    db.add(n)
    return n


def push_realtime(notification: Notification) -> None:
    """Fan-out helper — call after `db.commit()`."""
    ws_manager.push_to_user(notification.user_id, {
        "kind": "notification",
        "id": notification.id,
        "type": notification.type.value,
        "title": notification.title,
        "message": notification.message,
        "link": notification.link,
        "read": notification.read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    })
