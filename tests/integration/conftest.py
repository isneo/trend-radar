"""Integration fixtures — real Postgres + Redis via docker compose.

Preconditions:
  docker compose up -d postgres redis
  uv run alembic upgrade head
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


@pytest.fixture(scope="module")
def engine():
    settings = get_settings()
    eng = create_async_engine(settings.database_url, future=True, poolclass=NullPool)
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
