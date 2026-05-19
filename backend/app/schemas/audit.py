"""Audit log schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    target_type: str
    target_id: str
    detail: str
    ip_address: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
