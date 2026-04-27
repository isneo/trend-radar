from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import CrawlHistory


@pytest.mark.integration
async def test_second_write_updates_last_seen(db):
    now1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    now2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

    stmt1 = pg_insert(CrawlHistory).values(
        fingerprint="fp-dup",
        source="HN",
        title="T",
        url="https://x/",
        first_seen_at=now1,
        last_seen_at=now1,
    ).on_conflict_do_update(
        index_elements=[CrawlHistory.fingerprint],
        set_={"last_seen_at": now1},
    )
    await db.execute(stmt1)
    await db.commit()

    stmt2 = pg_insert(CrawlHistory).values(
        fingerprint="fp-dup",
        source="HN",
        title="T",
        url="https://x/",
        first_seen_at=now2,
        last_seen_at=now2,
    ).on_conflict_do_update(
        index_elements=[CrawlHistory.fingerprint],
        set_={"last_seen_at": now2},
    )
    await db.execute(stmt2)
    await db.commit()

    rows = (await db.execute(
        select(CrawlHistory).where(CrawlHistory.fingerprint == "fp-dup")
    )).scalars().all()
    assert len(rows) == 1, "fingerprint UNIQUE must keep it to 1 row"
    assert rows[0].first_seen_at == now1, "first_seen_at must NOT be overwritten"
    assert rows[0].last_seen_at == now2, "last_seen_at MUST be updated"
