"""
Channel configuration helper.

Resolves the Slack channel for a given report type exclusively from the DB
(channel_config table, managed via the dashboard Settings → Channel Assignments UI).

If a channel is not configured in the dashboard, the function returns None
and the caller should skip posting rather than falling back to an ENV var.

Usage:
    from src.utils.channel_config import get_channel

    channel = get_channel("standup")
    if not channel:
        print("No channel configured for standup — configure in dashboard Settings")

Report types (kept in sync with REPORT_TYPES in app.py):
    standup         - daily standup reports
    sla_violations  - SLA violation alerts
    sla_qa_alerts   - QA-specific SLA alerts
    timesheets      - weekly timesheet reports
    blocked_tickets - blocked ticket alerts
    pm_logs         - PM agent internal logs
"""

from typing import Optional


def get_channel(report_type: str) -> Optional[str]:
    """
    Return the Slack channel ID for *report_type* from the channel_config DB table.

    Returns None if:
    - No row exists for this report_type
    - The row has no channel_id set
    - The row is disabled
    - The DB is unreachable

    Callers should treat None as "skip posting".
    """
    try:
        from src.database.connection import get_engine
        from sqlalchemy import text

        engine = get_engine(default_path=".claude/data/bot-state/dashboard.db")
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT channel_id FROM channel_config "
                    "WHERE report_type = :rt AND (enabled IS NULL OR enabled = true)"
                ),
                {"rt": report_type},
            ).first()
            if row and row[0]:
                return row[0]
    except Exception:
        pass

    return None
