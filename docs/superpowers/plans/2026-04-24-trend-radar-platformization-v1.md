# TrendRadar Platformization V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the single-user `trend-radar` crawler into a multi-user SaaS on Oracle VM with TG Bot as control plane and Feishu group as a push target, running locally end-to-end.

**Architecture:** Docker Compose with Postgres 16 + Redis 7; 4 Python processes (FastAPI, aiogram v3 bot, Celery worker, Celery beat); Telegram as unified control plane; Feishu groups as passive push targets. `trendradar/` refactored into a library with a clean `fetch_all` API (ADR-008) consumed by Celery workers. All outbound HTTP has explicit timeouts; idempotency is enforced by `UNIQUE(subscription_id, item_fingerprint, delivery_target)` + `INSERT ... ON CONFLICT DO NOTHING RETURNING id` pattern (ADR-011).

**Tech Stack:** Python 3.12, uv, SQLAlchemy 2.0 async + asyncpg, Alembic, Celery 5 + Redis 7 AOF, aiogram v3, FastAPI, httpx, Postgres 16, pytest + pytest-asyncio, loguru, Sentry, Docker Compose.

**Upstream docs:**
- [docs/platform/product-spec.md](../../platform/product-spec.md) v0.3
- [docs/platform/architecture.md](../../platform/architecture.md) v0.2
- [docs/platform/technical-design.md](../../platform/technical-design.md) v0.1

---

## File Structure Overview

**New files (app layer)**
```
app/
├── fingerprint.py                       # URL canonicalize + sha256
├── pushers/
│   ├── __init__.py
│   ├── base.py                          # Protocol + PushResult enum + errors
│   ├── telegram.py                      # httpx → Bot API sendMessage
│   └── feishu.py                        # httpx → Feishu custom bot webhook
├── services/
│   ├── __init__.py
│   ├── subscriptions.py                 # User/Subscription CRUD
│   ├── feishu_groups.py                 # FeishuGroup CRUD + URL validation
│   └── dispatcher.py                    # match + fanout logic
├── bot/
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── personal.py                  # /start /subscribe /list /unsubscribe /pause /resume
│   │   └── feishu.py                    # /add_feishu_group /my_feishu_groups /edit_feishu_group /remove_feishu_group
│   └── formatters.py                    # item → TG message + Feishu card
├── worker/
│   ├── heartbeat.py                     # worker liveness to Redis
│   ├── celery_app.py                    # (modify)
│   └── tasks.py                         # crawl_task / dispatch_task / push_task (modify)
├── api/
│   ├── health.py                        # /healthz + /healthz?deep=1
│   └── main.py                          # (modify)
├── observability/
│   ├── __init__.py
│   └── sentry.py                        # init helper
└── models/
    ├── feishu_group.py                  # NEW
    ├── crawl_history.py                 # NEW
    ├── dispatch_state.py                # NEW
    ├── user.py                          # modify (add locale)
    ├── subscription.py                  # modify (drop channel, add delivery_targets, excluded_keywords)
    ├── delivery_log.py                  # modify (subscription_id + retry fields)
    └── __init__.py                      # modify (export new models)
```

**New files (trendradar layer — ADR-008)**
```
trendradar/
└── api.py                               # NEW: CrawledItem + fetch_all
```

**New files (tests)**
```
tests/
├── conftest.py                          # fixtures: db, http mocks
├── unit/
│   ├── test_fingerprint.py
│   ├── test_pushers_telegram.py
│   ├── test_pushers_feishu.py
│   ├── test_dispatcher_match.py
│   ├── test_handlers_personal.py
│   ├── test_handlers_feishu.py
│   └── test_trendradar_api.py
└── integration/
    ├── test_subscribe_flow.py
    ├── test_dispatch_idempotency.py
    ├── test_feishu_bind.py
    ├── test_crawl_onconflict.py
    └── test_push_retry.py
```

**Modified files**
- `pyproject.toml` — add dev deps; add pytest config
- `docker-compose.yml` — Redis AOF
- `app/alembic/versions/<new>_schema_v2.py` — migration
- `app/worker/celery_app.py` — config hardening
- `app/worker/tasks.py` — real tasks
- `app/bot/main.py` — wire up dispatcher with handlers
- `app/api/main.py` — add /healthz deep

---

## Phase index

| Phase | Topic | Commits |
|---|---|---|
| 0 | Dev infra: pytest + conftest | 1 |
| 1 | Schema v2: models + Alembic migration | 1 |
| 2 | Fingerprint utility | 1 |
| 3 | trendradar engine refactor (ADR-008) | 1 |
| 4 | Pushers: Telegram + Feishu | 1 |
| 5 | Services: subscriptions / feishu_groups / dispatcher | 1 |
| 6 | TG Bot personal commands | 1 |
| 7 | TG Bot Feishu commands | 1 |
| 8 | Celery tasks (crawl + dispatch + push) | 1 |
| 9 | Observability: heartbeat + healthz + Sentry | 1 |
| 10 | Integration tests | 1 |
| 11 | E2E manual verification checklist | 0 |

---

## Phase 0: Dev Infrastructure

### Task 0.1: Add dev dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `[dependency-groups]` block**

Replace `dev = []` with:

```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "pytest-timeout>=2.3",
    "httpx>=0.27",
    "respx>=0.21",
    "aiosqlite>=0.20",
]
```

- [ ] **Step 2: Add pytest config block**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: fast, isolated unit tests",
    "integration: tests that touch real Postgres + Redis",
]
addopts = "-ra -q --timeout=30"
```

- [ ] **Step 3: Install dev deps**

Run: `uv sync --group dev`
Expected: installs pytest, pytest-asyncio, respx, etc.

### Task 0.2: Create tests conftest

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py` (empty)
- Create: `tests/integration/__init__.py` (empty)

- [ ] **Step 1: Create empty `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`**

```bash
mkdir -p tests/unit tests/integration
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 2: Write `tests/conftest.py`**

```python
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Integration tests: real DB session. Assumes `docker compose up` + `alembic upgrade head`."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()
    await engine.dispose()
```

- [ ] **Step 3: Verify pytest discovers tests**

Run: `uv run pytest --collect-only`
Expected: `0 tests collected` (no test files yet, but no errors).

### Task 0.3: Commit

- [ ] **Step 1: Commit**

```bash
git add pyproject.toml tests/
git commit -m "chore: add pytest + dev dependencies and test scaffolding"
```

---

## Phase 1: Schema v2

### Task 1.1: Update `User` model — add `locale`

**Files:**
- Modify: `app/models/user.py`

- [ ] **Step 1: Add `locale` field**

Replace content of `app/models/user.py` with:

```python
from __future__ import annotations

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    tg_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    feishu_groups: Mapped[list["FeishuGroup"]] = relationship(  # noqa: F821
        back_populates="owner", cascade="all, delete-orphan"
    )
```

### Task 1.2: Rewrite `Subscription` model

**Files:**
- Modify: `app/models/subscription.py`

- [ ] **Step 1: Replace content**

```python
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
```

### Task 1.3: Create `FeishuGroup` model

**Files:**
- Create: `app/models/feishu_group.py`

- [ ] **Step 1: Write file**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FeishuGroup(Base, TimestampMixin):
    __tablename__ = "feishu_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    webhook_url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    last_broken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="feishu_groups")  # noqa: F821
```

### Task 1.4: Create `CrawlHistory` model

**Files:**
- Create: `app/models/crawl_history.py`

