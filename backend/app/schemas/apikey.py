"""API key request/response schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, description="Human label, e.g. 'GitHub Actions'")


class APIKeyOut(BaseModel):
    """Returned for listing. Never exposes the raw key — only the prefix."""
    id: int
    user_id: int
    name: str
    prefix: str
    last_used_at: Optional[datetime] = None
    revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(APIKeyOut):
    """Identical to APIKeyOut but with the raw key — only returned at creation time."""
    raw_key: str = Field(description="Save this — it will never be shown again.")
