"""Concrete SQLAlchemy-backed repository for all bot handlers."""

from __future__ import annotations

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeishuGroup, Subscription, User


class DbBotRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- users ---
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

    # --- subscriptions (personal) ---
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
        user_sq = select(User.id).where(User.tg_user_id == user_id).scalar_subquery()
        result = await self._s.execute(
            delete(Subscription).where(Subscription.id == sub_id, Subscription.user_id == user_sq)
        )
        await self._s.commit()
        return result.rowcount > 0

    async def set_user_active(self, user_id: int, active: bool) -> None:
        await self._s.execute(update(User).where(User.tg_user_id == user_id).values(is_active=active))
        await self._s.commit()

    async def set_subscription_active(self, user_id: int, sub_id: int, active: bool) -> bool:
        user_sq = select(User.id).where(User.tg_user_id == user_id).scalar_subquery()
        result = await self._s.execute(
            update(Subscription).where(Subscription.id == sub_id, Subscription.user_id == user_sq)
            .values(is_active=active)
        )
        await self._s.commit()
        return result.rowcount > 0

    # --- feishu groups ---
    async def create_feishu_group(self, owner_user_id: int, name: str | None, webhook_url: str, keywords: list[str]):
        user = (await self._s.execute(
            select(User).where(User.tg_user_id == owner_user_id)
        )).scalar_one()
        group = FeishuGroup(owner_user_id=user.id, name=name, webhook_url=webhook_url)
        self._s.add(group)
        await self._s.flush()
        sub = Subscription(
            user_id=user.id, keywords=keywords,
            delivery_targets=[f"feishu:{group.id}"],
        )
        self._s.add(sub)
        await self._s.commit()
        await self._s.refresh(group)
        return {"id": group.id, "owner": owner_user_id, "name": group.name, "url": group.webhook_url,
                "keywords": keywords, "status": group.status}

    async def list_feishu_groups(self, owner_user_id: int):
        rows = (await self._s.execute(
            select(FeishuGroup).join(User).where(User.tg_user_id == owner_user_id).order_by(FeishuGroup.id)
        )).scalars().all()
        result = []
        for g in rows:
            subs = (await self._s.execute(
                select(Subscription).where(Subscription.delivery_targets.any(f"feishu:{g.id}"))
            )).scalars().all()
            kws: list[str] = []
            for s in subs:
                kws.extend(s.keywords)
            result.append({"id": g.id, "owner": owner_user_id, "name": g.name, "url": g.webhook_url,
                           "keywords": kws, "status": g.status})
        return result

    async def remove_feishu_group(self, owner_user_id: int, group_id: int) -> bool:
        user_sq = select(User.id).where(User.tg_user_id == owner_user_id).scalar_subquery()
        result = await self._s.execute(
            delete(FeishuGroup).where(FeishuGroup.id == group_id, FeishuGroup.owner_user_id == user_sq)
        )
        await self._s.execute(
            delete(Subscription).where(Subscription.delivery_targets.any(f"feishu:{group_id}"), Subscription.user_id == user_sq)
        )
        await self._s.commit()
        return result.rowcount > 0

    async def probe_webhook(self, url: str) -> bool:
        payload = {"msg_type": "text", "content": {"text": "TrendRadar 已绑定本群 ✅"}}
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                resp = await client.post(url, json=payload)
            if 200 <= resp.status_code < 300:
                body = resp.json() if resp.content else {}
                return int(body.get("code", 0)) == 0
            return False
        except (httpx.HTTPError, ValueError):
            return False
