from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.bot.repo import DbBotRepo
from app.models import CrawlHistory, DeliveryLog


@pytest.mark.integration
async def test_dispatch_dedup_via_unique_constraint(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(555, "eve", "Eve")
    sub = await repo.create_subscription(555, ["gpt"], ["telegram"])

    db.add(
        CrawlHistory(
            fingerprint="fp-x",
            source="HN",
            title="GPT-5 released",
            url="https://example.com/",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    for _ in range(2):
        stmt = pg_insert(DeliveryLog).values(
            subscription_id=sub["id"],
            item_fingerprint="fp-x",
            delivery_target="telegram",
        ).on_conflict_do_nothing(
            index_elements=["subscription_id", "item_fingerprint", "delivery_target"]
        )
        await db.execute(stmt)
    await db.commit()

    rows = (await db.execute(select(DeliveryLog))).scalars().all()
    assert len(rows) == 1, (
        "UNIQUE(subscription_id, item_fingerprint, delivery_target) must enforce dedup"
    )