- [ ] **Step 1: Write file**

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class CrawlHistory(Base):
    __tablename__ = "crawl_history"
    __table_args__ = (
        Index("ix_crawl_history_first_seen_at", "first_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
```

### Task 1.5: Create `DispatchState` model

**Files:**
- Create: `app/models/dispatch_state.py`

- [ ] **Step 1: Write file**

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DispatchState(Base):
    """Global watermark — tracks which crawl_history items have been dispatched."""

    __tablename__ = "dispatch_state"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc),
    )
```

### Task 1.6: Rewrite `DeliveryLog` model

**Files:**
- Modify: `app/models/delivery_log.py`

- [ ] **Step 1: Replace content**

```python
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
```

### Task 1.7: Update `models/__init__.py`

**Files:**
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Replace content**

```python
from app.models.base import Base
from app.models.crawl_history import CrawlHistory
from app.models.delivery_log import DeliveryLog
from app.models.dispatch_state import DispatchState
from app.models.feishu_group import FeishuGroup
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "FeishuGroup",
    "CrawlHistory",
    "DispatchState",
    "DeliveryLog",
]
```

### Task 1.8: Generate Alembic migration

**Files:**
- Create: `app/alembic/versions/<auto>_schema_v2.py`

- [ ] **Step 1: Drop the v1 initial migration data, regenerate**

Since there's no production data to preserve yet, the cleanest path is to blow away schema and re-autogenerate:

```bash
docker compose exec postgres psql -U trendradar -d trendradar -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
rm -f app/alembic/versions/*.py
```

- [ ] **Step 2: Autogenerate migration**

Run: `uv run alembic revision --autogenerate -m "schema v2 multi-user platform"`
Expected: `Generating app/alembic/versions/<hash>_schema_v2_multi_user_platform.py ... done`

- [ ] **Step 3: Review generated migration**

Open the newly-created file in `app/alembic/versions/`. Confirm:
- `op.create_table("users", ...)` includes `locale` with server_default `'zh-CN'`
- `op.create_table("subscriptions", ...)` has `delivery_targets` array, `excluded_keywords` array, no `channel` column, CHECK constraints present
- `op.create_table("feishu_groups", ...)` has UNIQUE on `webhook_url`
- `op.create_table("crawl_history", ...)` has UNIQUE on `fingerprint`, index on `first_seen_at`
- `op.create_table("dispatch_state", ...)` with PK `key`
- `op.create_table("delivery_log", ...)` has `subscription_id` FK + UNIQUE 3-tuple

If any autogen detail is off (e.g., missing server_default), edit the file by hand.

### Task 1.9: Apply migration and verify

- [ ] **Step 1: Apply**

Run: `uv run alembic upgrade head`
Expected: `INFO  [alembic.runtime.migration] Running upgrade  -> <hash>, schema v2 multi-user platform`

- [ ] **Step 2: Verify tables exist**

Run: `docker compose exec postgres psql -U trendradar -d trendradar -c "\dt"`
Expected: 7 tables — `alembic_version`, `users`, `subscriptions`, `feishu_groups`, `crawl_history`, `dispatch_state`, `delivery_log`.

- [ ] **Step 3: Verify UNIQUE constraints**

Run:
```bash
docker compose exec postgres psql -U trendradar -d trendradar -c "\d delivery_log" | grep uq_delivery_once
```
Expected: a line mentioning `UNIQUE CONSTRAINT uq_delivery_once (subscription_id, item_fingerprint, delivery_target)`.

- [ ] **Step 4: Commit**

```bash
git add app/models/ app/alembic/versions/
git commit -m "feat(schema): add multi-user platform tables and rewrite delivery_log for ADR-011 idempotency"
```

---

## Phase 2: Fingerprint utility

### Task 2.1: Write fingerprint tests

**Files:**
- Create: `tests/unit/test_fingerprint.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from app.fingerprint import canonicalize_url, fingerprint


@pytest.mark.unit
class TestCanonicalizeUrl:
    def test_strips_utm_params(self):
        raw = "https://example.com/post?id=1&utm_source=tw&utm_medium=x"
        assert canonicalize_url(raw) == "https://example.com/post?id=1"

    def test_strips_fbclid(self):
        raw = "https://example.com/?fbclid=abc&x=1"
        assert canonicalize_url(raw) == "https://example.com/?x=1"

    def test_strips_trailing_slash(self):
        assert canonicalize_url("https://example.com/post/") == "https://example.com/post"

    def test_preserves_path_and_non_tracking_params(self):
        raw = "https://example.com/a/b?q=python&page=2"
        assert canonicalize_url(raw) == "https://example.com/a/b?page=2&q=python"

    def test_lowercases_scheme_and_host(self):
        assert canonicalize_url("HTTPS://Example.COM/X") == "https://example.com/X"


@pytest.mark.unit
class TestFingerprint:
    def test_is_deterministic(self):
        fp1 = fingerprint("HN", "https://example.com/x")
        fp2 = fingerprint("HN", "https://example.com/x")
        assert fp1 == fp2

    def test_different_source_different_fp(self):
        assert fingerprint("HN", "https://x.com/a") != fingerprint("TW", "https://x.com/a")

    def test_tracking_params_do_not_change_fp(self):
        fp1 = fingerprint("HN", "https://example.com/x")
        fp2 = fingerprint("HN", "https://example.com/x?utm_source=t")
        assert fp1 == fp2

    def test_length_is_16_hex_chars(self):
        fp = fingerprint("HN", "https://example.com/")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_fingerprint.py -v`
Expected: All tests fail with `ModuleNotFoundError: No module named 'app.fingerprint'`.

### Task 2.2: Implement fingerprint module

**Files:**
- Create: `app/fingerprint.py`

- [ ] **Step 1: Write implementation**

```python
"""URL canonicalization + stable content fingerprinting (ADR-011)."""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAM_PREFIXES: tuple[str, ...] = ("utm_",)
_TRACKING_PARAM_EXACT: frozenset[str] = frozenset({
    "fbclid", "gclid", "msclkid", "yclid", "mc_cid", "mc_eid",
    "ref", "ref_src", "ref_url", "_hsenc", "_hsmi",
})


def canonicalize_url(url: str) -> str:
    """Remove tracking params, normalize scheme/host case, strip trailing slash."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(k)
    ]
    kept.sort()
    query = urlencode(kept)

    path = parts.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    return urlunsplit((scheme, netloc, path, query, ""))


def _is_tracking_param(key: str) -> bool:
    lk = key.lower()
    if lk in _TRACKING_PARAM_EXACT:
        return True
    return any(lk.startswith(p) for p in _TRACKING_PARAM_PREFIXES)


def fingerprint(source: str, url: str) -> str:
    """Stable 16-hex fingerprint for dedup."""
    key = f"{source}|{canonicalize_url(url)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 2: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_fingerprint.py -v`
Expected: All 9 tests PASS.

### Task 2.3: Commit

- [ ] **Step 1: Commit**

```bash
git add app/fingerprint.py tests/unit/test_fingerprint.py
git commit -m "feat(fingerprint): URL canonicalization + stable sha256 fingerprint"
```

---

## Phase 3: trendradar engine refactor (ADR-008)

### Task 3.1: Write `CrawledItem` test

**Files:**
- Create: `tests/unit/test_trendradar_api.py`

- [ ] **Step 1: Write failing test**

```python
from datetime import datetime

import pytest

from trendradar.api import CrawledItem


@pytest.mark.unit
def test_crawled_item_is_frozen():
    item = CrawledItem(
        fingerprint="abc123", source="HN", category=None,
        title="Hello", url="https://example.com/", summary=None,
        published_at=None, raw={},
    )
    with pytest.raises(AttributeError):
        item.title = "mutated"


@pytest.mark.unit
def test_crawled_item_equality():
    a = CrawledItem("fp", "S", None, "T", "https://x/", None, None, {})
    b = CrawledItem("fp", "S", None, "T", "https://x/", None, None, {})
    assert a == b
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_trendradar_api.py -v`
Expected: ImportError — `trendradar.api` does not exist yet.

### Task 3.2: Implement `trendradar/api.py`

**Files:**
- Create: `trendradar/api.py`

- [ ] **Step 1: Write the module**

```python
"""Public library API for the trendradar engine.

Consumed by app.worker.tasks.crawl_task. This is the ONLY surface the
platform layer depends on — core internals may change freely.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CrawledItem:
    fingerprint: str
    source: str
    category: str | None
    title: str
    url: str
    summary: str | None
    published_at: datetime | None
    raw: dict[str, Any]


def fetch_all(
    config_path: str | None = None,
    sources: list[str] | None = None,
) -> Iterable[CrawledItem]:
    """Crawl all (or selected) sources and yield structured items.

    Does NOT write HTML, SQLite, or send notifications — those are the
    single-user CLI's concern. Platform callers iterate and persist.
    """
    from trendradar.api_impl import _fetch_all_impl
    yield from _fetch_all_impl(config_path=config_path, sources=sources)
```

- [ ] **Step 2: Run CrawledItem test to verify pass**

Run: `uv run pytest tests/unit/test_trendradar_api.py -v`
Expected: Both tests PASS.

### Task 3.3: Write fetch_all integration wrapper test

**Files:**
- Modify: `tests/unit/test_trendradar_api.py`

- [ ] **Step 1: Append test**

```python
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_fetch_all_yields_crawled_items(monkeypatch):
    """With mocked DataFetcher, fetch_all returns CrawledItem instances."""
    from trendradar import api as api_mod

    fake_items = [
        CrawledItem("fp1", "HN", None, "t1", "https://a/", None, None, {}),
        CrawledItem("fp2", "TW", None, "t2", "https://b/", None, None, {}),
    ]

    def fake_impl(config_path, sources):
        yield from fake_items

    monkeypatch.setattr("trendradar.api_impl._fetch_all_impl", fake_impl)

    got = list(api_mod.fetch_all())
    assert got == fake_items
```

- [ ] **Step 2: Run to verify failure (api_impl missing)**

Run: `uv run pytest tests/unit/test_trendradar_api.py::test_fetch_all_yields_crawled_items -v`
Expected: `ModuleNotFoundError: No module named 'trendradar.api_impl'`.

### Task 3.4: Implement `trendradar/api_impl.py`

**Files:**
- Create: `trendradar/api_impl.py`

- [ ] **Step 1: Write thin wrapper around existing DataFetcher**

```python
"""Implementation of the fetch_all public API.

Bridges the new structured-output contract to the existing DataFetcher
plumbing in trendradar.crawler. Single-user CLI semantics (HTML / SQLite /
notification) are the CLI layer's responsibility and are NOT invoked here.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from app.fingerprint import fingerprint as _fingerprint


def _fetch_all_impl(
    config_path: str | None = None,
    sources: list[str] | None = None,
) -> Iterable["CrawledItem"]:  # forward-ref to avoid cycle
    from trendradar.api import CrawledItem
    from trendradar.core import load_config
    from trendradar.crawler import DataFetcher

    config = load_config(config_path) if config_path else load_config()
    fetcher = DataFetcher(config)
    results = fetcher.fetch_all()  # existing method returning per-source items

    for source_name, payload in _iter_sources(results, sources):
        for raw_item in payload:
            url = _get(raw_item, ("url", "link"))
            title = _get(raw_item, ("title", "desc"))
            if not url or not title:
                continue
            yield CrawledItem(
                fingerprint=_fingerprint(source_name, url),
                source=source_name,
                category=_get(raw_item, ("category",)),
                title=title,
                url=url,
                summary=_get(raw_item, ("summary", "desc")),
                published_at=_parse_ts(_get(raw_item, ("published_at", "time"))),
                raw=dict(raw_item) if isinstance(raw_item, dict) else {},
            )


def _iter_sources(results: Any, filter_sources: list[str] | None):
    """Normalize DataFetcher output to (source_name, items) tuples."""
    if isinstance(results, dict):
        pairs = results.items()
    else:
        pairs = [(getattr(r, "source", "unknown"), r) for r in results]
    for name, payload in pairs:
        if filter_sources and name not in filter_sources:
            continue
        items = payload if isinstance(payload, list) else getattr(payload, "items", [])
        yield name, items


def _get(obj: Any, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k]:
            return obj[k]
        v = getattr(obj, k, None)
        if v:
            return v
    return None


def _parse_ts(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return None
    return None
```

> **Note:** Exact shape of `DataFetcher().fetch_all()` output depends on existing code. If the structure differs from assumptions above, adjust `_iter_sources` and `_get` only — leave the public contract in `trendradar/api.py` intact.

- [ ] **Step 2: Run all trendradar.api tests**

Run: `uv run pytest tests/unit/test_trendradar_api.py -v`
Expected: All 3 tests PASS.

### Task 3.5: Verify CLI still works

- [ ] **Step 1: Run CLI sanity check**

Run: `uv run python -m trendradar --help`
Expected: prints argparse usage; exits 0.

> **If the CLI imports break** because `trendradar/api.py` introduced a cycle, add `from __future__ import annotations` to the affected files or move the import inside functions.

### Task 3.6: Commit

- [ ] **Step 1: Commit**

```bash
git add trendradar/api.py trendradar/api_impl.py tests/unit/test_trendradar_api.py
git commit -m "feat(trendradar): add fetch_all library API per ADR-008"
```

---

## Phase 4: Pushers

### Task 4.1: Write base test

**Files:**
- Create: `tests/unit/test_pushers_base.py`

- [ ] **Step 1: Write failing test**

```python
import pytest

from app.pushers.base import BrokenChannel, PushResult, Retryable


@pytest.mark.unit
def test_push_result_enum_values():
    assert PushResult.SENT.value == "sent"
    assert PushResult.SKIPPED.value == "skipped"


@pytest.mark.unit
def test_broken_channel_exception():
    err = BrokenChannel("webhook deleted")
    assert str(err) == "webhook deleted"
    assert isinstance(err, Exception)


@pytest.mark.unit
def test_retryable_exception():
    err = Retryable("timeout")
    assert isinstance(err, Exception)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_pushers_base.py -v`
Expected: ImportError on `app.pushers.base`.

### Task 4.2: Implement pushers/base

**Files:**
- Create: `app/pushers/__init__.py` (empty)
- Create: `app/pushers/base.py`

- [ ] **Step 1: Create empty `app/pushers/__init__.py`**

Run: `touch app/pushers/__init__.py`

- [ ] **Step 2: Write `app/pushers/base.py`**

```python
"""Common contracts for channel pushers (telegram, feishu).

Error semantics drive ADR-011 retry policy:
- BrokenChannel → 4xx; mark channel broken, no retry.
- Retryable    → 5xx / timeout / network; Celery autoretry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from trendradar.api import CrawledItem


class PushResult(str, Enum):
    SENT = "sent"
    SKIPPED = "skipped"


class BrokenChannel(Exception):
    """Permanent failure. Caller should mark the channel broken."""


class Retryable(Exception):
    """Transient failure. Caller should retry with backoff."""


@dataclass(frozen=True)
class PushContext:
    """Carries what a pusher needs — kept small and concrete."""
    target_external_id: str   # TG chat id OR Feishu webhook URL


class Pusher(Protocol):
    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult: ...
```

- [ ] **Step 3: Run test to verify pass**

Run: `uv run pytest tests/unit/test_pushers_base.py -v`
Expected: 3 tests PASS.

### Task 4.3: Write TelegramPusher test

**Files:**
- Create: `tests/unit/test_pushers_telegram.py`

- [ ] **Step 1: Write failing test**

```python
import httpx
import pytest
import respx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.telegram import TelegramPusher
from trendradar.api import CrawledItem


def _item() -> CrawledItem:
    return CrawledItem(
        fingerprint="fp", source="HN", category="论文",
        title="T", url="https://example.com/", summary="s",
        published_at=None, raw={},
    )


@pytest.fixture
def pusher() -> TelegramPusher:
    return TelegramPusher(bot_token="TOK")


@pytest.mark.unit
@respx.mock
async def test_success_returns_sent(pusher: TelegramPusher):
    route = respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await pusher.push(PushContext(target_external_id="123"), _item())
    assert result is PushResult.SENT
    assert route.called


@pytest.mark.unit
@respx.mock
async def test_4xx_raises_broken(pusher: TelegramPusher):
    respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(403, json={"ok": False})
    )
    with pytest.raises(BrokenChannel):
        await pusher.push(PushContext(target_external_id="123"), _item())


@pytest.mark.unit
@respx.mock
async def test_5xx_raises_retryable(pusher: TelegramPusher):
    respx.post("https://api.telegram.org/botTOK/sendMessage").mock(
        return_value=httpx.Response(502, json={"ok": False})
    )
    with pytest.raises(Retryable):
        await pusher.push(PushContext(target_external_id="123"), _item())
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_pushers_telegram.py -v`
Expected: ImportError.

### Task 4.4: Implement TelegramPusher

**Files:**
- Create: `app/pushers/telegram.py`

- [ ] **Step 1: Write implementation**

```python
"""Telegram Bot API pusher.

Uses sendMessage with HTML parse mode; 10s timeout (ADR-011 §3).
"""

from __future__ import annotations

from html import escape

import httpx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Pusher, Retryable
from trendradar.api import CrawledItem


class TelegramPusher(Pusher):
    def __init__(self, bot_token: str, *, timeout: float = 10.0) -> None:
        self._base = f"https://api.telegram.org/bot{bot_token}"
        self._timeout = timeout

    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult:
        body = _format(item)
        url = f"{self._base}/sendMessage"
        payload = {
            "chat_id": ctx.target_external_id,
            "text": body,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise Retryable(f"telegram network: {e}") from e

        if 200 <= resp.status_code < 300:
            return PushResult.SENT
        if 400 <= resp.status_code < 500:
            raise BrokenChannel(f"telegram {resp.status_code}: {resp.text[:200]}")
        raise Retryable(f"telegram {resp.status_code}")


def _format(item: CrawledItem) -> str:
    cat = f"【{item.category}】 " if item.category else ""
    lines = [f"<b>{cat}{escape(item.title)}</b>"]
    if item.summary:
        lines.append(escape(item.summary[:280]))
    lines.append(f'<a href="{escape(item.url)}">阅读原文</a>  ·  {escape(item.source)}')
    return "\n".join(lines)
```

- [ ] **Step 2: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_pushers_telegram.py -v`
Expected: 3 tests PASS.

### Task 4.5: Write FeishuPusher test

**Files:**
- Create: `tests/unit/test_pushers_feishu.py`

- [ ] **Step 1: Write failing test**

```python
import httpx
import pytest
import respx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.feishu import FeishuPusher
from trendradar.api import CrawledItem


def _item() -> CrawledItem:
    return CrawledItem(
        fingerprint="fp", source="HN", category="论文",
        title="T", url="https://example.com/", summary="s",
        published_at=None, raw={},
    )


@pytest.fixture
def pusher() -> FeishuPusher:
    return FeishuPusher()


_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/abc"


@pytest.mark.unit
@respx.mock
async def test_success_returns_sent(pusher: FeishuPusher):
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    result = await pusher.push(PushContext(target_external_id=_URL), _item())
    assert result is PushResult.SENT
    assert route.called
    # Body should be a rich card (msg_type = "interactive")
    body = route.calls[0].request.content
    assert b'"msg_type":"interactive"' in body or b'"msg_type": "interactive"' in body


@pytest.mark.unit
@respx.mock
async def test_code_nonzero_is_broken(pusher: FeishuPusher):
    respx.post(_URL).mock(return_value=httpx.Response(200, json={"code": 19021}))
    with pytest.raises(BrokenChannel):
        await pusher.push(PushContext(target_external_id=_URL), _item())


@pytest.mark.unit
@respx.mock
async def test_5xx_is_retryable(pusher: FeishuPusher):
    respx.post(_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(Retryable):
        await pusher.push(PushContext(target_external_id=_URL), _item())
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_pushers_feishu.py -v`
Expected: ImportError.

### Task 4.6: Implement FeishuPusher

**Files:**
- Create: `app/pushers/feishu.py`

- [ ] **Step 1: Write implementation**

```python
"""Feishu custom-bot webhook pusher.

Sends interactive card (richer than plain text). Feishu returns 200 with
`code != 0` on logical failures (e.g., invalid signature, deleted bot) —
these are treated as BrokenChannel, not Retryable.
"""

from __future__ import annotations

import httpx

from app.pushers.base import BrokenChannel, PushContext, PushResult, Pusher, Retryable
from trendradar.api import CrawledItem

_TRANSIENT_CODES: frozenset[int] = frozenset({9499, 9504})  # Feishu internal error range


class FeishuPusher(Pusher):
    def __init__(self, *, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def push(self, ctx: PushContext, item: CrawledItem) -> PushResult:
        payload = {"msg_type": "interactive", "card": _card(item)}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(ctx.target_external_id, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise Retryable(f"feishu network: {e}") from e

        if 500 <= resp.status_code < 600:
            raise Retryable(f"feishu {resp.status_code}")
        if resp.status_code >= 400:
            raise BrokenChannel(f"feishu {resp.status_code}: {resp.text[:200]}")

        body = resp.json() if resp.content else {}
        code = int(body.get("code", 0))
        if code == 0:
            return PushResult.SENT
        if code in _TRANSIENT_CODES:
            raise Retryable(f"feishu code {code}")
        raise BrokenChannel(f"feishu code {code}: {body.get('msg','')}")


def _card(item: CrawledItem) -> dict:
    cat = f"【{item.category}】 " if item.category else ""
    elements: list[dict] = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**{cat}{item.title}**"}},
    ]
    if item.summary:
        elements.append({"tag": "div", "text": {"tag": "plain_text", "content": item.summary[:280]}})
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "阅读原文"},
            "type": "primary",
            "url": item.url,
        }],
    })
    return {
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": item.source}},
        "elements": elements,
    }
