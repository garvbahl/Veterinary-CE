"""SQLAlchemy model for admin sessions.

One row per active admin login. Created on successful POST /admin/login,
deleted on POST /admin/logout, expired by `expires_at` for stale sessions.

We store sessions in Postgres rather than as JWTs because:
- Single admin user, no need for stateless tokens
- We can revoke sessions (delete from DB) instantly
- No secret-rotation concerns
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from vetce.db import Base


class AdminSession(Base):
    """One active admin login session."""

    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 256-bit random token, hex-encoded → 64 chars. Stored in the session cookie.
    # Indexed because every authenticated request looks this up by token.
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AdminSession id={self.id} expires_at={self.expires_at}>"