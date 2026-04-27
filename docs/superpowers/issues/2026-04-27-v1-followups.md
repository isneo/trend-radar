# V1 Platformization — Post-E2E Follow-ups

**Recorded:** 2026-04-27 (after Phase 11 manual verification)
**Branch:** feat/v1-platformization

These issues were observed during Phase 11 manual verification but did not block
V1 acceptance. Captured here for V1.x triage.

---

## #2 Dispatch enqueue count > delivery_log row count

### Symptom

A dispatch run reported `enqueued: 24` (3 subscriptions × matching items), but
only 13 rows ever appeared in `delivery_log` (11 telegram + 2 feishu) for that
batch. Eleven push_task invocations left no trace — no placeholder row, no log,
no celery result entry, queue length back to zero.

### Suspected root causes (not confirmed)

1. **Stale ghost worker:** at the time of the run there were two celery worker
   processes on the host (one from a previous session, one freshly started).
   Tasks were split between them; the older worker was killed mid-flight,
   discarding any in-flight tasks.
2. **`asyncio.run()` double-call bug** (fixed in 0992b34): `push_task` used to
   call `asyncio.run()` twice — once for `_push_impl`, once for `_mark_broken`.
   The second call could fail with `RuntimeError: Event loop is closed`
   because asyncpg's global engine still holds connections from the closed
   loop. This swallowed both BrokenChannel handling AND any post-INSERT state
   updates. With the consolidation fix, this branch now uses a single loop.

### Recommended hardening

- **acks_late=True + visibility_timeout** on `push_task` so a worker crash
  re-queues the task instead of dropping it.
- **Per-task structured log line** at start/end (`task_id`, `sub_id`, `fp`,
  `target`, `outcome`) so loss is detectable without re-deriving from queue
  state.
- **Reproduction harness**: enqueue N push_tasks for known-good fingerprints
  against a clean delivery_log, assert N rows after worker drains.

### Status
Open. Most likely already mitigated by 0992b34, but worth a reproduction
attempt before V1 GA.

---

## #3 Heartbeat does not detect prefork child task hang

### Symptom

`/healthz?deep=1` reports `worker_heartbeat: ok` even when the prefork child
worker is stuck on a single task forever. The heartbeat thread runs in the
celery main process; the main process keeps writing to Redis even when no
task is making progress.

### Verified during Phase 11.8

`kill -STOP <prefork_child_pid>` had **zero effect** on healthz output — main
process kept writing heartbeat. Only `kill -STOP <main_pid>` triggered the
stale state.

### Recommended addition

- **`last_task_completed_at` heartbeat** written from the prefork child via
  the `task_postrun` celery signal. Health endpoint reads both this and the
  main heartbeat; flags `degraded` if either is stale.
- **Per-task watchdog**: enforce a hard task timeout (`time_limit`) on
  `push_task` so a stuck worker eventually crashes and is detected by the
  main-process liveness signal.

### Status
Out of V1 scope. V1 ships with main-process liveness only; document the gap
in the ops runbook.

---

## Cross-reference

- Phase 11.7 fix that closed part of #2: `0992b34 fix(worker): consolidate push_task to single asyncio.run for BrokenChannel handling`
- Phase 11.8 verification: heartbeat main-process detection works as designed.