```

- [ ] **Step 2: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_pushers_feishu.py -v`
Expected: 3 tests PASS.

### Task 4.7: Commit

- [ ] **Step 1: Commit**

```bash
git add app/pushers/ tests/unit/test_pushers_*.py
git commit -m "feat(pushers): add TelegramPusher and FeishuPusher with ADR-011 error semantics"
```

---

## Phase 5: Services

### Task 5.1: Subscriptions service — write tests

**Files:**
- Create: `tests/unit/test_services_subscriptions.py`

- [ ] **Step 1: Write failing tests using in-memory fakes**

```python
import pytest

from app.services.subscriptions import parse_keywords, format_subscription_list


@pytest.mark.unit
class TestParseKeywords:
    def test_comma_delimited(self):
        assert parse_keywords("大模型, agent, rag") == ["大模型", "agent", "rag"]

    def test_strips_whitespace(self):
        assert parse_keywords("  ai ,  ml  ") == ["ai", "ml"]

    def test_dedups_case_insensitive(self):
        assert parse_keywords("AI, ai, Ai") == ["ai"]

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_keywords("")

    def test_rejects_all_whitespace(self):
        with pytest.raises(ValueError):
            parse_keywords(" ,  ,")


@pytest.mark.unit
def test_format_subscription_list_empty():
    assert format_subscription_list([]) == "你还没有任何订阅。发 /subscribe 关键词 来添加。"


@pytest.mark.unit
def test_format_subscription_list_two_items():
    subs = [
        {"id": 3, "keywords": ["ai"], "delivery_targets": ["telegram"], "is_active": True},
        {"id": 5, "keywords": ["大模型", "agent"], "delivery_targets": ["telegram", "feishu:42"], "is_active": False},
    ]
    out = format_subscription_list(subs)
    assert "3" in out and "ai" in out
    assert "5" in out and "大模型" in out and "agent" in out
    assert "已暂停" in out  # sub 5 is_active=False
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_services_subscriptions.py -v`
Expected: ImportError.

