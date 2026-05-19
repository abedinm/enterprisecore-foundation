"""Server-side helper for pushing notifications to a user."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType


def notify(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    type: NotificationType = NotificationType.INFO,
    link: Optional[str] = None,
) -> Notification:
    """Create a notification row. Caller commits."""
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    db.add(n)
    return n
