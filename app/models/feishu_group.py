from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FeishuGroup(Base, TimestampMixin):
    __tablename__ = "feishu_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    webhook_url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", nullable=False)
    last_broken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="feishu_groups")  # noqa: F821
