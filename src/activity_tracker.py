#!/usr/bin/env python3
"""
Activity Tracker - Database logging for all PM agent activities
Provides metrics for heartbeat reporting and audit trails
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class ActivityTracker:
    """Track all PM agent activities in database"""

    def __init__(self, db_path: str = ".claude/data/bot-state/activity.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self):
        """Initialize activity tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activity_type TEXT NOT NULL,
                    details TEXT,
                    item_id TEXT,
                    success BOOLEAN DEFAULT 1
                )
            """)

            # Index for fast time-range queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON activities(timestamp)
            """)

            # Index for activity type queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type
                ON activities(activity_type)
            """)

    def log(self, activity_type: str, details: str = None, item_id: str = None, success: bool = True):
        """
        Log an activity

        Activity types:
        - polling_slack
        - polling_jira
        - polling_bitbucket
        - sla_check
        - standup_report
        - pm_story_draft
        - pm_story_approved
        - pm_story_created
        - jira_comment_posted
        - slack_message_posted
        - heartbeat
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO activities (activity_type, details, item_id, success) VALUES (?, ?, ?, ?)",
                (activity_type, details, item_id, 1 if success else 0)
            )

    def get_recent_summary(self, hours: int = 1) -> Dict[str, int]:
        """Get count of activities by type in last N hours"""
        since = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM activities
                WHERE timestamp >= ?
                GROUP BY activity_type
                ORDER BY count DESC
            """, (since.isoformat(),))

            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_last_activity(self, activity_type: str) -> Optional[datetime]:
        """Get timestamp of last activity of a given type"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp
                FROM activities
                WHERE activity_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (activity_type,))

            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0])
            return None

    def get_recent_activities(self, limit: int = 50) -> List[Dict]:
        """Get recent activities for debugging"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, activity_type, details, item_id, success
                FROM activities
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return [{
                "timestamp": row[0],
                "type": row[1],
                "details": row[2],
                "item_id": row[3],
                "success": bool(row[4])
            } for row in cursor.fetchall()]


# Singleton instance
_tracker = None


def get_tracker() -> ActivityTracker:
    """Get global activity tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = ActivityTracker()
    return _tracker
