"""
Cross-domain search.

GET /search?q=foo                  -> all entities the caller can see
GET /search?q=foo&scope=users      -> restrict to one kind

Visibility:
- Users:        admin-only (don't leak the directory to everyone).
- Departments:  any authenticated user.
- Projects:     admin/manager all; others only projects they own or are members of.
- Tasks:        same scope as the parent project.
- Comments:     same scope as the parent task.

This is a substring/ILIKE search — fine for SQLite at the scales this app
is targeted at. For tens of millions of rows, swap for FTS5 or external.
"""

from typing import List, Optional, Set
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.api.deps import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.task_comment import TaskComment
from app.schemas.search import SearchHit, SearchResponse


router = APIRouter()


def _visible_project_ids(db: Session, current_user: User) -> Optional[Set[int]]:
    """Returns the set of project ids the user can see, or None for 'all'."""
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        return None  # signal: no filter
    owned = {p_id for (p_id,) in db.execute(select(Project.id).where(Project.owner_id == current_user.id))}
    member = {p_id for (p_id,) in db.execute(select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id))}
    return owned | member


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=1, max_length=200),
    scope: str = Query("all", pattern="^(all|users|departments|projects|tasks|comments)$"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    like = f"%{q.strip()}%"
    hits: List[SearchHit] = []
    visible_pids = _visible_project_ids(db, current_user)

    # ── Users (admin only) ──────────────────────────────────────────────────
    if scope in ("all", "users") and current_user.role == UserRole.ADMIN:
        rows = db.scalars(
            select(User)
            .where(or_(User.email.ilike(like), User.full_name.ilike(like)))
            .limit(limit)
        )
        for u in rows:
            hits.append(SearchHit(
                kind="user", id=u.id, title=u.full_name,
                subtitle=f"{u.email} · {u.role.value}",
                link=f"/users", matched_at=u.created_at,
            ))

    # ── Departments ─────────────────────────────────────────────────────────
    if scope in ("all", "departments"):
        rows = db.scalars(
            select(Department)
            .where(or_(Department.name.ilike(like), Department.description.ilike(like)))
            .limit(limit)
        )
        for d in rows:
            hits.append(SearchHit(
                kind="department", id=d.id, title=d.name,
                subtitle=d.description, link="/departments",
                matched_at=d.created_at,
            ))

    # ── Projects ────────────────────────────────────────────────────────────
    if scope in ("all", "projects"):
        stmt = select(Project).where(
            or_(Project.name.ilike(like), Project.description.ilike(like))
        )
        if visible_pids is not None:
            stmt = stmt.where(Project.id.in_(visible_pids or {-1}))
        rows = db.scalars(stmt.limit(limit))
        for p in rows:
            hits.append(SearchHit(
                kind="project", id=p.id, title=p.name,
                subtitle=f"status: {p.status.value}",
                link="/projects", matched_at=p.created_at,
            ))

    # ── Tasks ───────────────────────────────────────────────────────────────
    if scope in ("all", "tasks"):
        stmt = select(Task).where(
            or_(Task.title.ilike(like), Task.description.ilike(like))
        )
        if visible_pids is not None:
            stmt = stmt.where(or_(
                Task.project_id.in_(visible_pids or {-1}),
                Task.assignee_id == current_user.id,
            ))
        rows = db.scalars(stmt.limit(limit))
        for t in rows:
            hits.append(SearchHit(
                kind="task", id=t.id, title=t.title,
                subtitle=f"{t.status.value} · {t.priority.value}",
                link="/tasks", matched_at=t.created_at,
            ))

    # ── Comments ────────────────────────────────────────────────────────────
    if scope in ("all", "comments"):
        stmt = select(TaskComment).where(TaskComment.body.ilike(like))
        if visible_pids is not None:
            # Comment is visible if its task's project is visible OR the user is the assignee.
            stmt = stmt.join(Task, Task.id == TaskComment.task_id).where(
                or_(
                    Task.project_id.in_(visible_pids or {-1}),
                    Task.assignee_id == current_user.id,
                )
            )
        rows = db.scalars(stmt.limit(limit))
        for c in rows:
            snippet = c.body[:120] + ("…" if len(c.body) > 120 else "")
            hits.append(SearchHit(
                kind="comment", id=c.id, title=snippet,
                subtitle=f"on task #{c.task_id}",
                link=f"/tasks", matched_at=c.created_at,
            ))

    # Newest matches first, then cap.
    hits.sort(key=lambda h: h.matched_at or 0, reverse=True)
    hits = hits[:limit]
    return SearchResponse(query=q, total=len(hits), results=hits)
