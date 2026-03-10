"""
Dashboard schema: SLA check execution history, active violations, schedules,
blocked ticket analyses, alert dedup tracking, and timesheet records.
"""

from sqlalchemy import (
    Table, Column, Integer, String, Float, Boolean, Text, Index, UniqueConstraint
)
from sqlalchemy import DateTime

from ._meta import metadata

check_runs = Table(
    "check_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("check_type", String(50), nullable=False),
    Column("started_at", DateTime, nullable=False),
    Column("completed_at", DateTime),
    Column("duration_seconds", Integer),
    Column("status", String(20), nullable=False),
    Column("violations_found", Integer, default=0),
    Column("critical_count", Integer, default=0),
    Column("warning_count", Integer, default=0),
    Column("output_json", Text),
    Column("error_message", Text),
    Column("triggered_by", String(50), default="scheduled"),
)

Index("idx_check_runs_type", check_runs.c.check_type)
Index("idx_check_runs_started", check_runs.c.started_at)


active_violations = Table(
    "active_violations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", String(50), nullable=False, unique=True),
    Column("violation_type", String(50), nullable=False),
    Column("severity", String(20), nullable=False),
    Column("detected_at", DateTime, nullable=False),
    Column("hours_overdue", Float),
    Column("owner", String(100)),
    Column("title", Text),
    Column("link", Text),
    Column("slack_thread_ts", String(50)),
    Column("escalation_level", Integer, default=1),
    Column("resolved_at", DateTime),
    Column("last_updated", DateTime, nullable=False),
    Column("metadata", Text),  # JSON blob
)

Index("idx_violations_type", active_violations.c.violation_type)
Index("idx_violations_resolved", active_violations.c.resolved_at)


check_schedules = Table(
    "check_schedules",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("check_type", String(50), nullable=False, unique=True),
    Column("schedule_expression", String(100), nullable=False),
    Column("enabled", Boolean, default=True),
    Column("last_run", DateTime),
    Column("next_run", DateTime),
    Column("description", Text),
)


blocked_ticket_analyses = Table(
    "blocked_ticket_analyses",
    metadata,
    Column("key", String(50), primary_key=True),
    Column("summary", Text),
    Column("assignee", String(200)),
    Column("link", Text),
    Column("category", String(50), nullable=False),
    Column("needs_alert", Boolean, default=False),
    Column("action", Text),
    Column("alert_message", Text),
    Column("blocking_tickets", Text),  # JSON blob
    Column("analyzed_at", DateTime, nullable=False),
)

Index("idx_bta_category", blocked_ticket_analyses.c.category)
Index("idx_bta_analyzed", blocked_ticket_analyses.c.analyzed_at)


blocked_sent_alerts = Table(
    "blocked_sent_alerts",
    metadata,
    Column("key", String(50), nullable=False),
    Column("category", String(50), nullable=False),
    Column("sent_at", DateTime, nullable=False),
)

blocked_sent_alerts.append_constraint(
    UniqueConstraint("key", "category", name="uq_blocked_sent_alert")
)


# ── Timesheets ──────────────────────────────────────────────────────────────

timesheet_weeks = Table(
    "timesheet_weeks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(100), nullable=False),
    Column("developer_name", String(200), nullable=False),
    Column("week_start", String(20), nullable=False),   # YYYY-MM-DD
    Column("week_end", String(20), nullable=False),     # YYYY-MM-DD
    Column("total_seconds", Integer, default=0),
    Column("total_estimate_seconds", Integer, default=0),
    Column("recorded_at", DateTime, nullable=False),
    UniqueConstraint("account_id", "week_start", name="uq_timesheet_week"),
)

Index("idx_tsw_week_start", timesheet_weeks.c.week_start)
Index("idx_tsw_account", timesheet_weeks.c.account_id)


timesheet_entries = Table(
    "timesheet_entries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(100), nullable=False),
    Column("week_start", String(20), nullable=False),
    Column("issue_key", String(50), nullable=False),
    Column("summary", Text),
    Column("status", String(100)),
    Column("logged_seconds", Integer, default=0),
    Column("estimate_seconds", Integer, default=0),
    Column("due_date", String(20)),  # YYYY-MM-DD or NULL
    Column("jira_url", Text),
    UniqueConstraint("account_id", "week_start", "issue_key", name="uq_timesheet_entry"),
)

Index("idx_tse_account_week", timesheet_entries.c.account_id, timesheet_entries.c.week_start)


# ── Channel Configuration ────────────────────────────────────────────────────

channel_config = Table(
    "channel_config",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("report_type", String(50), nullable=False),
    Column("label", String(100)),        # Human-readable label
    Column("channel_id", String(50)),    # Slack channel ID e.g. C12345
    Column("channel_name", String(100)), # e.g. #dev-standup
    Column("env_fallback", String(100)), # env var name used as fallback
    Column("enabled", Boolean, default=True),
    Column("updated_at", DateTime),
    UniqueConstraint("report_type", name="uq_channel_config_report_type"),
)


# ── System / Project Configuration ──────────────────────────────────────────
# Generic key-value store for project settings configurable from the dashboard.
# Priority: DB value > ENV fallback > None

system_config = Table(
    "system_config",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("key", String(100), nullable=False),
    Column("value", Text),
    Column("label", String(200)),
    Column("description", Text),
    Column("env_fallback", String(100)),  # env var to read if DB value is empty
    Column("updated_at", DateTime),
    UniqueConstraint("key", name="uq_system_config_key"),
)
