"""Two-factor authentication (TOTP) per-user state.

A user has one TwoFactor row, created when they begin enrollment.
- `enabled=False, secret=...` means "in setup" — login still works without code.
- `enabled=True` means TOTP code is required at login.
- `backup_codes_hashed` is a JSON list of bcrypt hashes for one-time fallback codes.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TwoFactor(Base):
    __tablename__ = "two_factor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_codes_hashed: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    enabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
