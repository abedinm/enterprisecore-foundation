"""Project CRUD + member management.

Managers and Admins can create projects. The creator becomes the `owner`,
which is distinct from membership: an owner is implicitly a member with full
permissions. Other users get access only by being added as members.

Employees can read+modify projects where they are owner or member.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_manager
from app.core.audit import log_action
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectMemberRole
from app.schemas.project import ProjectOut, ProjectCreate, ProjectUpdate
from app.schemas.project_member import ProjectMemberOut, ProjectMemberAdd, ProjectMemberUpdate


router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────
def _is_member(db: Session, project_id: int, user_id: int) -> bool:
    return db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project_id) & (ProjectMember.user_id == user_id)
        )
    ) is not None


def _can_see(db: Session, current_user: User, project: Project) -> bool:
    """Admins and managers see all. Others must own or be a member."""
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        return True
    if project.owner_id == current_user.id:
        return True
    return _is_member(db, project.id, current_user.id)


def _can_modify(db: Session, current_user: User, project: Project) -> bool:
    """Owners, admins, and project Leads may modify the project."""
    if current_user.role == UserRole.ADMIN:
        return True
    if project.owner_id == current_user.id:
        return True
    lead = db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project.id)
            & (ProjectMember.user_id == current_user.id)
            & (ProjectMember.role == ProjectMemberRole.LEAD)
        )
    )
    return lead is not None


# ── Project CRUD ────────────────────────────────────────────────────────────
@router.get("", response_model=List[ProjectOut])
def list_projects(
    mine_only: bool = False,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Project)
    if not include_archived:
        stmt = stmt.where(Project.deleted_at.is_(None))
    if mine_only or current_user.role == UserRole.EMPLOYEE:
        # Owned OR membership in either case.
        member_project_ids = [
            r for (r,) in db.execute(
                select(ProjectMember.project_id).where(ProjectMember.user_id == current_user.id)
            )
        ]
        stmt = stmt.where(
            (Project.owner_id == current_user.id) | (Project.id.in_(member_project_ids or [-1]))
        )
    return list(db.scalars(stmt.order_by(Project.created_at.desc())))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_manager)])
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = Project(owner_id=current_user.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_see(db, current_user, row):
        raise HTTPException(status_code=403, detail="Forbidden")
    return row


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_modify(db, current_user, row):
        raise HTTPException(status_code=403, detail="Forbidden")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archive_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft-delete (preferred). Project stays in the DB; lists exclude it by default."""
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != UserRole.ADMIN and row.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    from datetime import datetime as _dt
    row.deleted_at = _dt.utcnow()
    log_action(
        db, user_id=current_user.id, action="project.archive",
        target_type="project", target_id=row.id, ip_address=client_ip(request),
    )
    db.commit(); db.refresh(row)
    return row


@router.post("/{project_id}/restore", response_model=ProjectOut)
def restore_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != UserRole.ADMIN and row.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if row.deleted_at is None:
        raise HTTPException(status_code=400, detail="Project is not archived")
    row.deleted_at = None
    log_action(
        db, user_id=current_user.id, action="project.restore",
        target_type="project", target_id=row.id, ip_address=client_ip(request),
    )
    db.commit(); db.refresh(row)
    return row


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Hard delete — admin only, irreversible. Prefer /archive."""
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can hard-delete projects")
    db.delete(row); db.commit()
    return None


# ── Member management ──────────────────────────────────────────────────────
@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_see(db, current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = db.scalars(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    ).all()
    return [
        ProjectMemberOut(
            id=m.id, project_id=m.project_id, user_id=m.user_id,
            role=m.role, added_at=m.added_at,
            user_full_name=m.user.full_name, user_email=m.user.email,
        )
        for m in rows
    ]


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int,
    payload: ProjectMemberAdd,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_modify(db, current_user, project):
        raise HTTPException(status_code=403, detail="Only project owners, admins, or leads can add members")

    target = db.get(User, payload.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if _is_member(db, project_id, payload.user_id):
        raise HTTPException(status_code=409, detail="Already a member")

    row = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
    db.add(row); db.flush()
    log_action(
        db, user_id=current_user.id, action="project.member_add",
        target_type="project", target_id=project_id,
        detail=f"Added {target.email} as {payload.role.value}",
        ip_address=client_ip(request),
    )
    db.commit(); db.refresh(row)
    return ProjectMemberOut(
        id=row.id, project_id=row.project_id, user_id=row.user_id,
        role=row.role, added_at=row.added_at,
        user_full_name=target.full_name, user_email=target.email,
    )


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
def update_member_role(
    project_id: int,
    user_id: int,
    payload: ProjectMemberUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_modify(db, current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")
    row = db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project_id) & (ProjectMember.user_id == user_id)
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    row.role = payload.role
    log_action(
        db, user_id=current_user.id, action="project.member_update",
        target_type="project", target_id=project_id,
        detail=f"User {user_id} role -> {payload.role.value}",
        ip_address=client_ip(request),
    )
    db.commit(); db.refresh(row)
    return ProjectMemberOut(
        id=row.id, project_id=row.project_id, user_id=row.user_id,
        role=row.role, added_at=row.added_at,
        user_full_name=row.user.full_name, user_email=row.user.email,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    # Allow self-removal even without modify rights.
    if current_user.id != user_id and not _can_modify(db, current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")
    row = db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project_id) & (ProjectMember.user_id == user_id)
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(row)
    log_action(
        db, user_id=current_user.id, action="project.member_remove",
        target_type="project", target_id=project_id,
        detail=f"Removed user {user_id}",
        ip_address=client_ip(request),
    )
    db.commit()
    return None
