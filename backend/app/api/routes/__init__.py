"""
Mount all route modules. The top-level `app.main` imports `api_router` from here.
"""
from fastapi import APIRouter

from app.api.routes import (
    auth, users, notifications, settings, departments,
    projects, tasks, audit, system, apikeys, auth_flows, two_factor,
    task_comments, task_attachments, search, activity,
)

api_router = APIRouter()
api_router.include_router(auth.router,             prefix="/auth",          tags=["auth"])
api_router.include_router(auth_flows.router,       prefix="/auth",          tags=["auth"])
api_router.include_router(two_factor.router,       prefix="/2fa",           tags=["2fa"])
api_router.include_router(users.router,            prefix="/users",         tags=["users"])
api_router.include_router(notifications.router,    prefix="/notifications", tags=["notifications"])
api_router.include_router(settings.router,         prefix="/settings",      tags=["settings"])
api_router.include_router(departments.router,      prefix="/departments",   tags=["departments"])
api_router.include_router(projects.router,         prefix="/projects",      tags=["projects"])
api_router.include_router(tasks.router,            prefix="/tasks",         tags=["tasks"])
# task_comments + task_attachments mount under /tasks for nested paths.
api_router.include_router(task_comments.router,    prefix="/tasks",         tags=["tasks"])
api_router.include_router(task_attachments.router, prefix="/tasks",         tags=["tasks"])
api_router.include_router(search.router,           prefix="/search",        tags=["search"])
api_router.include_router(activity.router,         prefix="/activity",      tags=["activity"])
api_router.include_router(audit.router,            prefix="/audit",         tags=["audit"])
api_router.include_router(system.router,           prefix="/system",        tags=["system"])
api_router.include_router(apikeys.router,          prefix="/api-keys",      tags=["api-keys"])
