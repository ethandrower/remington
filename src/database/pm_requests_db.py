#!/usr/bin/env python3
"""
PM Requests Database - Approval Workflow Tracking

Manages pending product management requests (stories, bugs, epics)
awaiting user approval before Jira ticket creation.

Database: .claude/data/pm-requests/pm_requests_state.db
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json


class PMRequestsDB:
    """Database manager for PM approval workflow"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize PM requests database

        Args:
            db_path: Path to SQLite database file (default: .claude/data/pm-requests/pm_requests_state.db)
        """
        if db_path is None:
            db_path = Path(".claude/data/pm-requests/pm_requests_state.db")

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

        cursor = self.conn.cursor()

        # Main table: Pending PM requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_pm_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                request_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                original_context TEXT NOT NULL,
                draft_content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                jira_ticket_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                created_ticket_at TIMESTAMP
            )
        """)

        # Indexes for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_id
            ON pending_pm_requests(request_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_id
            ON pending_pm_requests(source, source_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON pending_pm_requests(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_pending
            ON pending_pm_requests(user_id, status)
        """)

        # Revision history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pm_request_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                draft_content TEXT NOT NULL,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES pending_pm_requests(request_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_revision_request
            ON pm_request_revisions(request_id)
        """)

        self.conn.commit()

    def create_request(
        self,
        source: str,
        source_id: str,
        request_type: str,
        user_id: str,
        user_name: str,
        original_context: str,
        draft_content: str
    ) -> str:
        """
        Create a new PM request

        Args:
            source: 'jira' | 'slack' | 'bitbucket'
            source_id: issue_key | thread_ts | pr_id
            request_type: 'story' | 'bug' | 'epic' | 'feature'
            user_id: Requester's account ID
            user_name: Requester's display name
            original_context: Original comment/thread text
            draft_content: Generated draft story/bug/epic

        Returns:
            request_id: UUID of created request
        """
        request_id = str(uuid.uuid4())
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO pending_pm_requests (
                request_id, source, source_id, request_type,
                user_id, user_name, original_context, draft_content, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (request_id, source, source_id, request_type, user_id, user_name, original_context, draft_content))

        # Store initial draft as revision 1
        cursor.execute("""
            INSERT INTO pm_request_revisions (
                request_id, revision_number, draft_content, feedback
            ) VALUES (?, 1, ?, NULL)
        """, (request_id, draft_content))

        self.conn.commit()
        return request_id

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get a request by ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM pending_pm_requests
            WHERE request_id = ?
        """, (request_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_request_by_source(self, source: str, source_id: str) -> Optional[Dict]:
        """Get most recent request for a given source location"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM pending_pm_requests
            WHERE source = ? AND source_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (source, source_id))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_pending_requests(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all pending requests (optionally filtered by user)

        Args:
            user_id: If provided, only return requests from this user

        Returns:
            List of pending request dicts
        """
        cursor = self.conn.cursor()

        if user_id:
            cursor.execute("""
                SELECT * FROM pending_pm_requests
                WHERE status = 'pending' AND user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM pending_pm_requests
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)

        return [dict(row) for row in cursor.fetchall()]

    def update_request_status(
        self,
        request_id: str,
        status: str,
        jira_ticket_key: Optional[str] = None
    ) -> bool:
        """
        Update request status

        Args:
            request_id: UUID of request
            status: 'pending' | 'approved' | 'changes_requested' | 'cancelled' | 'created'
            jira_ticket_key: Jira ticket key if status is 'created'

        Returns:
            True if update successful
        """
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()

        if status == 'approved':
            cursor.execute("""
                UPDATE pending_pm_requests
                SET status = ?, updated_at = ?, approved_at = ?
                WHERE request_id = ?
            """, (status, now, now, request_id))

        elif status == 'created' and jira_ticket_key:
            cursor.execute("""
                UPDATE pending_pm_requests
                SET status = ?, updated_at = ?, created_ticket_at = ?, jira_ticket_key = ?
                WHERE request_id = ?
            """, (status, now, now, jira_ticket_key, request_id))

        else:
            cursor.execute("""
                UPDATE pending_pm_requests
                SET status = ?, updated_at = ?
                WHERE request_id = ?
            """, (status, now, request_id))

        self.conn.commit()
        return cursor.rowcount > 0

    def add_revision(
        self,
        request_id: str,
        draft_content: str,
        feedback: Optional[str] = None
    ) -> int:
        """
        Add a new revision to a request

        Args:
            request_id: UUID of request
            draft_content: Updated draft content
            feedback: User feedback that prompted this revision

        Returns:
            revision_number: The revision number created
        """
        cursor = self.conn.cursor()

        # Get current max revision number
        cursor.execute("""
            SELECT MAX(revision_number) as max_rev
            FROM pm_request_revisions
            WHERE request_id = ?
        """, (request_id,))

        max_rev = cursor.fetchone()['max_rev'] or 0
        new_rev = max_rev + 1

        # Insert new revision
        cursor.execute("""
            INSERT INTO pm_request_revisions (
                request_id, revision_number, draft_content, feedback
            ) VALUES (?, ?, ?, ?)
        """, (request_id, new_rev, draft_content, feedback))

        # Update main request with new draft and status
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE pending_pm_requests
            SET draft_content = ?, status = 'pending', updated_at = ?
            WHERE request_id = ?
        """, (draft_content, now, request_id))

        self.conn.commit()
        return new_rev

    def get_revisions(self, request_id: str) -> List[Dict]:
        """Get all revisions for a request"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM pm_request_revisions
            WHERE request_id = ?
            ORDER BY revision_number ASC
        """, (request_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_user_pending_count(self, user_id: str) -> int:
        """Get count of pending requests for a user (for spam prevention)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pending_pm_requests
            WHERE user_id = ? AND status = 'pending'
        """, (user_id,))

        return cursor.fetchone()['count']

    def cleanup_old_requests(self, days: int = 30) -> int:
        """
        Archive old completed/cancelled requests

        Args:
            days: Archive requests older than this many days

        Returns:
            Number of requests archived
        """
        cursor = self.conn.cursor()

        # For now, just delete old completed/cancelled requests
        # In production, you might want to move to archive table instead
        cursor.execute("""
            DELETE FROM pending_pm_requests
            WHERE status IN ('created', 'cancelled')
            AND datetime(updated_at) < datetime('now', '-' || ? || ' days')
        """, (days,))

        self.conn.commit()
        return cursor.rowcount

    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'created' THEN 1 ELSE 0 END) as created,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN status = 'changes_requested' THEN 1 ELSE 0 END) as changes_requested
            FROM pending_pm_requests
        """)

        row = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as revision_count FROM pm_request_revisions")
        revision_row = cursor.fetchone()

        return {
            "total_requests": row['total'],
            "pending": row['pending'],
            "approved": row['approved'],
            "created": row['created'],
            "cancelled": row['cancelled'],
            "changes_requested": row['changes_requested'],
            "total_revisions": revision_row['revision_count']
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience function for getting singleton instance
_db_instance = None

def get_pm_requests_db() -> PMRequestsDB:
    """Get singleton PMRequestsDB instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = PMRequestsDB()
    return _db_instance


if __name__ == "__main__":
    # Test database creation
    print("Initializing PM Requests Database...")
    db = PMRequestsDB()

    print("\n✅ Database created successfully!")
    print(f"   Location: {db.db_path}")

    stats = db.get_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Pending: {stats['pending']}")
    print(f"   Created: {stats['created']}")
    print(f"   Total Revisions: {stats['total_revisions']}")

    db.close()
