"""Notification schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType = NotificationType.INFO
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    link: Optional[str] = Field(default=None, max_length=500)


class NotificationOut(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationsBatch(BaseModel):
    """Bulk operations payload."""
    ids: List[int]
