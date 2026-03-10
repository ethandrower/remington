"""
DB Cleanup — prune high-volume tables to keep storage under control.

Retention policy:
  - slack_processed_messages   7 days  (dedup store; monitor never looks back this far)
  - jira_processed_mentions    7 days
  - bb_processed_pr_comments   7 days
  - confluence_processed_*     7 days
  - activities                 30 days
  - check_runs                 30 days
  - blocked_ticket_analyses    14 days
  - blocked_sent_alerts        3 days  (48h cooldown window + buffer)

Tables we intentionally keep forever:
  - team_members, check_schedules, active_violations
  - timesheet_weeks, timesheet_entries  (financial records)
  - bb_last_pr_commit, bb_last_check_per_repo, jira_last_check  (state tables, tiny)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


TABLES = [
    # (table_name, timestamp_column, retention_days)
    ("slack_processed_messages",    "processed_at",  7),
    ("slack_tracked_threads",       "created_at",    7),
    ("slack_sla_alerts",            "created_at",    7),
    ("jira_processed_mentions",     "processed_at",  7),
    ("bb_processed_pr_comments",    "processed_at",  7),
    ("confluence_processed_comments", "processed_at", 7),
    ("activities",                  "timestamp",     30),
    ("check_runs",                  "started_at",    30),
    ("blocked_ticket_analyses",     "analyzed_at",   14),
    ("blocked_sent_alerts",         "sent_at",        3),
]


def run(dry_run: bool = False) -> dict:
    from src.database.connection import get_engine
    from sqlalchemy import text

    engine = get_engine(default_path=str(PROJECT_ROOT / ".claude/data/bot-state/dashboard.db"))
    now = datetime.utcnow()
    results = {}

    print(f"\n{'='*55}")
    print("  DB CLEANUP")
    print(f"  {'DRY RUN — ' if dry_run else ''}UTC {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    with engine.begin() as conn:
        for table, ts_col, days in TABLES:
            cutoff = now - timedelta(days=days)
            try:
                # Count first
                count_row = conn.execute(text(
                    f"SELECT COUNT(*) FROM {table} WHERE {ts_col} < :cutoff"
                ), {"cutoff": cutoff}).scalar()

                if count_row and not dry_run:
                    conn.execute(text(
                        f"DELETE FROM {table} WHERE {ts_col} < :cutoff"
                    ), {"cutoff": cutoff})

                results[table] = count_row or 0
                flag = " (skipped)" if dry_run else " deleted"
                print(f"  {table:<40} {count_row or 0:>6}{flag}  (>{days}d)")

            except Exception as e:
                # Table may not exist yet on fresh deployments
                results[table] = 0
                print(f"  {table:<40} skipped: {e}")

    total = sum(results.values())
    action = "would delete" if dry_run else "deleted"
    print(f"\n  Total rows {action}: {total}")
    print(f"{'='*55}\n")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prune old rows from high-volume DB tables")
    parser.add_argument("--dry-run", action="store_true", help="Show counts without deleting")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
