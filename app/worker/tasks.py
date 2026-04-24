"""Celery tasks: crawl, dispatch, push (ADR-011 idempotent)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models import (
    CrawlHistory,
    DeliveryLog,
    DispatchState,
    FeishuGroup,
    Subscription,
    User,
)
from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.feishu import FeishuPusher
from app.pushers.telegram import TelegramPusher
from app.services.dispatcher import item_matches
from app.worker.celery_app import celery_app
from trendradar.api import CrawledItem, fetch_all

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- CRAWL ----------

@celery_app.task(name="app.tasks.crawl")
def crawl_task() -> int:
    items = list(fetch_all())
    asyncio.run(_persist_crawl(items))
    dispatch_task.delay()
    return len(items)


async def _persist_crawl(items: Iterable[CrawledItem]) -> None:
    async with AsyncSessionLocal() as s:
        for item in items:
            stmt = (
                pg_insert(CrawlHistory)
                .values(
                    fingerprint=item.fingerprint,
                    source=item.source,
                    category=item.category,
                    title=item.title,
                    url=item.url,
                    summary=item.summary,
                    published_at=item.published_at,
                    raw=item.raw,
                )
                .on_conflict_do_update(
                    index_elements=[CrawlHistory.fingerprint],
                    set_={"last_seen_at": datetime.now(timezone.utc)},
                )
            )
            await s.execute(stmt)
        await s.commit()


# ---------- DISPATCH ----------

@celery_app.task(name="app.tasks.dispatch")
def dispatch_task() -> int:
    return asyncio.run(_dispatch_impl())


async def _dispatch_impl() -> int:
    enqueued = 0
    async with AsyncSessionLocal() as s:
        state = (await s.execute(
            select(DispatchState).where(DispatchState.key == "global")
        )).scalar_one_or_none()
        if state is None:
            state = DispatchState(key="global")
            s.add(state)
            await s.flush()

        new_items = (await s.execute(
            select(CrawlHistory)
            .where(CrawlHistory.first_seen_at > state.last_dispatched_at)
            .order_by(CrawlHistory.first_seen_at)
        )).scalars().all()

        if not new_items:
            return 0

        subs = (await s.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(Subscription.is_active, User.is_active)
        )).all()

        for item in new_items:
            for sub, user in subs:
                if not item_matches(item.title, sub.keywords, sub.excluded_keywords):
                    continue
                for target in sub.delivery_targets:
                    push_task.delay(sub.id, item.fingerprint, target, user.tg_user_id)
                    enqueued += 1

        state.last_dispatched_at = new_items[-1].first_seen_at
        await s.commit()
    return enqueued


# ---------- PUSH ----------

@celery_app.task(
    name="app.tasks.push",
    bind=True,
    autoretry_for=(Retryable,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def push_task(self, subscription_id: int, fp: str, delivery_target: str, tg_user_id: int) -> str:
    try:
        return asyncio.run(_push_impl(subscription_id, fp, delivery_target, tg_user_id))
    except BrokenChannel as e:
        asyncio.run(_mark_broken(delivery_target, str(e)))
        return "broken"


async def _push_impl(sub_id: int, fp: str, target: str, tg_user_id: int) -> str:
    async with AsyncSessionLocal() as s:
        # ADR-011: INSERT placeholder BEFORE external call
        ins = (
            pg_insert(DeliveryLog)
            .values(
                subscription_id=sub_id,
                item_fingerprint=fp,
                delivery_target=target,
            )
            .on_conflict_do_nothing(
                index_elements=["subscription_id", "item_fingerprint", "delivery_target"]
            )
            .returning(DeliveryLog.id)
        )
        row_id = (await s.execute(ins)).scalar_one_or_none()
        await s.commit()
        if row_id is None:
            return PushResult.SKIPPED.value  # already delivered

        item = (await s.execute(
            select(CrawlHistory).where(CrawlHistory.fingerprint == fp)
        )).scalar_one()

        # resolve target → pusher + external id
        if target == "telegram":
            settings = get_settings()
            pusher = TelegramPusher(settings.telegram_bot_token)
            ctx = PushContext(target_external_id=str(tg_user_id))
        elif target.startswith("feishu:"):
            group_id = int(target.split(":", 1)[1])
            group = (await s.execute(
                select(FeishuGroup).where(
                    FeishuGroup.id == group_id,
                    FeishuGroup.status == "active",
                )
            )).scalar_one_or_none()
            if group is None:
                return PushResult.SKIPPED.value
            pusher = FeishuPusher()
            ctx = PushContext(target_external_id=group.webhook_url)
        else:
            log.warning("unknown delivery target: %s", target)
            return PushResult.SKIPPED.value

        item_dto = CrawledItem(
            fingerprint=item.fingerprint,
            source=item.source,
            category=item.category,
            title=item.title,
            url=item.url,
            summary=item.summary,
            published_at=item.published_at,
            raw=item.raw,
        )

        try:
            result = await pusher.push(ctx, item_dto)
        except Retryable as e:
            async with AsyncSessionLocal() as s2:
                await s2.execute(
                    update(DeliveryLog)
                    .where(DeliveryLog.id == row_id)
                    .values(retry_count=DeliveryLog.retry_count + 1, last_error=str(e))
                )
                await s2.commit()
            raise

    async with AsyncSessionLocal() as s3:
        await s3.execute(
            update(DeliveryLog)
            .where(DeliveryLog.id == row_id)
            .values(sent_at=_now())
        )
        await s3.commit()
    return result.value


async def _mark_broken(target: str, err: str) -> None:
    if target == "telegram":
        return  # TG-level breakage surfaced as BrokenChannel but bot-user id is always valid
    if target.startswith("feishu:"):
        gid = int(target.split(":", 1)[1])
        async with AsyncSessionLocal() as s:
            await s.execute(
                update(FeishuGroup)
                .where(FeishuGroup.id == gid)
                .values(status="broken", last_broken_at=_now())
            )
            await s.commit()


# keep ping for health checks
@celery_app.task(name="app.ping")
def ping() -> str:
    return "pong"
