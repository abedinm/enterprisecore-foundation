"""User-level and system-level settings."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user, client_ip
from app.core.permissions import require_admin
from app.core.audit import log_action
from app.models.user import User
from app.models.settings import UserSetting, SystemSetting
from app.schemas.settings import (
    UserSettingItem, UserSettingsUpdate, SystemSettingOut, SystemSettingUpdate
)


router = APIRouter()


# ── User settings (key/value bag per user) ──────────────────────────────────
@router.get("/me", response_model=List[UserSettingItem])
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows = db.scalars(select(UserSetting).where(UserSetting.user_id == current_user.id))
    return [UserSettingItem(key=r.key, value=r.value) for r in rows]


@router.put("/me", response_model=List[UserSettingItem])
def upsert_my_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk upsert. Keys missing from payload are NOT deleted (use DELETE for that)."""
    existing = {r.key: r for r in db.scalars(select(UserSetting).where(UserSetting.user_id == current_user.id))}
    for item in payload.items:
        if item.key in existing:
            existing[item.key].value = item.value
        else:
            db.add(UserSetting(user_id=current_user.id, key=item.key, value=item.value))
    db.commit()
    rows = db.scalars(select(UserSetting).where(UserSetting.user_id == current_user.id))
    return [UserSettingItem(key=r.key, value=r.value) for r in rows]


@router.delete("/me/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.scalar(
        select(UserSetting).where((UserSetting.user_id == current_user.id) & (UserSetting.key == key))
    )
    if row:
        db.delete(row)
        db.commit()
    return None


# ── System settings (admin-only) ────────────────────────────────────────────
@router.get("/system", response_model=List[SystemSettingOut], dependencies=[Depends(require_admin)])
def list_system_settings(db: Session = Depends(get_db)):
    return list(db.scalars(select(SystemSetting).order_by(SystemSetting.key)))


@router.put("/system/{key}", response_model=SystemSettingOut, dependencies=[Depends(require_admin)])
def upsert_system_setting(
    key: str,
    body: SystemSettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if row:
        row.value = body.value
    else:
        row = SystemSetting(key=key, value=body.value, description="")
        db.add(row)
    log_action(
        db, user_id=current_user.id, action="system_setting.update",
        target_type="setting", target_id=key, detail=body.value[:200],
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(row)
    return row
