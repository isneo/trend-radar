from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class DeliveryLog(Base):
    """Tracks what item has been delivered to what user on what channel.

    Used to de-dupe: never send the same (user, item, channel) twice.
    """

    __tablename__ = "delivery_log"
    __table_args__ = (
        UniqueConstraint("user_id", "item_fingerprint", "channel", name="uq_delivery_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