### Task 5.2: Implement subscriptions service

**Files:**
- Create: `app/services/__init__.py` (empty)
- Create: `app/services/subscriptions.py`

- [ ] **Step 1: Create empty `__init__.py`**

Run: `touch app/services/__init__.py`

- [ ] **Step 2: Write `app/services/subscriptions.py`**

```python
"""Pure-Python business logic for subscriptions (no DB session here).

DB CRUD happens in the caller (bot handler) using SQLAlchemy session.
These helpers are easy to unit-test without a DB.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def parse_keywords(raw: str) -> list[str]:
    """Comma-delimited → normalized, deduped, lowercased, non-empty."""
    seen: dict[str, None] = {}
    for token in raw.split(","):
        t = token.strip().lower()
        if t:
            seen[t] = None
    if not seen:
        raise ValueError("关键词不能为空")
    return list(seen.keys())


def format_subscription_list(subs: Sequence[dict[str, Any]]) -> str:
    if not subs:
        return "你还没有任何订阅。发 /subscribe 关键词 来添加。"
    lines = ["<b>你的订阅：</b>"]
    for s in subs:
        flag = "" if s["is_active"] else " （已暂停）"
        kws = ", ".join(s["keywords"])
        targets = ", ".join(s["delivery_targets"])
        lines.append(f"#{s['id']}  {kws}  →  {targets}{flag}")
    return "\n".join(lines)
```

- [ ] **Step 3: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_services_subscriptions.py -v`
Expected: 7 tests PASS.

### Task 5.3: feishu_groups service — write tests

**Files:**
- Create: `tests/unit/test_services_feishu_groups.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest

from app.services.feishu_groups import is_valid_feishu_webhook


@pytest.mark.unit
@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://open.feishu.cn/open-apis/bot/v2/hook/abc-123", True),
        ("http://open.feishu.cn/open-apis/bot/v2/hook/abc", False),   # http not https
        ("https://open.larksuite.com/open-apis/bot/v2/hook/abc", True),  # intl
        ("https://evil.example/feishu", False),
        ("not-a-url", False),
        ("", False),
    ],
)
def test_is_valid_feishu_webhook(url: str, ok: bool):
    assert is_valid_feishu_webhook(url) is ok
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_services_feishu_groups.py -v`
Expected: ImportError.

### Task 5.4: Implement feishu_groups service

**Files:**
- Create: `app/services/feishu_groups.py`

- [ ] **Step 1: Write module**

```python
"""Feishu webhook validation + group helpers."""

from __future__ import annotations

from urllib.parse import urlparse

_ALLOWED_HOSTS: frozenset[str] = frozenset({
    "open.feishu.cn",
    "open.larksuite.com",
})
_REQUIRED_PATH_PREFIX = "/open-apis/bot/v2/hook/"


def is_valid_feishu_webhook(url: str) -> bool:
    if not url:
        return False
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    if parts.scheme != "https":
        return False
    if parts.hostname not in _ALLOWED_HOSTS:
        return False
    if not parts.path.startswith(_REQUIRED_PATH_PREFIX):
        return False
    # token segment must be non-empty
    token = parts.path[len(_REQUIRED_PATH_PREFIX):]
    return bool(token.strip("/"))
```

- [ ] **Step 2: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_services_feishu_groups.py -v`
Expected: 6 PASS.

### Task 5.5: Dispatcher match logic — write tests

**Files:**
- Create: `tests/unit/test_services_dispatcher.py`

- [ ] **Step 1: Write failing test**

```python
import pytest

from app.services.dispatcher import item_matches


@pytest.mark.unit
class TestItemMatches:
    def test_contains_single_keyword(self):
        assert item_matches("GPT-5 evaluation", ["gpt-5"], []) is True

    def test_case_insensitive(self):
        assert item_matches("OpenAI releases GPT-5", ["gpt-5"], []) is True

    def test_no_match(self):
        assert item_matches("Weather report", ["gpt-5"], []) is False

    def test_any_of_keywords_hits(self):
        assert item_matches("Anthropic announcement", ["gpt", "anthropic"], []) is True

    def test_excluded_keyword_blocks(self):
        assert item_matches("GPT-5 user agent bug", ["gpt-5"], ["user agent"]) is False

    def test_excluded_absent_keeps_match(self):
        assert item_matches("GPT-5 big news", ["gpt-5"], ["user agent"]) is True
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_services_dispatcher.py -v`
Expected: ImportError.

### Task 5.6: Implement dispatcher

**Files:**
- Create: `app/services/dispatcher.py`

- [ ] **Step 1: Write module**

```python
"""Match + fanout logic for dispatch_task (ADR-005 + ADR-011)."""

from __future__ import annotations

from collections.abc import Iterable


def item_matches(
    title: str,
    keywords: Iterable[str],
    excluded: Iterable[str],
) -> bool:
    """Case-insensitive substring match. Excluded wins over included."""
    lower = title.lower()
    if any(ex.lower() in lower for ex in excluded if ex):
        return False
    return any(kw.lower() in lower for kw in keywords if kw)
```

- [ ] **Step 2: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_services_dispatcher.py -v`
Expected: 6 PASS.

### Task 5.7: Commit

- [ ] **Step 1: Commit**

```bash
git add app/services/ tests/unit/test_services_*.py
git commit -m "feat(services): add subscriptions, feishu_groups, dispatcher domain helpers"
```

---

## Phase 6: TG Bot personal commands

### Task 6.1: Handlers test — `/start`, `/subscribe`, `/list`, `/unsubscribe`

**Files:**
- Create: `tests/unit/test_handlers_personal.py`

- [ ] **Step 1: Write failing tests with aiogram in-memory bot harness**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.personal import (
    handle_list,
    handle_start,
    handle_subscribe,
    handle_unsubscribe,
)


class _Msg:
    """Minimal aiogram.types.Message double."""

    def __init__(self, text: str, tg_user_id: int = 123, username: str = "neo"):
        self.text = text
        self.from_user = MagicMock(id=tg_user_id, username=username, full_name="Neo")
        self.answer = AsyncMock()


class _FakeRepo:
    def __init__(self):
        self.users: dict[int, dict] = {}
        self.subs: list[dict] = []
        self.next_sub_id = 1

    async def upsert_user(self, tg_user_id, tg_username, display_name):
        if tg_user_id not in self.users:
            self.users[tg_user_id] = {"id": tg_user_id, "username": tg_username, "name": display_name}
        return self.users[tg_user_id]

    async def create_subscription(self, user_id, keywords, targets):
        sub = {"id": self.next_sub_id, "user_id": user_id, "keywords": keywords,
               "delivery_targets": targets, "is_active": True}
        self.subs.append(sub)
        self.next_sub_id += 1
        return sub

    async def list_subscriptions(self, user_id):
        return [s for s in self.subs if s["user_id"] == user_id]

    async def delete_subscription(self, user_id, sub_id):
        before = len(self.subs)
        self.subs = [s for s in self.subs if not (s["user_id"] == user_id and s["id"] == sub_id)]
        return len(self.subs) < before


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.mark.unit
async def test_start_registers_user_and_greets(repo: _FakeRepo):
    msg = _Msg("/start")
    await handle_start(msg, repo=repo)
    assert 123 in repo.users
    assert msg.answer.called
    assert "欢迎" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_subscribe_creates_subscription(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/subscribe 大模型, agent")
    await handle_subscribe(msg, repo=repo)
    assert len(repo.subs) == 1
    assert repo.subs[0]["keywords"] == ["大模型", "agent"]
    assert repo.subs[0]["delivery_targets"] == ["telegram"]


@pytest.mark.unit
async def test_subscribe_empty_keywords_rejects(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/subscribe   ")
    await handle_subscribe(msg, repo=repo)
    assert len(repo.subs) == 0
    assert "用法" in msg.answer.call_args.args[0] or "不能为空" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_list_empty(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    msg = _Msg("/list")
    await handle_list(msg, repo=repo)
    assert "还没有任何订阅" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_unsubscribe_removes(repo: _FakeRepo):
    await repo.upsert_user(123, "neo", "Neo")
    await repo.create_subscription(123, ["ai"], ["telegram"])
    msg = _Msg("/unsubscribe 1")
    await handle_unsubscribe(msg, repo=repo)
    assert repo.subs == []
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_handlers_personal.py -v`
Expected: ImportError on `app.bot.handlers.personal`.

