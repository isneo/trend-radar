from __future__ import annotations

from sqlalchemy import ARRAY, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("array_length(keywords, 1) >= 1", name="ck_subscription_keywords_nonempty"),
        CheckConstraint("array_length(delivery_targets, 1) >= 1", name="ck_subscription_targets_nonempty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    excluded_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    delivery_targets: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscriptions")  # noqa: F821
