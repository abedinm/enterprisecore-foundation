"""Task attachment schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TaskAttachmentOut(BaseModel):
    id: int
    task_id: int
    uploader_id: int
    uploader_name: str  # joined for display
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