### Task 6.2: Implement handlers module

**Files:**
- Create: `app/bot/handlers/__init__.py` (empty)
- Create: `app/bot/handlers/personal.py`

- [ ] **Step 1: Create empty `__init__.py`**

Run: `touch app/bot/handlers/__init__.py`

- [ ] **Step 2: Write `app/bot/handlers/personal.py`**

```python
"""Personal subscription commands — TG control plane part 1."""

from __future__ import annotations

from typing import Protocol

from aiogram.types import Message

from app.services.subscriptions import format_subscription_list, parse_keywords


class PersonalRepo(Protocol):
    async def upsert_user(self, tg_user_id: int, tg_username: str | None, display_name: str | None): ...
    async def create_subscription(self, user_id: int, keywords: list[str], targets: list[str]): ...
    async def list_subscriptions(self, user_id: int): ...
    async def delete_subscription(self, user_id: int, sub_id: int) -> bool: ...
    async def set_user_active(self, user_id: int, active: bool) -> None: ...
    async def set_subscription_active(self, user_id: int, sub_id: int, active: bool) -> bool: ...


_HELP = (
    "欢迎使用 TrendRadar。支持命令：\n"
    "/subscribe 关键词1, 关键词2   订阅\n"
    "/list                        查看订阅\n"
    "/unsubscribe &lt;id&gt;            取消订阅\n"
    "/pause  /resume              暂停 / 恢复整体推送\n"
)


async def handle_start(msg: Message, *, repo: PersonalRepo) -> None:
    u = msg.from_user
    await repo.upsert_user(u.id, u.username, u.full_name)
    await msg.answer(_HELP)


async def handle_subscribe(msg: Message, *, repo: PersonalRepo) -> None:
    u = msg.from_user
    text = (msg.text or "").partition(" ")[2].strip()
    if not text:
        await msg.answer("用法：/subscribe 关键词1, 关键词2")
        return
    try:
        kws = parse_keywords(text)
    except ValueError as e:
        await msg.answer(str(e))
        return
    await repo.upsert_user(u.id, u.username, u.full_name)
    sub = await repo.create_subscription(u.id, kws, ["telegram"])
    await msg.answer(f"✅ 已订阅 #{sub['id']}：{', '.join(kws)}")


async def handle_list(msg: Message, *, repo: PersonalRepo) -> None:
    subs = await repo.list_subscriptions(msg.from_user.id)
    await msg.answer(format_subscription_list(subs))


async def handle_unsubscribe(msg: Message, *, repo: PersonalRepo) -> None:
    arg = (msg.text or "").partition(" ")[2].strip()
    if not arg.isdigit():
        await msg.answer("用法：/unsubscribe &lt;id&gt;")
        return
    ok = await repo.delete_subscription(msg.from_user.id, int(arg))
    await msg.answer("✅ 已删除" if ok else "❌ 订阅不存在或不属于你")


async def handle_pause(msg: Message, *, repo: PersonalRepo) -> None:
    await repo.set_user_active(msg.from_user.id, False)
    await msg.answer("⏸ 已暂停所有推送。/resume 恢复。")


async def handle_resume(msg: Message, *, repo: PersonalRepo) -> None:
    await repo.set_user_active(msg.from_user.id, True)
    await msg.answer("▶️ 已恢复推送。")
```

- [ ] **Step 3: Run tests to verify pass**

Run: `uv run pytest tests/unit/test_handlers_personal.py -v`
Expected: 5 tests PASS.

### Task 6.3: Create DB-backed PersonalRepo

**Files:**
- Create: `app/bot/repo.py`

- [ ] **Step 1: Write module**

```python
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
```

### Task 6.4: Wire handlers in `bot/main.py`

**Files:**
- Modify: `app/bot/main.py`

- [ ] **Step 1: Replace content**

```python
"""aiogram v3 bot — local polling mode.

Run with: uv run python -m app.bot.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.handlers import personal
from app.bot.repo import DbPersonalRepo
from app.config import get_settings
from app.db import AsyncSessionLocal


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env.local")

    bot = Bot(token=settings.telegram_bot_token, default_parse_mode="HTML")
    dp = Dispatcher()

    def _with_repo(handler):
        async def _wrap(msg: Message):
            async with AsyncSessionLocal() as session:
                await handler(msg, repo=DbPersonalRepo(session))
        return _wrap

    dp.message.register(_with_repo(personal.handle_start), Command("start"))
    dp.message.register(_with_repo(personal.handle_subscribe), Command("subscribe"))
    dp.message.register(_with_repo(personal.handle_list), Command("list"))
    dp.message.register(_with_repo(personal.handle_unsubscribe), Command("unsubscribe"))
    dp.message.register(_with_repo(personal.handle_pause), Command("pause"))
    dp.message.register(_with_repo(personal.handle_resume), Command("resume"))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Smoke test — bot starts without error**

Run (10s then Ctrl+C): `timeout 10 uv run python -m app.bot.main 2>&1 | head -20`
Expected: `INFO aiogram.dispatcher:Start polling` and no tracebacks.

### Task 6.5: Commit

- [ ] **Step 1: Commit**

```bash
git add app/bot/ tests/unit/test_handlers_personal.py
git commit -m "feat(bot): implement personal commands /start /subscribe /list /unsubscribe /pause /resume"
```

---

## Phase 7: TG Bot Feishu commands

### Task 7.1: Feishu handlers test

**Files:**
- Create: `tests/unit/test_handlers_feishu.py`

- [ ] **Step 1: Write failing test**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.handlers.feishu import (
    handle_add_feishu_group,
    handle_my_feishu_groups,
    handle_remove_feishu_group,
)


class _Msg:
    def __init__(self, text: str):
        self.text = text
        self.from_user = MagicMock(id=123, username="neo", full_name="Neo")
        self.answer = AsyncMock()


class _FakeRepo:
    def __init__(self):
        self.groups: list[dict] = []
        self.next_id = 1
        self.probe_ok = True

    async def upsert_user(self, *a, **kw):
        return {"id": 123}

    async def create_feishu_group(self, owner_user_id, name, webhook_url, keywords):
        g = {"id": self.next_id, "owner": owner_user_id, "name": name, "url": webhook_url,
             "keywords": keywords, "status": "active"}
        self.groups.append(g)
        self.next_id += 1
        return g

    async def list_feishu_groups(self, owner_user_id):
        return [g for g in self.groups if g["owner"] == owner_user_id]

    async def remove_feishu_group(self, owner_user_id, group_id):
        before = len(self.groups)
        self.groups = [g for g in self.groups if not (g["owner"] == owner_user_id and g["id"] == group_id)]
        return len(self.groups) < before

    async def probe_webhook(self, url: str) -> bool:
        return self.probe_ok


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


GOOD_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/abcdef"


@pytest.mark.unit
async def test_add_feishu_group_happy(repo: _FakeRepo):
    msg = _Msg(f"/add_feishu_group {GOOD_URL} 大模型, agent")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 1
    assert repo.groups[0]["keywords"] == ["大模型", "agent"]
    assert "已绑定" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_add_feishu_group_invalid_url(repo: _FakeRepo):
    msg = _Msg("/add_feishu_group https://evil.example/x 大模型")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 0
    assert "webhook" in msg.answer.call_args.args[0].lower()


@pytest.mark.unit
async def test_add_feishu_group_probe_failure(repo: _FakeRepo):
    repo.probe_ok = False
    msg = _Msg(f"/add_feishu_group {GOOD_URL} 大模型")
    await handle_add_feishu_group(msg, repo=repo)
    assert len(repo.groups) == 0
    assert "不可达" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_my_feishu_groups_empty(repo: _FakeRepo):
    msg = _Msg("/my_feishu_groups")
    await handle_my_feishu_groups(msg, repo=repo)
    assert "没有" in msg.answer.call_args.args[0]


@pytest.mark.unit
async def test_remove_feishu_group(repo: _FakeRepo):
    await repo.create_feishu_group(123, "g", GOOD_URL, ["x"])
    msg = _Msg("/remove_feishu_group 1")
    await handle_remove_feishu_group(msg, repo=repo)
    assert repo.groups == []
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_handlers_feishu.py -v`
Expected: ImportError.

### Task 7.2: Implement Feishu handlers

**Files:**
- Create: `app/bot/handlers/feishu.py`

- [ ] **Step 1: Write module**

