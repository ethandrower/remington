#!/usr/bin/env python3
"""
ABOUTME: CLI runner for the langgraph checkpoint pruner.
ABOUTME: Deletes agent checkpoints older than --days (default 30) and prints counts.

Usage:
    python scripts/cleanup_checkpoints.py             # 30-day retention
    python scripts/cleanup_checkpoints.py --days 7    # custom retention

Safe to wire into cron, or to invoke ad-hoc via `dokku run`.
"""

import argparse
import sys
from pathlib import Path

# Project root on path
_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root))

from src.utils.checkpoint_cleanup import (  # noqa: E402
    DEFAULT_RETENTION_DAYS,
    cleanup_old_checkpoints,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune old LangGraph agent checkpoints.")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Retention window in days (default: {DEFAULT_RETENTION_DAYS})",
    )
    args = parser.parse_args()

    deleted = cleanup_old_checkpoints(retention_days=args.days)
    if not deleted:
        print("No DATABASE_URL configured (or langgraph_agent schema absent) — nothing to do.")
        return 0

    print(f"Pruned langgraph_agent checkpoints older than {args.days} days:")
    for table, rows in deleted.items():
        print(f"  {table:25s} {rows:>10} rows deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
