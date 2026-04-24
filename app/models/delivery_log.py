from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class DeliveryLog(Base):
    """Idempotent delivery ledger (ADR-011).

    UNIQUE(subscription_id, item_fingerprint, delivery_target) guarantees
    that INSERT ... ON CONFLICT DO NOTHING RETURNING id is atomic per target.
    """

    __tablename__ = "delivery_log"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "item_fingerprint", "delivery_target",
            name="uq_delivery_once",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    delivery_target: Mapped[str] = mapped_column(String(64), nullable=False)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
