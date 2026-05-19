"""System-wide health, version, dashboard stats."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.api.deps import get_db, get_current_active_user
from app.config import settings
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.notification import Notification


router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness probe — never requires auth."""
    return {"status": "ok", "app": settings.app_name, "time": datetime.utcnow().isoformat()}


@router.get("/info")
def info():
    """Public app metadata for the client to render headers and version chips."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "features": ["auth", "rbac", "notifications", "settings", "audit", "projects", "tasks"],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Aggregate stats for the home dashboard widgets."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    tasks_done = db.query(Task).filter(Task.status == TaskStatus.DONE).count()
    unread_notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read.is_(False)
    ).count()

    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_7d = db.query(User).filter(User.created_at >= week_ago).count()

    role_breakdown = {}
    for r in UserRole:
        role_breakdown[r.value] = db.query(User).filter(User.role == r).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_last_7d": new_users_7d,
            "by_role": role_breakdown,
        },
        "projects": {"total": total_projects},
        "tasks": {
            "total": total_tasks,
            "done": tasks_done,
            "completion_rate": round(tasks_done / total_tasks * 100, 1) if total_tasks else 0.0,
        },
        "my_unread_notifications": unread_notifs,
    }
