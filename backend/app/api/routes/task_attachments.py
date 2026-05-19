"""
Task attachments — upload, list, download, delete.

Storage: local filesystem under settings.uploads_dir. Files are stored with
a UUID name so two uploads of `report.pdf` don't collide. The original
filename is preserved in the DB and returned in the Content-Disposition
header on download.

Limits:
- MIME type must be in settings.allowed_upload_mimes
- Size capped at settings.max_upload_mb
- Visibility follows task visibility (project members + assignee)
"""

import os
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.config import settings
from app.core.audit import log_action
from app.models.user import User, UserRole
from app.models.task import Task
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task_attachment import TaskAttachment
from app.schemas.task_attachment import TaskAttachmentOut


router = APIRouter()


# ── Storage helpers ─────────────────────────────────────────────────────────
def _uploads_root() -> Path:
    root = Path(settings.uploads_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _allowed_mimes() -> set[str]:
    return {m.strip() for m in settings.allowed_upload_mimes.split(",") if m.strip()}


def _can_access_task(db: Session, current_user: User, task: Task) -> bool:
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER):
        return True
    if task.assignee_id == current_user.id:
        return True
    project = db.get(Project, task.project_id)
    if not project:
        return False
    if project.owner_id == current_user.id:
        return True
    return db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project.id) & (ProjectMember.user_id == current_user.id)
        )
    ) is not None


def _serialize(a: TaskAttachment) -> TaskAttachmentOut:
    return TaskAttachmentOut(
        id=a.id, task_id=a.task_id, uploader_id=a.uploader_id,
        uploader_name=a.uploader.full_name if a.uploader else "(unknown)",
        filename=a.filename, content_type=a.content_type,
        size_bytes=a.size_bytes, created_at=a.created_at,
    )


# ── Routes ──────────────────────────────────────────────────────────────────
@router.get("/{task_id}/attachments", response_model=List[TaskAttachmentOut])
def list_attachments(
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
        select(TaskAttachment).where(TaskAttachment.task_id == task_id).order_by(TaskAttachment.created_at.desc())
    ).all()
    return [_serialize(a) for a in rows]


@router.post("/{task_id}/attachments", response_model=TaskAttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    task_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(db, current_user, task):
        raise HTTPException(status_code=403, detail="Forbidden")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in _allowed_mimes():
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"MIME '{content_type}' not allowed. See system settings.",
        )

    # Stream to disk so we don't load huge files into memory.
    root = _uploads_root()
    safe_name = Path(file.filename or "upload").name  # strip any path component
    stored_filename = f"{uuid.uuid4().hex}-{safe_name[:100]}"
    target = root / stored_filename

    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {settings.max_upload_mb} MB limit",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {type(e).__name__}")

    row = TaskAttachment(
        task_id=task_id, uploader_id=current_user.id,
        filename=safe_name, stored_path=stored_filename,
        content_type=content_type, size_bytes=written,
    )
    db.add(row); db.flush()
    log_action(
        db, user_id=current_user.id, action="task.attachment_upload",
        target_type="task", target_id=task_id,
        detail=f"{safe_name} ({written} bytes)",
        ip_address=client_ip(request),
    )
    db.commit(); db.refresh(row)
    return _serialize(row)


@router.get("/{task_id}/attachments/{att_id}/download")
def download_attachment(
    task_id: int,
    att_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(db, current_user, task):
        raise HTTPException(status_code=403, detail="Forbidden")
    a = db.get(TaskAttachment, att_id)
    if not a or a.task_id != task_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    full_path = _uploads_root() / a.stored_path
    if not full_path.exists():
        raise HTTPException(status_code=410, detail="File missing from storage")
    return FileResponse(
        path=str(full_path),
        media_type=a.content_type,
        filename=a.filename,
    )


@router.delete("/{task_id}/attachments/{att_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    task_id: int,
    att_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    a = db.get(TaskAttachment, att_id)
    if not a or a.task_id != task_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # Uploader OR admin/manager can delete.
    if a.uploader_id != current_user.id and current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Best-effort file removal — the row is the source of truth for "exists?".
    try:
        (_uploads_root() / a.stored_path).unlink(missing_ok=True)
    except OSError:
        pass

    log_action(
        db, user_id=current_user.id, action="task.attachment_delete",
        target_type="task_attachment", target_id=a.id,
        ip_address=client_ip(request),
    )
    db.delete(a); db.commit()
    return None
