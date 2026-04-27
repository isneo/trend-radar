"""Integration fixtures — real Postgres + Redis via docker compose.

The integration suite uses a **separate database** (the production DB name with
``_test`` appended) so running ``pytest`` cannot wipe development data via the
TRUNCATE teardown. The database is auto-created and migrated on first use.

Preconditions:
  docker compose up -d postgres redis
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings

_DB_NAME_RE = re.compile(r"/(?P<name>[^/?]+)(?P<rest>(\?.*)?)$")


def _swap_db_name(url: str, new_name: str) -> str:
    return _DB_NAME_RE.sub(rf"/{new_name}\g<rest>", url)


def _extract_db_name(url: str) -> str:
    m = _DB_NAME_RE.search(url)
    if not m:
        raise ValueError(f"cannot parse db name from URL: {url}")
    return m.group("name")


@pytest.fixture(scope="session")
def _test_db_url() -> str:
    """Ensure the test DB exists and is migrated to head; return its async URL."""
    settings = get_settings()
    prod_db = _extract_db_name(settings.database_url_sync)
    test_db = f"{prod_db}_test"

    sync_url = _swap_db_name(settings.database_url_sync, test_db)
    async_url = _swap_db_name(settings.database_url, test_db)

    # Connect to the cluster's "postgres" admin DB to issue CREATE DATABASE.
    # psycopg accepts a sync postgresql:// URL; strip the "+psycopg" driver tag.
    admin_url = _swap_db_name(settings.database_url_sync, "postgres").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(admin_url, autocommit=True) as admin:
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_db,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{test_db}"')

    cfg = Config(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")

    return async_url


@pytest.fixture(scope="module")
def engine(_test_db_url: str):
    eng = create_async_engine(_test_db_url, future=True, poolclass=NullPool)
    yield eng


@pytest.fixture
async def db(engine) -> AsyncIterator[AsyncSession]:
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        for tbl in (
            "delivery_log",
            "subscriptions",
            "feishu_groups",
            "crawl_history",
            "dispatch_state",
            "users",
        ):
            await session.execute(text(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE"))
        await session.commit()
