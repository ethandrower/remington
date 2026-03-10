"""
Monitor schemas: deduplication and state tracking for all 4 polling monitors.

Each monitor tracks which messages/comments/PRs have already been processed
so the same item is never acted on twice across restarts.
"""

from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Index

from ._meta import metadata

# ---------------------------------------------------------------------------
# Slack Monitor
# ---------------------------------------------------------------------------

slack_processed_messages = Table(
    "slack_processed_messages",
    metadata,
    Column("ts", Text, primary_key=True),
    Column("channel", Text),
    Column("user_id", Text),
    Column("text", Text),
    Column("response", Text),
    Column("processed_at", DateTime),
)

slack_tracked_threads = Table(
    "slack_tracked_threads",
    metadata,
    Column("thread_ts", Text, primary_key=True),
    Column("channel", Text),
    Column("context", Text),
    Column("last_checked_ts", Text),
    Column("created_at", DateTime),
)

slack_sla_alerts = Table(
    "slack_sla_alerts",
    metadata,
    Column("violation_id", Text, primary_key=True),
    Column("item_id", Text, nullable=False),
    Column("violation_type", Text, nullable=False),
    Column("last_alerted_at", DateTime, nullable=False),
    Column("alert_count", Integer, default=1),
    Column("current_escalation_level", Integer, default=1),
    Column("slack_thread_ts", Text),
    Column("created_at", DateTime),
)

Index("idx_slack_sla_item_type", slack_sla_alerts.c.item_id, slack_sla_alerts.c.violation_type)


# ---------------------------------------------------------------------------
# Jira Monitor
# ---------------------------------------------------------------------------

jira_processed_mentions = Table(
    "jira_processed_mentions",
    metadata,
    Column("issue_key", Text, nullable=False),
    Column("comment_id", Text, nullable=False),
    Column("processed_at", DateTime),
)

# Composite primary key expressed via table args
from sqlalchemy import UniqueConstraint
jira_processed_mentions.append_constraint(
    UniqueConstraint("issue_key", "comment_id", name="uq_jira_mention")
)

jira_last_check = Table(
    "jira_last_check",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", Text),
    Column("updated_at", DateTime),
)


# ---------------------------------------------------------------------------
# Bitbucket Monitor
# ---------------------------------------------------------------------------

bb_processed_pr_comments = Table(
    "bb_processed_pr_comments",
    metadata,
    Column("repo", Text, nullable=False),
    Column("pr_id", Integer, nullable=False),
    Column("comment_id", Text, nullable=False),
    Column("processed_at", DateTime),
)

bb_processed_pr_comments.append_constraint(
    UniqueConstraint("repo", "pr_id", "comment_id", name="uq_bb_pr_comment")
)

bb_last_check_per_repo = Table(
    "bb_last_check_per_repo",
    metadata,
    Column("repo", Text, primary_key=True),
    Column("timestamp", Text),
    Column("updated_at", DateTime),
)

bb_reviewed_pr_commits = Table(
    "bb_reviewed_pr_commits",
    metadata,
    Column("repo", Text, nullable=False),
    Column("pr_id", Integer, nullable=False),
    Column("commit_sha", Text, nullable=False),
    Column("reviewed_at", DateTime),
)

bb_reviewed_pr_commits.append_constraint(
    UniqueConstraint("repo", "pr_id", "commit_sha", name="uq_bb_reviewed_commit")
)

bb_last_pr_commit = Table(
    "bb_last_pr_commit",
    metadata,
    Column("repo", Text, nullable=False),
    Column("pr_id", Integer, nullable=False),
    Column("commit_sha", Text),
    Column("updated_at", DateTime),
)

bb_last_pr_commit.append_constraint(
    UniqueConstraint("repo", "pr_id", name="uq_bb_last_pr_commit")
)


# ---------------------------------------------------------------------------
# Confluence Monitor
# ---------------------------------------------------------------------------

confluence_processed_comments = Table(
    "confluence_processed_comments",
    metadata,
    Column("page_id", Text, nullable=False),
    Column("comment_id", Text, nullable=False),
    Column("processed_at", DateTime),
)

confluence_processed_comments.append_constraint(
    UniqueConstraint("page_id", "comment_id", name="uq_confluence_comment")
)

confluence_last_check = Table(
    "confluence_last_check",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("timestamp", Text),
    Column("updated_at", DateTime),
)
