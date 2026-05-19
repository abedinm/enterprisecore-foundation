"""
First-run bootstrap:
- Seed the system admin if no users exist
- Seed a few default system settings
- Seed default departments

Idempotent — safe to call on every startup.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.settings import SystemSetting
from app.models.department import Department


_DEFAULT_SYSTEM_SETTINGS = [
    ("registration.open", "true",                       "Allow self-service signup"),
    ("notifications.email_enabled", "false",            "Send notification emails (requires SMTP)"),
    ("ui.welcome_message", "Welcome to EnterpriseCore", "Banner text on the dashboard"),
    ("ui.maintenance_mode", "false",                    "Take the app offline for non-admins"),
]


_DEFAULT_DEPARTMENTS = [
    ("Engineering",  "Builds and operates the platform"),
    ("Product",      "Owns the roadmap and feature design"),
    ("Operations",   "Day-to-day running of the business"),
    ("People",       "HR, recruiting, and culture"),
]


def seed(db: Session) -> dict:
    summary = {"admin_seeded": False, "departments_seeded": 0, "settings_seeded": 0}

    if db.query(User).count() == 0:
        admin = User(
            email=settings.first_admin_email,
            full_name=settings.first_admin_name,
            hashed_password=hash_password(settings.first_admin_password),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        summary["admin_seeded"] = True

    for key, value, description in _DEFAULT_SYSTEM_SETTINGS:
        if not db.scalar(select(SystemSetting).where(SystemSetting.key == key)):
            db.add(SystemSetting(key=key, value=value, description=description))
            summary["settings_seeded"] += 1

    for name, description in _DEFAULT_DEPARTMENTS:
        if not db.scalar(select(Department).where(Department.name == name)):
            db.add(Department(name=name, description=description))
            summary["departments_seeded"] += 1

    db.commit()
    return summary
