"""Task CRUD inside a Project."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.models.project import Project
from app.schemas.task import TaskOut, TaskCreate, TaskUpdate


router = APIRouter()


def _can_see_project(current_user: User, project: Project) -> bool:
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER, UserRole.DEVELOPER):
        return True
    return project.owner_id == current_user.id


@router.get("", response_model=List[TaskOut])
def list_tasks(
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    status_filter: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter)
    # Employees only see tasks they're assigned to or own the project for.
    if current_user.role == UserRole.EMPLOYEE:
        stmt = stmt.where(Task.assignee_id == current_user.id)
    return list(db.scalars(stmt.order_by(Task.created_at.desc())))


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_see_project(current_user, project):
        raise HTTPException(status_code=403, detail="Cannot add tasks to this project")
    row = Task(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Task, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    project = db.get(Project, row.project_id)
    if not project or not _can_see_project(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")
    if current_user.role == UserRole.EMPLOYEE and row.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.get(Task, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(row); db.commit()
    return None
