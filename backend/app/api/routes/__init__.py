"""
Mount all route modules. The top-level `app.main` imports `api_router` from here.
"""
from fastapi import APIRouter

from app.api.routes import auth, users, notifications, settings, departments, projects, tasks, audit, system

api_router = APIRouter()
api_router.include_router(auth.router,          prefix="/auth",          tags=["auth"])
api_router.include_router(users.router,         prefix="/users",         tags=["users"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(settings.router,      prefix="/settings",      tags=["settings"])
api_router.include_router(departments.router,   prefix="/departments",   tags=["departments"])
api_router.include_router(projects.router,      prefix="/projects",      tags=["projects"])
api_router.include_router(tasks.router,         prefix="/tasks",         tags=["tasks"])
api_router.include_router(audit.router,         prefix="/audit",         tags=["audit"])
api_router.include_router(system.router,        prefix="/system",        tags=["system"])
