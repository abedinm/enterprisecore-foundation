"""
Activity feed — chronological event stream backed by the audit log.

GET /activity                       -> last 50 events the caller can see
GET /activity?project_id=X          -> filter to a project
GET /activity?mine=true             -> only the caller's actions

Visibility rules:
- Admins see everything.
- Managers see everything (they typically need full org visibility).
- Employees see:
    * their own actions
    * actions whose target is a project they own/member-of
- Non-admin requests for project_id they don't have visibility into return 403.
"""

from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_

from app.api.deps import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.audit import AuditLogOut


router = APIRouter()


def _visible_project_ids(db: Session, current_user: User) -> Optional[Set[int]]:
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        return None
    owned = {p_id for (p_id,) in db.execute(select(Project.id).where(Project.owner_id == current_user.id))}
    member = {p_id for (p_id,) in db.execute(select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id))}
    return owned | member


@router.get("", response_model=List[AuditLogOut])
def activity_feed(
    project_id: Optional[int] = Query(None, ge=1),
    mine: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    visible_pids = _visible_project_ids(db, current_user)

    stmt = select(AuditLog)

    # ── project_id filter ──────────────────────────────────────────────────
    if project_id is not None:
        if visible_pids is not None and project_id not in visible_pids:
            raise HTTPException(status_code=403, detail="No access to this project")
        stmt = stmt.where(
            and_(AuditLog.target_type == "project", AuditLog.target_id == str(project_id))
        )

    # ── visibility scoping ─────────────────────────────────────────────────
    if visible_pids is not None:
        # Employee: their own actions OR actions targeting projects they can see.
        if visible_pids:
            project_target_filter = and_(
                AuditLog.target_type == "project",
                AuditLog.target_id.in_([str(i) for i in visible_pids]),
            )
            stmt = stmt.where(or_(AuditLog.user_id == current_user.id, project_target_filter))
        else:
            stmt = stmt.where(AuditLog.user_id == current_user.id)

    if mine:
        stmt = stmt.where(AuditLog.user_id == current_user.id)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))
