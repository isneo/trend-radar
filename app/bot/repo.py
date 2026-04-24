"""Concrete SQLAlchemy-backed repository for bot handlers."""

from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription, User


class DbPersonalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_user(self, tg_user_id: int, tg_username: str | None, display_name: str | None):
        stmt = (
            pg_insert(User)
            .values(tg_user_id=tg_user_id, tg_username=tg_username, display_name=display_name)
            .on_conflict_do_update(
                index_elements=[User.tg_user_id],
                set_={"tg_username": tg_username, "display_name": display_name},
            )
            .returning(User)
        )
        row = (await self._s.execute(stmt)).scalar_one()
        await self._s.commit()
        return row

    async def create_subscription(self, user_id: int, keywords: list[str], targets: list[str]):
        user = (await self._s.execute(
            select(User).where(User.tg_user_id == user_id)
        )).scalar_one()
        sub = Subscription(user_id=user.id, keywords=keywords, delivery_targets=targets)
        self._s.add(sub)
        await self._s.commit()
        await self._s.refresh(sub)
        return {"id": sub.id, "keywords": sub.keywords, "delivery_targets": sub.delivery_targets,
                "is_active": sub.is_active}

    async def list_subscriptions(self, user_id: int):
        rows = (await self._s.execute(
            select(Subscription).join(User).where(User.tg_user_id == user_id).order_by(Subscription.id)
        )).scalars().all()
        return [
            {"id": r.id, "keywords": r.keywords, "delivery_targets": r.delivery_targets,
             "is_active": r.is_active}
            for r in rows
        ]

    async def delete_subscription(self, user_id: int, sub_id: int) -> bool:
        result = await self._s.execute(
            delete(Subscription)
            .where(
                Subscription.id == sub_id,
                Subscription.user_id == select(User.id).where(User.tg_user_id == user_id).scalar_subquery(),
            )
        )
        await self._s.commit()
        return result.rowcount > 0

    async def set_user_active(self, user_id: int, active: bool) -> None:
        await self._s.execute(
            update(User).where(User.tg_user_id == user_id).values(is_active=active)
        )
        await self._s.commit()

    async def set_subscription_active(self, user_id: int, sub_id: int, active: bool) -> bool:
        result = await self._s.execute(
            update(Subscription)
            .where(
                Subscription.id == sub_id,
                Subscription.user_id == select(User.id).where(User.tg_user_id == user_id).scalar_subquery(),
            )
            .values(is_active=active)
        )
        await self._s.commit()
        return result.rowcount > 0
