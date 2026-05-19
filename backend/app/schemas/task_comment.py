"""Task comment schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskCommentOut(BaseModel):
    id: int
    task_id: int
    author_id: int
    author_name: str  # convenience: joined from user.full_name
    body: str
    created_at: datetime
    edited_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class TaskCommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)
