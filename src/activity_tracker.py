"""
Activity Tracker - Audit log for all PM agent actions.

Backed by SQLAlchemy so it works with both SQLite (local/tests) and
PostgreSQL (Heroku production).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_engine
from src.database.schema import metadata, activities


class ActivityTracker:
    """Track all PM agent activities in the database."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        engine: Optional[Engine] = None,
    ):
        """
        Args:
            engine: SQLAlchemy engine (used in tests).
            db_path: SQLite file path when no engine and no DATABASE_URL set.
        """
        if engine is not None:
            self.engine = engine
        elif db_path is not None:
            self.engine = get_engine(default_path=db_path)
        else:
            self.engine = get_engine(
                default_path=".claude/data/bot-state/activity.db"
            )
        self._init_db()

    def _init_db(self):
        """Create the activities table if it doesn't exist."""
        activities.create(self.engine, checkfirst=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log(
        self,
        activity_type: str,
        details: str = None,
        item_id: str = None,
        success: bool = True,
    ):
        """
        Log an activity.

        Activity types:
        - polling_slack / polling_jira / polling_bitbucket
        - sla_check / standup_report
        - pm_story_draft / pm_story_approved / pm_story_created
        - jira_comment_posted / slack_message_posted
        - heartbeat
        """
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO activities (timestamp, activity_type, details, item_id, success)
                    VALUES (:timestamp, :activity_type, :details, :item_id, :success)
                """),
                {
                    "timestamp": datetime.now().isoformat(),
                    "activity_type": activity_type,
                    "details": details,
                    "item_id": item_id,
                    "success": success,
                },
            )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_recent_summary(self, hours: int = 1) -> Dict[str, int]:
        """Return count of activities by type in the last N hours."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT activity_type, COUNT(*) as count
                    FROM activities
                    WHERE timestamp >= :since
                    GROUP BY activity_type
                    ORDER BY count DESC
                """),
                {"since": since},
            ).all()
            return {row[0]: row[1] for row in rows}

    def get_last_activity(self, activity_type: str) -> Optional[datetime]:
        """Return the timestamp of the most recent activity of a given type."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT timestamp FROM activities
                    WHERE activity_type = :activity_type
                    ORDER BY timestamp DESC
                    LIMIT 1
                """),
                {"activity_type": activity_type},
            ).fetchone()
            return datetime.fromisoformat(row[0]) if row else None

    def get_last_activity_details(self, activity_type: str) -> Optional[Dict]:
        """Return the most recent activity of a given type with full details."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT timestamp, details, item_id, success
                    FROM activities
                    WHERE activity_type = :activity_type
                    ORDER BY timestamp DESC
                    LIMIT 1
                """),
                {"activity_type": activity_type},
            ).fetchone()
            if row:
                return {
                    "timestamp": row[0],
                    "details": row[1],
                    "item_id": row[2],
                    "success": bool(row[3]),
                }
            return None

    def get_recent_activities(self, limit: int = 50) -> List[Dict]:
        """Return recent activities for debugging, most recent first."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT timestamp, activity_type, details, item_id, success
                    FROM activities
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).all()
            return [
                {
                    "timestamp": r[0],
                    "type": r[1],
                    "details": r[2],
                    "item_id": r[3],
                    "success": bool(r[4]),
                }
                for r in rows
            ]


# Singleton instance (production use)
_tracker = None


def get_tracker() -> ActivityTracker:
    """Return the global ActivityTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ActivityTracker()
    return _tracker
