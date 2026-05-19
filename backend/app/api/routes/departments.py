"""Department CRUD (admins manage, all roles can read)."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user
from app.core.permissions import require_admin
from app.models.department import Department
from app.schemas.department import DepartmentOut, DepartmentCreate, DepartmentUpdate


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
    db.delete(row); db.commit()
    return None
