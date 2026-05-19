"""
ABOUTME: Periodic pruner for the langgraph_agent checkpoint tables.
ABOUTME: Deletes checkpoints older than RETENTION_DAYS using the UUIDv6 timestamp.

Keeps the agent's persistent state from growing unbounded. Designed to be safe
to run repeatedly — every DELETE is bounded by the retention cutoff, and
deleted rows are state we explicitly do not need to archive (PR review
transcripts, Slack reply context).

LangGraph's PostgresSaver writes checkpoint_id as a UUIDv6, which embeds a
60-bit timestamp (100-ns ticks since the Gregorian epoch 1582-10-15) in its
first 60 bits. UUIDv6 is lexicographically sortable by time, so we can find
"older than N days" with a single ordered comparison.
"""

import os
from datetime import datetime, timedelta, timezone

import psycopg

DEFAULT_RETENTION_DAYS = 30
SCHEMA = "langgraph_agent"

# 100-ns ticks between the Gregorian start (1582-10-15) and the Unix epoch.
_GREGORIAN_TO_UNIX_TICKS = 0x01B21DD213814000


def _datetime_to_uuid6_prefix(dt: datetime) -> str:
    """
    Build a UUIDv6 string whose timestamp == dt and whose remaining bits are
    zero. Used as the < comparator for "everything older than dt".
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    unix_ticks_100ns = int(dt.timestamp() * 10_000_000)
    ticks = unix_ticks_100ns + _GREGORIAN_TO_UNIX_TICKS
    time_high = (ticks >> 28) & 0xFFFFFFFF
    time_mid = (ticks >> 12) & 0xFFFF
    time_low = ticks & 0xFFF
    return f"{time_high:08x}-{time_mid:04x}-6{time_low:03x}-0000-000000000000"


def _normalize_dsn(database_url: str) -> str:
    """Heroku-style postgres:// → psycopg3-compatible postgresql://."""
    return database_url.replace("postgres://", "postgresql://", 1)


def cleanup_old_checkpoints(
    database_url: str | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict:
    """
    Delete langgraph checkpoint rows older than `retention_days`.

    Returns a dict of {table_name: rows_deleted} for logging.

    Safe to call without a DATABASE_URL — returns an empty dict if no
    Postgres is configured (local dev with SQLite).
    """
    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        return {}

    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_uuid = _datetime_to_uuid6_prefix(cutoff_dt)

    deleted: dict[str, int] = {}

    with psycopg.connect(_normalize_dsn(database_url), autocommit=True) as conn:
        with conn.cursor() as cur:
            # If the schema isn't present yet (fresh DB), nothing to do.
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (SCHEMA,),
            )
            if cur.fetchone() is None:
                return {}

            # checkpoint_writes references a checkpoint_id directly.
            cur.execute(
                f"DELETE FROM {SCHEMA}.checkpoint_writes "
                f"WHERE checkpoint_id < %s::uuid",
                (cutoff_uuid,),
            )
            deleted["checkpoint_writes"] = cur.rowcount

            # checkpoints owns the timestamped checkpoint_id column.
            cur.execute(
                f"DELETE FROM {SCHEMA}.checkpoints "
                f"WHERE checkpoint_id < %s::uuid",
                (cutoff_uuid,),
            )
            deleted["checkpoints"] = cur.rowcount

            # checkpoint_blobs has no checkpoint_id — drop any blob whose
            # thread_id no longer appears in checkpoints (orphaned by the
            # two deletes above).
            cur.execute(
                f"DELETE FROM {SCHEMA}.checkpoint_blobs "
                f"WHERE thread_id NOT IN "
                f"(SELECT DISTINCT thread_id FROM {SCHEMA}.checkpoints)"
            )
            deleted["checkpoint_blobs"] = cur.rowcount

    return deleted
