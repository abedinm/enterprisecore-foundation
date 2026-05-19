"""Search response schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SearchHit(BaseModel):
    kind: str           # "user" | "project" | "task" | "comment" | "department"
    id: int
    title: str          # human-readable label
    subtitle: str = ""  # secondary line (email, status, parent project, etc.)
    link: str           # frontend route to navigate to
    matched_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchHit]
