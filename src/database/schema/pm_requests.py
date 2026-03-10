"""
PM Requests schema: approval workflow tracking for Jira ticket creation.
"""

from sqlalchemy import (
    Table, Column, Integer, String, Text, DateTime, ForeignKey, Index
)

from ._meta import metadata

pending_pm_requests = Table(
    "pending_pm_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", Text, unique=True, nullable=False),
    Column("source", Text, nullable=False),       # 'jira' | 'slack' | 'bitbucket'
    Column("source_id", Text, nullable=False),     # issue_key | thread_ts | pr_id
    Column("request_type", Text, nullable=False),  # 'story' | 'bug' | 'epic'
    Column("user_id", Text, nullable=False),
    Column("user_name", Text, nullable=False),
    Column("original_context", Text, nullable=False),
    Column("draft_content", Text, nullable=False),
    Column("status", Text, default="pending"),
    Column("jira_ticket_key", Text),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    Column("approved_at", DateTime),
    Column("created_ticket_at", DateTime),
)

Index("idx_pm_request_id", pending_pm_requests.c.request_id)
Index("idx_pm_source_id", pending_pm_requests.c.source, pending_pm_requests.c.source_id)
Index("idx_pm_status", pending_pm_requests.c.status)
Index("idx_pm_user_pending", pending_pm_requests.c.user_id, pending_pm_requests.c.status)


pm_request_revisions = Table(
    "pm_request_revisions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "request_id",
        Text,
        ForeignKey("pending_pm_requests.request_id"),
        nullable=False,
    ),
    Column("revision_number", Integer, nullable=False),
    Column("draft_content", Text, nullable=False),
    Column("feedback", Text),
    Column("created_at", DateTime),
)

Index("idx_pm_revision_request", pm_request_revisions.c.request_id)
