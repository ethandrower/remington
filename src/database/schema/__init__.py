"""
SQLAlchemy table definitions for all PM Agent databases.

Import from here to access any table definition or the shared metadata:

    from src.database.schema import metadata, check_runs, activities

Use metadata.create_all(engine) to create all tables at once, or call
individual table.create(engine, checkfirst=True) for a specific table.
"""

from ._meta import metadata

from .dashboard import check_runs, active_violations, check_schedules, blocked_ticket_analyses, blocked_sent_alerts, timesheet_weeks, timesheet_entries, channel_config, system_config
from .pm_requests import pending_pm_requests, pm_request_revisions
from .activity import activities
from .team_members import team_members
from .monitors import (
    slack_processed_messages,
    slack_tracked_threads,
    slack_sla_alerts,
    jira_processed_mentions,
    jira_last_check,
    bb_processed_pr_comments,
    bb_last_check_per_repo,
    bb_reviewed_pr_commits,
    bb_last_pr_commit,
    confluence_processed_comments,
    confluence_last_check,
)

__all__ = [
    "metadata",
    # Dashboard
    "check_runs",
    "active_violations",
    "check_schedules",
    "blocked_ticket_analyses",
    "blocked_sent_alerts",
    "timesheet_weeks",
    "timesheet_entries",
    "channel_config",
    "system_config",
    # PM Requests
    "pending_pm_requests",
    "pm_request_revisions",
    # Activity
    "activities",
    # Team members
    "team_members",
    # Slack monitor
    "slack_processed_messages",
    "slack_tracked_threads",
    "slack_sla_alerts",
    # Jira monitor
    "jira_processed_mentions",
    "jira_last_check",
    # Bitbucket monitor
    "bb_processed_pr_comments",
    "bb_last_check_per_repo",
    "bb_reviewed_pr_commits",
    "bb_last_pr_commit",
    # Confluence monitor
    "confluence_processed_comments",
    "confluence_last_check",
]