```python
"""Feishu group binding commands — TG control plane part 2."""

from __future__ import annotations

from typing import Protocol

from aiogram.types import Message

from app.services.feishu_groups import is_valid_feishu_webhook
from app.services.subscriptions import parse_keywords


class FeishuRepo(Protocol):
    async def upsert_user(self, tg_user_id: int, tg_username: str | None, display_name: str | None): ...
    async def create_feishu_group(self, owner_user_id: int, name: str | None, webhook_url: str, keywords: list[str]): ...
    async def list_feishu_groups(self, owner_user_id: int): ...
    async def remove_feishu_group(self, owner_user_id: int, group_id: int) -> bool: ...
    async def probe_webhook(self, url: str) -> bool: ...


async def handle_add_feishu_group(msg: Message, *, repo: FeishuRepo) -> None:
    u = msg.from_user
    parts = (msg.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("用法：/add_feishu_group &lt;webhook_url&gt; 关键词1, 关键词2")
        return
    _, url, kws_raw = parts
    if not is_valid_feishu_webhook(url):
        await msg.answer("❌ 不是合法的飞书 webhook URL（必须 https://open.feishu.cn/... 或 larksuite.com）")
        return
    try:
        kws = parse_keywords(kws_raw)
    except ValueError as e:
        await msg.answer(f"❌ {e}")
        return
    if not await repo.probe_webhook(url):
        await msg.answer("❌ webhook 不可达，请确认群里机器人仍存在")
        return
    await repo.upsert_user(u.id, u.username, u.full_name)
    group = await repo.create_feishu_group(u.id, None, url, kws)
    await msg.answer(
        f"✅ 已绑定飞书群 #{group['id']}，关键词：{', '.join(kws)}。群里应已收到欢迎卡片。"
    )


async def handle_my_feishu_groups(msg: Message, *, repo: FeishuRepo) -> None:
    groups = await repo.list_feishu_groups(msg.from_user.id)
    if not groups:
        await msg.answer("你还没有绑定任何飞书群。用 /add_feishu_group 开始。")
        return
    lines = ["<b>你的飞书群：</b>"]
    for g in groups:
        status = "✅" if g["status"] == "active" else "⚠️ 已断开"
        name = g.get("name") or "(未命名)"
        lines.append(f"#{g['id']}  {name}  {status}  keywords={','.join(g['keywords'])}")
    await msg.answer("\n".join(lines))


async def handle_remove_feishu_group(msg: Message, *, repo: FeishuRepo) -> None:
    arg = (msg.text or "").partition(" ")[2].strip()
    if not arg.isdigit():
        await msg.answer("用法：/remove_feishu_group &lt;id&gt;")
        return
    ok = await repo.remove_feishu_group(msg.from_user.id, int(arg))
    await msg.answer("✅ 已解绑" if ok else "❌ 群不存在或不属于你")
```

- [ ] **Step 2: Extend `DbPersonalRepo` → `DbBotRepo` with feishu methods**

Rename the class and add methods. Replace `app/bot/repo.py` content:

```python
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
            delete(Subscription).where(Subscription.delivery_targets.any(f"feishu:{group_id}"))
        )
        await self._s.commit()
        return result.rowcount > 0

    async def probe_webhook(self, url: str) -> bool:
        payload = {"msg_type": "text", "content": {"text": "TrendRadar 已绑定本群 ✅"}}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
            if 200 <= resp.status_code < 300:
                body = resp.json() if resp.content else {}
                return int(body.get("code", 0)) == 0
            return False
        except (httpx.TimeoutException, httpx.NetworkError):
            return False
```

- [ ] **Step 3: Update `bot/main.py` imports and registration**

Change `from app.bot.repo import DbPersonalRepo` to `from app.bot.repo import DbBotRepo` and the `DbPersonalRepo(session)` call to `DbBotRepo(session)`.

Then add Feishu handler registrations in `main()` after the personal ones:

```python
from app.bot.handlers import feishu as feishu_handlers

dp.message.register(_with_repo(feishu_handlers.handle_add_feishu_group), Command("add_feishu_group"))
dp.message.register(_with_repo(feishu_handlers.handle_my_feishu_groups), Command("my_feishu_groups"))
dp.message.register(_with_repo(feishu_handlers.handle_remove_feishu_group), Command("remove_feishu_group"))
```

- [ ] **Step 4: Run all unit tests**

Run: `uv run pytest tests/unit -v`
Expected: all previously passing tests still PASS + 5 new Feishu handler tests PASS.

### Task 7.3: Commit

- [ ] **Step 1: Commit**

```bash
git add app/bot/handlers/feishu.py app/bot/repo.py app/bot/main.py tests/unit/test_handlers_feishu.py
git commit -m "feat(bot): add Feishu group binding commands (TG control plane)"
```

---

## Phase 8: Celery tasks (crawl + dispatch + push)

### Task 8.1: Redis AOF in docker-compose

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Change the `redis` service command**

Replace:
```yaml
  redis:
    image: redis:7-alpine
    container_name: trendradar-redis
    restart: unless-stopped
```
with:
```yaml
  redis:
    image: redis:7-alpine
    container_name: trendradar-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
```

- [ ] **Step 2: Recreate the container**

```bash
docker compose up -d --force-recreate redis
```

- [ ] **Step 3: Verify AOF enabled**

Run: `docker exec trendradar-redis redis-cli CONFIG GET appendonly`
Expected output:
```
appendonly
yes
```

### Task 8.2: Celery config hardening

**Files:**
- Modify: `app/worker/celery_app.py`

- [ ] **Step 1: Replace content**

```python
from __future__ import annotations

from celery import Celery

from app.config import get_settings

_settings = get_settings()

celery_app: Celery = Celery(
    "trendradar",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_hijack_root_logger=False,
    # --- ADR-011 hardening ---
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # --- beat ---
    beat_schedule={
        "hourly-crawl": {
            "task": "app.tasks.crawl",
            "schedule": 3600.0,
        },
    },
)
```

### Task 8.3: crawl_task test

**Files:**
- Create: `tests/unit/test_tasks_crawl.py`

- [ ] **Step 1: Write failing test**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.worker import tasks as tasks_mod
from trendradar.api import CrawledItem


@pytest.mark.unit
async def test_persist_items_inserts_on_conflict(monkeypatch):
    saved: list[str] = []

    class _Session:
        async def execute(self, stmt):
            saved.append(str(stmt.compile(compile_kwargs={"literal_binds": False})).split("\n")[0])
            return MagicMock()
        async def commit(self): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass

    monkeypatch.setattr(tasks_mod, "AsyncSessionLocal", lambda: _Session())

    items = [CrawledItem("fp1", "HN", None, "t", "https://x/", None, None, {})]
    await tasks_mod._persist_crawl(items)

    assert saved, "expected at least one INSERT statement to be executed"
    assert any("INSERT INTO crawl_history" in s for s in saved)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/unit/test_tasks_crawl.py -v`
Expected: `AttributeError: module 'app.worker.tasks' has no attribute '_persist_crawl'`.

### Task 8.4: Implement crawl_task + dispatch_task + push_task

**Files:**
- Modify: `app/worker/tasks.py`

- [ ] **Step 1: Replace content**

```python
"""Celery tasks: crawl, dispatch, push (ADR-011 idempotent)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.fingerprint import fingerprint as _fp
from app.models import (
    CrawlHistory, DeliveryLog, DispatchState, FeishuGroup, Subscription, User,
)
from app.pushers.base import BrokenChannel, PushContext, PushResult, Retryable
from app.pushers.feishu import FeishuPusher
from app.pushers.telegram import TelegramPusher
from app.services.dispatcher import item_matches
from app.worker.celery_app import celery_app
from trendradar.api import CrawledItem, fetch_all

log = logging.getLogger(__name__)


# ---------- CRAWL ----------

@celery_app.task(name="app.tasks.crawl")
def crawl_task() -> int:
    items = list(fetch_all())
    asyncio.run(_persist_crawl(items))
    # chain to dispatch
    dispatch_task.delay()
    return len(items)


async def _persist_crawl(items: Iterable[CrawledItem]) -> None:
    async with AsyncSessionLocal() as s:
        for item in items:
            stmt = (
                pg_insert(CrawlHistory)
                .values(
                    fingerprint=item.fingerprint, source=item.source, category=item.category,
                    title=item.title, url=item.url, summary=item.summary,
                    published_at=item.published_at, raw=item.raw,
                )
                .on_conflict_do_update(
                    index_elements=[CrawlHistory.fingerprint],
                    set_={"last_seen_at": CrawlHistory.__table__.c.last_seen_at.default.arg},
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
            select(CrawlHistory).where(CrawlHistory.first_seen_at > state.last_dispatched_at)
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
def push_task(self, subscription_id: int, fingerprint: str, delivery_target: str, tg_user_id: int) -> str:
    try:
        return asyncio.run(_push_impl(subscription_id, fingerprint, delivery_target, tg_user_id))
    except BrokenChannel as e:
        asyncio.run(_mark_broken(delivery_target, str(e)))
        return "broken"


async def _push_impl(sub_id: int, fp: str, target: str, tg_user_id: int) -> str:
    async with AsyncSessionLocal() as s:
        # ADR-011 ② — INSERT placeholder BEFORE external call
        ins = pg_insert(DeliveryLog).values(
            subscription_id=sub_id, item_fingerprint=fp, delivery_target=target,
        ).on_conflict_do_nothing(
            index_elements=["subscription_id", "item_fingerprint", "delivery_target"]
        ).returning(DeliveryLog.id)
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
                select(FeishuGroup).where(FeishuGroup.id == group_id, FeishuGroup.status == "active")
            )).scalar_one_or_none()
            if group is None:
                return PushResult.SKIPPED.value
            pusher = FeishuPusher()
            ctx = PushContext(target_external_id=group.webhook_url)
        else:
            log.warning("unknown delivery target: %s", target)
            return PushResult.SKIPPED.value

        item_dto = CrawledItem(
            fingerprint=item.fingerprint, source=item.source, category=item.category,
            title=item.title, url=item.url, summary=item.summary,
            published_at=item.published_at, raw=item.raw,
        )

        try:
            result = await pusher.push(ctx, item_dto)
        except Retryable as e:
            async with AsyncSessionLocal() as s2:
                await s2.execute(
                    update(DeliveryLog).where(DeliveryLog.id == row_id)
                    .values(retry_count=DeliveryLog.retry_count + 1, last_error=str(e))
                )
                await s2.commit()
            raise

    async with AsyncSessionLocal() as s3:
        await s3.execute(
            update(DeliveryLog).where(DeliveryLog.id == row_id)
            .values(sent_at=update_now())
        )
        await s3.commit()
    return result.value


def update_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


async def _mark_broken(target: str, err: str) -> None:
    if target == "telegram":
        return  # TG-level breakage is surfaced as BrokenChannel but bot-user id is always valid
    if target.startswith("feishu:"):
        async with AsyncSessionLocal() as s:
            gid = int(target.split(":", 1)[1])
            await s.execute(
                update(FeishuGroup).where(FeishuGroup.id == gid)
                .values(status="broken", last_broken_at=update_now())
            )
            await s.commit()


# keep ping for health
@celery_app.task(name="app.ping")
def ping() -> str:
    return "pong"
```

- [ ] **Step 2: Run crawl_task test**

Run: `uv run pytest tests/unit/test_tasks_crawl.py -v`
Expected: PASS.

### Task 8.5: Commit

- [ ] **Step 1: Commit**

```bash
git add docker-compose.yml app/worker/celery_app.py app/worker/tasks.py tests/unit/test_tasks_crawl.py
git commit -m "feat(worker): implement crawl + dispatch + push tasks with ADR-011 idempotency"
```

---

## Phase 9: Observability

### Task 9.1: Heartbeat writer

**Files:**
- Create: `app/worker/heartbeat.py`

- [ ] **Step 1: Write module**

```python
"""Worker heartbeat — writes a Redis key every 60s with TTL 120s.

