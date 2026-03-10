"""
Activity schema: audit log for all PM agent actions.
"""

from sqlalchemy import Table, Column, Integer, String, Text, DateTime, Boolean, Index

from ._meta import metadata

activities = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime, nullable=False),
    Column("activity_type", Text, nullable=False),
    Column("details", Text),
    Column("item_id", Text),
    Column("success", Boolean, default=True),
)

Index("idx_activity_timestamp", activities.c.timestamp)
Index("idx_activity_type", activities.c.activity_type)
