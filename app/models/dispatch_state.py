from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DispatchState(Base):
    """Global watermark — tracks which crawl_history items have been dispatched."""

    __tablename__ = "dispatch_state"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc),
        server_default="1970-01-01 00:00:00+00:00",
    )
