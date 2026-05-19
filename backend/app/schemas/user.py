"""User-facing schemas (no password fields leak out)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole


class UserOut(BaseModel):
    """Self-view (or any view that doesn't include sensitive admin fields)."""
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Lightweight view for /users listings."""
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    department_id: Optional[int] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Fields a user is allowed to change about themselves."""
    full_name: Optional[str] = Field(default=None, max_length=120)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=40)


class UserAdminUpdate(BaseModel):
    """Fields only Admins can modify on any user."""
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    department_id: Optional[int] = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