Read by app.api.health /healthz?deep=1 to detect silent hangs (H2).
"""

from __future__ import annotations

import logging
import socket
import time

import redis

from app.config import get_settings

log = logging.getLogger(__name__)

_KEY_PREFIX = "trendradar:worker:heartbeat:"
_TTL_SECONDS = 120
_INTERVAL_SECONDS = 60


def start_heartbeat() -> None:
    """Spawn a background thread that ticks every INTERVAL seconds."""
    import threading
    t = threading.Thread(target=_loop, daemon=True, name="heartbeat")
    t.start()


def _loop() -> None:
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    key = _KEY_PREFIX + socket.gethostname()
    while True:
        try:
            client.set(key, str(int(time.time())), ex=_TTL_SECONDS)
        except Exception as e:
            log.warning("heartbeat failed: %s", e)
        time.sleep(_INTERVAL_SECONDS)


def read_latest() -> int | None:
    """Return the newest heartbeat epoch across all workers, or None."""
    settings = get_settings()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys = client.keys(_KEY_PREFIX + "*")
        if not keys:
            return None
        values = client.mget(keys)
        latest = max((int(v) for v in values if v), default=None)
        return latest
    except Exception:
        return None
```

- [ ] **Step 2: Register heartbeat in Celery worker init**

Modify `app/worker/celery_app.py`, append at the end:

```python
from celery.signals import worker_ready


@worker_ready.connect
def _on_worker_ready(**_) -> None:
    from app.worker.heartbeat import start_heartbeat
    start_heartbeat()
```

### Task 9.2: /healthz?deep=1 implementation

**Files:**
- Create: `app/api/health.py`
- Modify: `app/api/main.py`

- [ ] **Step 1: Write `app/api/health.py`**

```python
"""Health endpoints (shallow + deep)."""

from __future__ import annotations

import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.worker.heartbeat import read_latest

router = APIRouter()

_HEARTBEAT_MAX_AGE = 300  # 5 minutes


@router.get("/healthz")
async def healthz(deep: int = 0, response: Response = None) -> dict:
    status: dict[str, str] = {"status": "ok"}
    if not deep:
        return status

    settings = get_settings()
    # 1) Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"fail: {e}"

    # 2) Redis
    try:
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"fail: {e}"

    # 3) Worker heartbeat freshness
    last = read_latest()
    if last is None:
        status["worker_heartbeat"] = "missing"
    else:
        age = int(time.time()) - last
        status["worker_heartbeat"] = f"age={age}s"
        if age > _HEARTBEAT_MAX_AGE:
            status["worker_heartbeat"] += " (stale)"

    if any(v != "ok" and not str(v).startswith("age=") for k, v in status.items() if k != "status"):
        status["status"] = "degraded"
        if response is not None:
            response.status_code = 503
    return status
```

- [ ] **Step 2: Wire router in `app/api/main.py`**

Replace content:

```python
"""FastAPI app — V1 exposes /healthz and /healthz?deep=1."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.observability.sentry import init_sentry

init_sentry("api")

app = FastAPI(title="TrendRadar Platform", version="0.1.0")
app.include_router(health_router)
```

### Task 9.3: Sentry init helper

**Files:**
- Create: `app/observability/__init__.py` (empty)
- Create: `app/observability/sentry.py`

- [ ] **Step 1: Add optional Sentry dep to `pyproject.toml`**

Append to dependencies list in `[project]`:

```toml
    "sentry-sdk>=2.15",
```

Then run: `uv sync`

- [ ] **Step 2: Create empty `__init__.py`**

Run: `touch app/observability/__init__.py`

- [ ] **Step 3: Write sentry helper**

```python
"""Sentry initialization — safe to call from any process.

Reads SENTRY_DSN from env; no-ops silently if unset.
"""

from __future__ import annotations

import os


def init_sentry(proc: str) -> None:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("APP_ENV", "local"),
        traces_sample_rate=0.1,
    )
    sentry_sdk.set_tag("proc", proc)
