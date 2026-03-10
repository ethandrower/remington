"""Team members schema: Slack ↔ Jira ID mapping for the team roster."""

from sqlalchemy import Table, Column, Integer, String, Boolean, Float, Text, Index

from ._meta import metadata

team_members = Table(
    "team_members",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("display_name", String(255), nullable=False),
    Column("jira_account_id", String(255), nullable=True),
    Column("jira_display_name", String(255), nullable=True),
    Column("slack_user_id", String(50), nullable=True),
    Column("slack_display_name", String(255), nullable=True),
    Column("email", String(255), nullable=True),
    Column("role", String(50), nullable=True),  # dev | wa | tech_lead | pm | ceo | operations
    Column("weekly_capacity_hours", Float, nullable=True, default=40.0),
    Column("is_active", Boolean, default=True, nullable=False),
    Column("notes", Text, nullable=True),
    Column("created_at", String(50), nullable=False),
    Column("updated_at", String(50), nullable=False),
)

Index("idx_team_members_jira_id", team_members.c.jira_account_id)
Index("idx_team_members_slack_id", team_members.c.slack_user_id)
