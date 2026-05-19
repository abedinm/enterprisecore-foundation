"""Aggregate Pydantic schemas."""
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenPair, TokenRefreshRequest, TokenPayload
)
from app.schemas.user import UserOut, UserUpdate, UserAdminUpdate, UserListItem, PasswordChange
from app.schemas.notification import NotificationCreate, NotificationOut, NotificationsBatch
from app.schemas.settings import (
    UserSettingItem, UserSettingsUpdate, SystemSettingOut, SystemSettingUpdate
)
from app.schemas.department import DepartmentOut, DepartmentCreate, DepartmentUpdate
from app.schemas.project import ProjectOut, ProjectCreate, ProjectUpdate
from app.schemas.task import TaskOut, TaskCreate, TaskUpdate
from app.schemas.audit import AuditLogOut

__all__ = [
    "LoginRequest", "RegisterRequest", "TokenPair", "TokenRefreshRequest", "TokenPayload",
    "UserOut", "UserUpdate", "UserAdminUpdate", "UserListItem", "PasswordChange",
    "NotificationCreate", "NotificationOut", "NotificationsBatch",
    "UserSettingItem", "UserSettingsUpdate", "SystemSettingOut", "SystemSettingUpdate",
    "DepartmentOut", "DepartmentCreate", "DepartmentUpdate",
    "ProjectOut", "ProjectCreate", "ProjectUpdate",
    "TaskOut", "TaskCreate", "TaskUpdate",
    "AuditLogOut",
]
