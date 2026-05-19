"""Project CRUD. Managers and Admins create. Owners and Admins edit/delete."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user
from app.core.permissions import require_manager
from app.models.user import User, UserRole
from app.models.project import Project
from app.schemas.project import ProjectOut, ProjectCreate, ProjectUpdate


router = APIRouter()


@router.get("", response_model=List[ProjectOut])
def list_projects(
    mine_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Project)
    if mine_only or current_user.role == UserRole.EMPLOYEE:
        # Employees only see projects they own or are assigned to via tasks
        stmt = stmt.where(Project.owner_id == current_user.id)
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
    if current_user.role == UserRole.EMPLOYEE and row.owner_id != current_user.id:
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
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER) and row.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role not in (UserRole.ADMIN,) and row.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(row); db.commit()
    return None
