"""
Aggregate import so that simply importing `app.models` registers every
SQLAlchemy model on the Base metadata. New model files should be added here.
"""
from app.models.user import User, UserRole
from app.models.session import RefreshToken
from app.models.notification import Notification, NotificationType
from app.models.settings import UserSetting, SystemSetting
from app.models.audit import AuditLog
from app.models.department import Department
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.apikey import APIKey
from app.models.password_reset import OneTimeToken, OneTimeTokenType

__all__ = [
    "User", "UserRole",
    "RefreshToken",
    "Notification", "NotificationType",
    "UserSetting", "SystemSetting",
    "AuditLog",
    "Department",
    "Project", "ProjectStatus",
    "Task", "TaskStatus", "TaskPriority",
    "APIKey",
    "OneTimeToken", "OneTimeTokenType",
]
