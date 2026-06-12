"""SQLAlchemy model for newsletter subscribers."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from vetce.db import Base


class Subscriber(Base):
    """A person who signed up via the 'Stay in the loop' form.

    Single-step signup: row is created when the form is submitted.
    No confirmation flow (yet); when we have a newsletter infrastructure
    set up, we can add a confirmed_at column and a verification token.

    Email is the unique key — submitting the same address twice is idempotent
    (no error, no duplicate row).
    """

    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320),  # max email length per RFC 5321
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Subscriber id={self.id} email={self.email!r}>"