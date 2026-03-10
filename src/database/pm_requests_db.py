"""
PM Requests Database - Approval Workflow Tracking

Manages pending product management requests (stories, bugs, epics)
awaiting user approval before Jira ticket creation.

Backed by SQLAlchemy so it works with both SQLite (local/tests) and
PostgreSQL (Heroku production).
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_engine
from src.database.schema import (
    metadata,
    pending_pm_requests,
    pm_request_revisions,
)


class PMRequestsDB:
    """Database manager for PM approval workflow."""

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
            self.engine = get_engine(default_path=str(db_path))
        else:
            self.engine = get_engine(
                default_path=".claude/data/pm-requests/pm_requests_state.db"
            )
        self._init_db()

    def _init_db(self):
        """Create tables if they don't already exist."""
        for table in (pending_pm_requests, pm_request_revisions):
            table.create(self.engine, checkfirst=True)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_request(
        self,
        source: str,
        source_id: str,
        request_type: str,
        user_id: str,
        user_name: str,
        original_context: str,
        draft_content: str,
    ) -> str:
        """
        Create a new PM request and store the initial draft as revision 1.

        Returns:
            request_id: UUID string of the created request.
        """
        request_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO pending_pm_requests (
                        request_id, source, source_id, request_type,
                        user_id, user_name, original_context, draft_content,
                        status, created_at, updated_at
                    ) VALUES (
                        :request_id, :source, :source_id, :request_type,
                        :user_id, :user_name, :original_context, :draft_content,
                        'pending', :now, :now
                    )
                """),
                {
                    "request_id": request_id,
                    "source": source,
                    "source_id": source_id,
                    "request_type": request_type,
                    "user_id": user_id,
                    "user_name": user_name,
                    "original_context": original_context,
                    "draft_content": draft_content,
                    "now": now,
                },
            )
            conn.execute(
                text("""
                    INSERT INTO pm_request_revisions (
                        request_id, revision_number, draft_content, feedback, created_at
                    ) VALUES (:request_id, 1, :draft_content, NULL, :now)
                """),
                {"request_id": request_id, "draft_content": draft_content, "now": now},
            )

        return request_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Return a request by its UUID, or None if not found."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM pending_pm_requests WHERE request_id = :id"),
                {"id": request_id},
            ).mappings().fetchone()
            return dict(row) if row else None

    def get_request_by_source(self, source: str, source_id: str) -> Optional[Dict]:
        """Return the most recent request for a given source location."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT * FROM pending_pm_requests
                    WHERE source = :source AND source_id = :source_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"source": source, "source_id": source_id},
            ).mappings().fetchone()
            return dict(row) if row else None

    def get_pending_requests(self, user_id: Optional[str] = None) -> List[Dict]:
        """Return all pending requests, optionally filtered by user."""
        with self.engine.connect() as conn:
            if user_id:
                rows = conn.execute(
                    text("""
                        SELECT * FROM pending_pm_requests
                        WHERE status = 'pending' AND user_id = :user_id
                        ORDER BY created_at DESC
                    """),
                    {"user_id": user_id},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text("""
                        SELECT * FROM pending_pm_requests
                        WHERE status = 'pending'
                        ORDER BY created_at DESC
                    """)
                ).mappings().all()
            return [dict(r) for r in rows]

    def get_user_pending_count(self, user_id: str) -> int:
        """Return count of pending requests for a user (spam prevention)."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM pending_pm_requests
                    WHERE user_id = :user_id AND status = 'pending'
                """),
                {"user_id": user_id},
            ).scalar()
            return result or 0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_request_status(
        self,
        request_id: str,
        status: str,
        jira_ticket_key: Optional[str] = None,
    ) -> bool:
        """
        Update request status.

        Args:
            status: 'pending' | 'approved' | 'changes_requested' | 'cancelled' | 'created'
            jira_ticket_key: Required when status is 'created'.

        Returns:
            True if the row was found and updated.
        """
        now = datetime.utcnow().isoformat()
        with self.engine.begin() as conn:
            if status == "approved":
                result = conn.execute(
                    text("""
                        UPDATE pending_pm_requests
                        SET status = :status, updated_at = :now, approved_at = :now
                        WHERE request_id = :id
                    """),
                    {"status": status, "now": now, "id": request_id},
                )
            elif status == "created" and jira_ticket_key:
                result = conn.execute(
                    text("""
                        UPDATE pending_pm_requests
                        SET status = :status, updated_at = :now,
                            created_ticket_at = :now, jira_ticket_key = :key
                        WHERE request_id = :id
                    """),
                    {
                        "status": status,
                        "now": now,
                        "key": jira_ticket_key,
                        "id": request_id,
                    },
                )
            else:
                result = conn.execute(
                    text("""
                        UPDATE pending_pm_requests
                        SET status = :status, updated_at = :now
                        WHERE request_id = :id
                    """),
                    {"status": status, "now": now, "id": request_id},
                )
            return result.rowcount > 0

    def add_revision(
        self,
        request_id: str,
        draft_content: str,
        feedback: Optional[str] = None,
    ) -> int:
        """
        Add a new revision and reset request status to 'pending'.

        Returns:
            The revision number created.
        """
        now = datetime.utcnow().isoformat()
        with self.engine.begin() as conn:
            max_rev = conn.execute(
                text("""
                    SELECT COALESCE(MAX(revision_number), 0)
                    FROM pm_request_revisions
                    WHERE request_id = :id
                """),
                {"id": request_id},
            ).scalar()
            new_rev = (max_rev or 0) + 1

            conn.execute(
                text("""
                    INSERT INTO pm_request_revisions
                        (request_id, revision_number, draft_content, feedback, created_at)
                    VALUES (:id, :rev, :content, :feedback, :now)
                """),
                {
                    "id": request_id,
                    "rev": new_rev,
                    "content": draft_content,
                    "feedback": feedback,
                    "now": now,
                },
            )
            conn.execute(
                text("""
                    UPDATE pending_pm_requests
                    SET draft_content = :content, status = 'pending', updated_at = :now
                    WHERE request_id = :id
                """),
                {"content": draft_content, "now": now, "id": request_id},
            )
        return new_rev

    # ------------------------------------------------------------------
    # Revisions
    # ------------------------------------------------------------------

    def get_revisions(self, request_id: str) -> List[Dict]:
        """Return all revisions for a request in ascending order."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT * FROM pm_request_revisions
                    WHERE request_id = :id
                    ORDER BY revision_number ASC
                """),
                {"id": request_id},
            ).mappings().all()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup_old_requests(self, days: int = 30) -> int:
        """Delete completed/cancelled requests older than `days` days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self.engine.begin() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM pending_pm_requests
                    WHERE status IN ('created', 'cancelled')
                    AND updated_at < :cutoff
                """),
                {"cutoff": cutoff},
            )
            return result.rowcount

    def get_stats(self) -> Dict:
        """Return database statistics."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        COALESCE(SUM(CASE WHEN status = 'pending'            THEN 1 ELSE 0 END), 0) as pending,
                        COALESCE(SUM(CASE WHEN status = 'approved'           THEN 1 ELSE 0 END), 0) as approved,
                        COALESCE(SUM(CASE WHEN status = 'created'            THEN 1 ELSE 0 END), 0) as created,
                        COALESCE(SUM(CASE WHEN status = 'cancelled'          THEN 1 ELSE 0 END), 0) as cancelled,
                        COALESCE(SUM(CASE WHEN status = 'changes_requested'  THEN 1 ELSE 0 END), 0) as changes_requested
                    FROM pending_pm_requests
                """)
            ).mappings().fetchone()

            revision_count = conn.execute(
                text("SELECT COUNT(*) FROM pm_request_revisions")
            ).scalar()

            return {
                "total_requests": row["total"],
                "pending": row["pending"],
                "approved": row["approved"],
                "created": row["created"],
                "cancelled": row["cancelled"],
                "changes_requested": row["changes_requested"],
                "total_revisions": revision_count,
            }

    # Legacy compat — close() is now a no-op since SQLAlchemy manages connections
    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Singleton instance (production use)
_db_instance = None


def get_pm_requests_db() -> PMRequestsDB:
    """Return the singleton PMRequestsDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = PMRequestsDB()
    return _db_instance
