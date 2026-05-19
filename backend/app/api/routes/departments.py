"""Department CRUD + member assignment (admins manage, all roles can read)."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_admin
from app.core.audit import log_action
from app.models.user import User
from app.models.department import Department
from app.schemas.department import DepartmentOut, DepartmentCreate, DepartmentUpdate
from app.schemas.user import UserListItem


router = APIRouter()


@router.get("", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _user=Depends(get_current_active_user)):
    return list(db.scalars(select(Department).order_by(Department.name)))


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Department).where(Department.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department exists")
    row = Department(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.patch("/{dept_id}", response_model=DepartmentOut, dependencies=[Depends(require_admin)])
def update_department(dept_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)):
    row = db.get(Department, dept_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    row = db.get(Department, dept_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    # Detach all members rather than cascading their deletion.
    for u in row.members:
        u.department_id = None
    db.delete(row); db.commit()
    return None


# ── Member management ──────────────────────────────────────────────────────
@router.get("/{dept_id}/members", response_model=List[UserListItem])
def list_members(
    dept_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_active_user),
):
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return list(db.scalars(select(User).where(User.department_id == dept_id).order_by(User.full_name)))


@router.post("/{dept_id}/members/{user_id}", response_model=UserListItem, dependencies=[Depends(require_admin)])
def add_member(
    dept_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Assign a user to this department (replaces any existing assignment)."""
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.department_id = dept_id
    log_action(
        db,
        user_id=current_user.id,
        action="department.member_add",
        target_type="user",
        target_id=user.id,
        detail=f"Added to dept {dept.name}",
        ip_address=client_ip(request),
    )
    db.commit(); db.refresh(user)
    return user


@router.delete("/{dept_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def remove_member(
    dept_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Unassign a user from this department."""
    user = db.get(User, user_id)
    if not user or user.department_id != dept_id:
        raise HTTPException(status_code=404, detail="User is not in this department")
    user.department_id = None
    log_action(
        db,
        user_id=current_user.id,
        action="department.member_remove",
        target_type="user",
        target_id=user.id,
        detail=f"Removed from dept {dept_id}",
        ip_address=client_ip(request),
    )
    db.commit()
    return None
