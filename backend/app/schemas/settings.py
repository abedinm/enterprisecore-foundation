"""Settings schemas."""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class UserSettingItem(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = ""


class UserSettingsUpdate(BaseModel):
    items: List[UserSettingItem]


class SystemSettingOut(BaseModel):
    id: int
    key: str
    value: str
    description: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemSettingUpdate(BaseModel):
    value: str