```

- [ ] **Step 4: Add `init_sentry` calls to bot + worker + beat**

Modify `app/bot/main.py` top of `main()`:

```python
from app.observability.sentry import init_sentry
init_sentry("bot")
```

Modify `app/worker/celery_app.py` near top (after `_settings`):

```python
from app.observability.sentry import init_sentry
init_sentry("worker")  # also used by beat — tag is good enough
```

- [ ] **Step 5: Smoke test — imports work**

Run: `uv run python -c "from app.api.main import app; print('ok')"`
Expected: `ok`.

### Task 9.4: Commit

- [ ] **Step 1: Commit**

```bash
git add app/worker/heartbeat.py app/worker/celery_app.py app/api/ app/observability/ app/bot/main.py pyproject.toml
git commit -m "feat(observability): heartbeat + /healthz?deep=1 + Sentry init across 4 processes"
```

---

## Phase 10: Integration tests

### Task 10.1: Create integration fixtures

**Files:**
- Create: `tests/integration/conftest.py`

- [ ] **Step 1: Write conftest**

```python
"""Integration fixtures — real Postgres + Redis via docker compose.

Preconditions (executed manually or by Makefile):
  docker compose up -d postgres redis
  uv run alembic upgrade head
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


@pytest.fixture(scope="module")
def engine():
    settings = get_settings()
    eng = create_async_engine(settings.database_url, future=True)
    yield eng


@pytest.fixture
async def db(engine) -> AsyncIterator[AsyncSession]:
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        # clean up per test
        for tbl in ("delivery_log", "subscriptions", "feishu_groups", "crawl_history",
                    "dispatch_state", "users"):
            await session.execute(text(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE"))
        await session.commit()
```

### Task 10.2: Subscribe flow integration test

**Files:**
- Create: `tests/integration/test_subscribe_flow.py`

- [ ] **Step 1: Write test**

```python
import pytest

from app.bot.repo import DbBotRepo


@pytest.mark.integration
async def test_upsert_user_then_subscribe(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "alice", "Alice")
    sub = await repo.create_subscription(111, ["ai", "rag"], ["telegram"])
    assert sub["id"] >= 1
    listed = await repo.list_subscriptions(111)
    assert len(listed) == 1
    assert set(listed[0]["keywords"]) == {"ai", "rag"}


@pytest.mark.integration
async def test_delete_subscription(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "alice", "Alice")
    sub = await repo.create_subscription(111, ["ai"], ["telegram"])
    ok = await repo.delete_subscription(111, sub["id"])
    assert ok is True
    assert await repo.list_subscriptions(111) == []


@pytest.mark.integration
async def test_delete_foreign_subscription_denied(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(111, "a", "A")
    await repo.upsert_user(222, "b", "B")
    sub = await repo.create_subscription(111, ["ai"], ["telegram"])
    ok = await repo.delete_subscription(222, sub["id"])
    assert ok is False
    assert await repo.list_subscriptions(111) != []
```

- [ ] **Step 2: Run (requires `docker compose up -d` + `alembic upgrade head`)**

Run: `uv run pytest tests/integration/test_subscribe_flow.py -v`
Expected: 3 PASS.

### Task 10.3: Dispatch idempotency test

**Files:**
- Create: `tests/integration/test_dispatch_idempotency.py`

- [ ] **Step 1: Write test**

```python
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.bot.repo import DbBotRepo
from app.models import CrawlHistory, DeliveryLog


@pytest.mark.integration
async def test_dispatch_dedup_via_unique_constraint(db):
    repo = DbBotRepo(db)
    await repo.upsert_user(555, "eve", "Eve")
    sub = await repo.create_subscription(555, ["gpt"], ["telegram"])

    # insert a crawl_history item
    db.add(CrawlHistory(
        fingerprint="fp-x", source="HN", title="GPT-5 released", url="https://example.com/",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    ))
    await db.commit()

    # simulate two parallel push_task runs for the same (sub, fp, target)
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for _ in range(2):
        stmt = pg_insert(DeliveryLog).values(
            subscription_id=sub["id"], item_fingerprint="fp-x", delivery_target="telegram",
        ).on_conflict_do_nothing(
            index_elements=["subscription_id", "item_fingerprint", "delivery_target"]
        )
        await db.execute(stmt)
    await db.commit()

    rows = (await db.execute(select(DeliveryLog))).scalars().all()
    assert len(rows) == 1, "UNIQUE(subscription_id, item_fingerprint, delivery_target) must enforce dedup"
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/integration/test_dispatch_idempotency.py -v`
Expected: PASS.

### Task 10.4: Feishu bind + crawl on-conflict test

**Files:**
- Create: `tests/integration/test_feishu_bind.py`
- Create: `tests/integration/test_crawl_onconflict.py`

- [ ] **Step 1: Write feishu bind test**

```python
import pytest
import respx
import httpx

from app.bot.repo import DbBotRepo

GOOD_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/token-xyz"


@pytest.mark.integration
@respx.mock
async def test_probe_webhook_success(db):
    respx.post(GOOD_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    repo = DbBotRepo(db)
    assert await repo.probe_webhook(GOOD_URL) is True


@pytest.mark.integration
@respx.mock
async def test_bind_and_list(db):
    respx.post(GOOD_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
    repo = DbBotRepo(db)
    await repo.upsert_user(777, "bob", "Bob")
    group = await repo.create_feishu_group(777, "AI 前沿群", GOOD_URL, ["rag", "agent"])
    assert group["id"] >= 1
    listed = await repo.list_feishu_groups(777)
    assert len(listed) == 1
    assert set(listed[0]["keywords"]) == {"rag", "agent"}
```

- [ ] **Step 2: Write crawl on-conflict test**

```python
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
        fingerprint="fp-dup", source="HN", title="T", url="https://x/",
        first_seen_at=now1, last_seen_at=now1,
    ).on_conflict_do_update(
        index_elements=[CrawlHistory.fingerprint],
        set_={"last_seen_at": now1},
    )
    await db.execute(stmt1); await db.commit()

    stmt2 = pg_insert(CrawlHistory).values(
        fingerprint="fp-dup", source="HN", title="T", url="https://x/",
        first_seen_at=now2, last_seen_at=now2,
    ).on_conflict_do_update(
        index_elements=[CrawlHistory.fingerprint],
        set_={"last_seen_at": now2},
    )
    await db.execute(stmt2); await db.commit()

    rows = (await db.execute(select(CrawlHistory))).scalars().all()
    assert len(rows) == 1, "fingerprint UNIQUE must keep it to 1 row"
    assert rows[0].first_seen_at == now1, "first_seen_at must NOT be overwritten"
    assert rows[0].last_seen_at == now2, "last_seen_at MUST be updated"
```

- [ ] **Step 3: Run all integration tests**

Run: `uv run pytest tests/integration -v`
Expected: all PASS.

### Task 10.5: Commit

- [ ] **Step 1: Commit**

```bash
git add tests/integration/
git commit -m "test(integration): subscribe flow + dispatch dedup + feishu bind + crawl on-conflict"
```

---

## Phase 11: E2E Manual Verification Checklist

This phase has no code. Execute the following end-to-end validation by hand and tick each item. Failures block V1 acceptance.

### Task 11.1: Pre-flight

- [ ] `docker compose ps` shows `trendradar-postgres` and `trendradar-redis` both **healthy**
- [ ] `uv run alembic upgrade head` prints `INFO ... -> <hash>` (or `INFO ... is up to date`)
- [ ] `uv run pytest -q` prints `N passed` with **zero failures**

### Task 11.2: Start the four processes in separate terminals

```
Terminal A:  uv run python -m app.bot.main
Terminal B:  uv run uvicorn app.api.main:app --port 8000
Terminal C:  uv run celery -A app.worker.celery_app worker --concurrency=1 --loglevel=INFO
Terminal D:  uv run celery -A app.worker.celery_app beat --loglevel=INFO
```

- [ ] A prints `Start polling` (no traceback)
- [ ] B serves 200 on `curl http://localhost:8000/healthz`
- [ ] C prints `celery@<host> ready.`
- [ ] D prints `beat: Starting...`

### Task 11.3: Personal subscription flow

From your phone:

- [ ] Send `/start` to the dev bot — receives welcome help text
- [ ] Send `/subscribe 大模型, agent` — receives `已订阅 #1：大模型, agent`
- [ ] Send `/list` — sees the subscription listed
- [ ] Manually trigger a crawl: in terminal, `uv run python -c "from app.worker.tasks import crawl_task; crawl_task()"`
- [ ] Wait ≤ 2 minutes → phone receives at least one matching item
- [ ] Run `psql` query: `SELECT count(*) FROM delivery_log WHERE sent_at IS NOT NULL;` returns > 0

### Task 11.4: Deep health

- [ ] `curl 'http://localhost:8000/healthz?deep=1' | jq` — returns `postgres: ok, redis: ok, worker_heartbeat: age=...s`

### Task 11.5: Dedup verification

- [ ] Invoke `crawl_task()` a second time
- [ ] Phone does **NOT** receive duplicates
- [ ] `SELECT count(*) FROM delivery_log;` did **not** increase (since no new items were crawled)

### Task 11.6: Feishu group binding (requires a real Feishu test group)

- [ ] In Feishu, create a private group + add custom webhook bot; copy the webhook URL
- [ ] In TG: `/add_feishu_group <url> 大模型, agent`
- [ ] Group receives the welcome test card
- [ ] Trigger a crawl → group receives matching items as rich cards
- [ ] `/my_feishu_groups` lists the group with status `✅`

### Task 11.7: Broken channel fallback

- [ ] In Feishu, **delete** the custom bot from the group (simulates webhook failure)
- [ ] Trigger a crawl
- [ ] Celery worker log shows `BrokenChannel` handled
- [ ] `SELECT status FROM feishu_groups WHERE id = ...;` returns `broken`

### Task 11.8: Worker hang detection

- [ ] Send Celery worker SIGSTOP (simulate stuck): `kill -STOP <pid>`
- [ ] Wait > 5 minutes
- [ ] `curl 'http://localhost:8000/healthz?deep=1'` returns 503 + `worker_heartbeat: age=... (stale)`
- [ ] Resume: `kill -CONT <pid>` → next heartbeat tick restores health

---

## Self-Review (before handoff)

**Spec coverage — every V1 feature in product-spec.md §4 is implemented:**
- F1 `/start` — Task 6.2
- F2 `/subscribe` — Task 6.2
- F3 `/list` — Task 6.2
- F4 `/unsubscribe` — Task 6.2
- F5 hourly crawl — Task 8.2 (beat schedule) + 8.4 (crawl_task)
- F6 contains match + subscription filter — Task 5.5 (dispatcher) + 8.4 (dispatch_task)
- F7 TG push on match — Task 4.4 (TelegramPusher) + 8.4 (push_task)
- F8 delivery_log dedup — Task 1.6 (UNIQUE) + 8.4 (push_task INSERT-first)
- F9 `/now` — covered by manual `crawl_task()` trigger in Task 11.3 (V1 acceptable; full `/now` command deferred to post-V1 if wanted)
- F10 curated sources — inherited from `config/config.yaml`
- F11 Feishu push — Task 4.6
- F12 `/add_feishu_group` — Task 7.2
- F13 `/my_feishu_groups`, `/remove_feishu_group` — Task 7.2
- F14 multi-target subscription — Task 1.2 (`delivery_targets TEXT[]`)
- `/pause`, `/resume` — Task 6.2

**Architecture alignment:**
- ADR-001 Oracle VM — deferred to deployment, local dev covers it
- ADR-002 Postgres — Phases 0, 1
- ADR-003 Celery + Redis — Phase 8
- ADR-004 TG control plane + Feishu — Phases 6, 7
- ADR-005 contains match — Task 5.6
- ADR-006 aiogram v3 — Phase 6
- ADR-008 trendradar engine — Phase 3
- ADR-009 Alembic migration policy — Phase 1
- ADR-011 idempotency — Phases 1 + 8

**Placeholder scan — none found.** All steps have concrete code, paths, and commands.

**Type consistency check:**
- `CrawledItem` fields (fingerprint/source/category/title/url/summary/published_at/raw) are identical in Phase 3, 4, 8.
- Handler signatures `handle_xxx(msg: Message, *, repo: XxxRepo)` — consistent across Phase 6 and 7.
- `DeliveryLog` UNIQUE key order `(subscription_id, item_fingerprint, delivery_target)` — matches in Phase 1, 8, 10.

**Potential gap:** `/now` command (immediate crawl trigger from bot) is NOT a separate handler — it's acceptable to defer per product-spec Q19 ("dispatch_task reusable across triggers") and the manual trigger in Task 11.3 shows end-to-end works. If `/now` needed in V1, add a small handler calling `crawl_task.delay()` and register it — ~5 minutes.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-24-trend-radar-platformization-v1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
