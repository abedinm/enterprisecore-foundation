"""
Task comments — discussion thread on a task.

Visibility follows project visibility: a user can comment on a task if they
can see its parent project. Authors can edit/delete their own comments;
admins/managers can delete any.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.audit import log_action
from app.models.user import User, UserRole
from app.models.task import Task
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task_comment import TaskComment
from app.schemas.task_comment import TaskCommentOut, TaskCommentCreate, TaskCommentUpdate


router = APIRouter()


def _can_access_task(db: Session, current_user: User, task: Task) -> bool:
    """Same rule as projects: admin/manager always, otherwise owner OR project member OR assignee."""
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        return True
    if task.assignee_id == current_user.id:
        return True
    project = db.get(Project, task.project_id)
    if not project:
        return False
    if project.owner_id == current_user.id:
        return True
    member = db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project.id) & (ProjectMember.user_id == current_user.id)
        )
    )
    return member is not None


def _serialize(c: TaskComment) -> TaskCommentOut:
    return TaskCommentOut(
        id=c.id, task_id=c.task_id, author_id=c.author_id,
        author_name=c.author.full_name if c.author else "(unknown)",
        body=c.body, created_at=c.created_at, edited_at=c.edited_at,
    )


@router.get("/{task_id}/comments", response_model=List[TaskCommentOut])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(db, current_user, task):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = db.scalars(
        select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at)
    ).all()
    return [_serialize(c) for c in rows]


@router.post("/{task_id}/comments", response_model=TaskCommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    task_id: int,
    body: TaskCommentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(db, current_user, task):
        raise HTTPException(status_code=403, detail="Forbidden")
    c = TaskComment(task_id=task_id, author_id=current_user.id, body=body.body)
    db.add(c); db.flush()
    log_action(
        db, user_id=current_user.id, action="task.comment_create",
        target_type="task", target_id=task_id, ip_address=client_ip(request),
    )
    db.commit(); db.refresh(c)
    return _serialize(c)


@router.patch("/{task_id}/comments/{comment_id}", response_model=TaskCommentOut)
def update_comment(
    task_id: int,
    comment_id: int,
    body: TaskCommentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.get(TaskComment, comment_id)
    if not c or c.task_id != task_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if c.author_id != current_user.id:
        # Only the author can edit. (Admins must delete + recreate to preserve attribution.)
        raise HTTPException(status_code=403, detail="Only the author can edit")
    c.body = body.body
    c.edited_at = datetime.utcnow()
    log_action(
        db, user_id=current_user.id, action="task.comment_update",
        target_type="task_comment", target_id=c.id, ip_address=client_ip(request),
    )
    db.commit(); db.refresh(c)
    return _serialize(c)


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    task_id: int,
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.get(TaskComment, comment_id)
    if not c or c.task_id != task_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    # Author OR admin/manager can delete.
    if c.author_id != current_user.id and current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Forbidden")
    log_action(
        db, user_id=current_user.id, action="task.comment_delete",
        target_type="task_comment", target_id=c.id, ip_address=client_ip(request),
    )
    db.delete(c); db.commit()
    return None
