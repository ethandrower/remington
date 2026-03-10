"""
Dashboard Database - Check execution history, active violations, and schedules.

Backed by SQLAlchemy so it works with both SQLite (local/tests) and
PostgreSQL (Heroku production). The engine is selected via get_engine():
  - DATABASE_URL env var → PostgreSQL
  - default_path fallback → SQLite
"""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_engine
from src.database.schema import (
    metadata,
    check_runs,
    active_violations,
    check_schedules,
    team_members,
    blocked_ticket_analyses,
    blocked_sent_alerts,
    timesheet_weeks,
    timesheet_entries,
    channel_config,
    system_config,
)


class DashboardDB:
    """Database for dashboard data — check runs, violations, and schedules."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        engine: Optional[Engine] = None,
    ):
        """
        Args:
            engine: SQLAlchemy engine (used in tests to pass an in-process DB).
            db_path: SQLite file path (used when no engine and no DATABASE_URL).
                     Defaults to .claude/data/bot-state/dashboard.db.
        """
        if engine is not None:
            self.engine = engine
        elif db_path is not None:
            self.engine = get_engine(default_path=str(db_path))
        else:
            self.engine = get_engine(
                default_path=".claude/data/bot-state/dashboard.db"
            )
        self._init_db()

    def _init_db(self):
        """Create tables if they don't already exist."""
        for table in (
            check_runs, active_violations, check_schedules, team_members,
            blocked_ticket_analyses, blocked_sent_alerts,
            timesheet_weeks, timesheet_entries,
            channel_config, system_config,
        ):
            table.create(self.engine, checkfirst=True)

    @contextmanager
    def _conn(self):
        """Transactional connection context manager."""
        with self.engine.begin() as conn:
            yield conn

    # ------------------------------------------------------------------
    # Check runs
    # ------------------------------------------------------------------

    def log_check_start(self, check_type: str, triggered_by: str = "scheduled") -> int:
        """Log the start of a check execution. Returns the new run ID."""
        with self._conn() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO check_runs (check_type, started_at, status, triggered_by)
                    VALUES (:check_type, :started_at, 'running', :triggered_by)
                    RETURNING id
                """),
                {
                    "check_type": check_type,
                    "started_at": datetime.now().isoformat(),
                    "triggered_by": triggered_by,
                },
            )
            return result.scalar()

    def log_check_complete(
        self,
        run_id: int,
        violations_found: int = 0,
        critical_count: int = 0,
        warning_count: int = 0,
        output_json: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ):
        """Log the completion of a check execution."""
        with self._conn() as conn:
            row = conn.execute(
                text("SELECT started_at FROM check_runs WHERE id = :id"),
                {"id": run_id},
            ).fetchone()

            completed_at = datetime.now()
            duration = 0
            if row:
                # Postgres returns datetime objects; SQLite returns strings
                raw = row[0]
                started_at = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))
                duration = int((completed_at - started_at).total_seconds())

            status = "success" if error_message is None else "failed"

            conn.execute(
                text("""
                    UPDATE check_runs
                    SET completed_at     = :completed_at,
                        duration_seconds = :duration,
                        status           = :status,
                        violations_found = :violations_found,
                        critical_count   = :critical_count,
                        warning_count    = :warning_count,
                        output_json      = :output_json,
                        error_message    = :error_message
                    WHERE id = :id
                """),
                {
                    "completed_at": completed_at.isoformat(),
                    "duration": duration,
                    "status": status,
                    "violations_found": violations_found,
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                    "output_json": json.dumps(output_json) if output_json else None,
                    "error_message": error_message,
                    "id": run_id,
                },
            )

    def update_schedule_last_run(self, check_type: str):
        """Update the last_run timestamp for a check schedule."""
        with self._conn() as conn:
            conn.execute(
                text("""
                    UPDATE check_schedules
                    SET last_run = :now
                    WHERE check_type = :check_type
                """),
                {"now": datetime.now().isoformat(), "check_type": check_type},
            )

    def mark_stale_runs_failed(self, stale_after_minutes: int = 15):
        """Mark any check that's been 'running' for too long as failed."""
        cutoff = (datetime.now() - timedelta(minutes=stale_after_minutes)).isoformat()
        with self._conn() as conn:
            conn.execute(
                text("""
                    UPDATE check_runs
                    SET status = 'failed',
                        error_message = 'Check did not complete — process may have crashed or restarted',
                        completed_at = :now
                    WHERE status = 'running' AND started_at < :cutoff
                """),
                {"now": datetime.now().isoformat(), "cutoff": cutoff},
            )

    def get_check_history(
        self, check_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """Return check execution history, most recent first."""
        with self.engine.connect() as conn:
            if check_type:
                rows = conn.execute(
                    text("""
                        SELECT * FROM check_runs
                        WHERE check_type = :check_type
                        ORDER BY started_at DESC
                        LIMIT :limit
                    """),
                    {"check_type": check_type, "limit": limit},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text("""
                        SELECT * FROM check_runs
                        ORDER BY started_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit},
                ).mappings().all()
            return [dict(r) for r in rows]

    def get_latest_check(self, check_type: str) -> Optional[Dict]:
        """Return the most recent check run for a given type."""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT * FROM check_runs
                    WHERE check_type = :check_type
                    ORDER BY started_at DESC
                    LIMIT 1
                """),
                {"check_type": check_type},
            ).mappings().fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Violations
    # ------------------------------------------------------------------

    def upsert_violation(self, violation: Dict):
        """Insert or update an active violation."""
        with self._conn() as conn:
            conn.execute(
                text("""
                    INSERT INTO active_violations (
                        item_id, violation_type, severity, detected_at,
                        hours_overdue, owner, title, link, slack_thread_ts,
                        escalation_level, last_updated, metadata
                    ) VALUES (
                        :item_id, :violation_type, :severity, :detected_at,
                        :hours_overdue, :owner, :title, :link, :slack_thread_ts,
                        :escalation_level, :last_updated, :metadata
                    )
                    ON CONFLICT (item_id) DO UPDATE SET
                        severity          = excluded.severity,
                        hours_overdue     = excluded.hours_overdue,
                        slack_thread_ts   = excluded.slack_thread_ts,
                        escalation_level  = excluded.escalation_level,
                        last_updated      = excluded.last_updated
                """),
                {
                    "item_id": violation.get("item_id"),
                    "violation_type": violation.get("type"),
                    "severity": violation.get("severity", "warning"),
                    "detected_at": violation.get("detected_at", datetime.now().isoformat()),
                    "hours_overdue": violation.get("hours_overdue", 0),
                    "owner": violation.get("owner"),
                    "title": violation.get("title"),
                    "link": violation.get("link"),
                    "slack_thread_ts": violation.get("slack_thread_ts"),
                    "escalation_level": violation.get("escalation_level", 1),
                    "last_updated": datetime.now().isoformat(),
                    "metadata": json.dumps(violation.get("metadata", {})),
                },
            )

    def resolve_violation(self, item_id: str):
        """Mark a violation as resolved."""
        with self._conn() as conn:
            conn.execute(
                text("""
                    UPDATE active_violations
                    SET resolved_at = :resolved_at
                    WHERE item_id = :item_id AND resolved_at IS NULL
                """),
                {"resolved_at": datetime.now().isoformat(), "item_id": item_id},
            )

    def get_active_violations(
        self, violation_type: Optional[str] = None
    ) -> List[Dict]:
        """Return all unresolved violations."""
        with self.engine.connect() as conn:
            if violation_type:
                rows = conn.execute(
                    text("""
                        SELECT * FROM active_violations
                        WHERE resolved_at IS NULL AND violation_type = :violation_type
                        ORDER BY hours_overdue DESC
                    """),
                    {"violation_type": violation_type},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text("""
                        SELECT * FROM active_violations
                        WHERE resolved_at IS NULL
                        ORDER BY severity DESC, hours_overdue DESC
                    """)
                ).mappings().all()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Return dashboard statistics."""
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        with self.engine.connect() as conn:
            violation_stats = conn.execute(
                text("""
                    SELECT
                        violation_type,
                        COUNT(*) as count,
                        COALESCE(SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END), 0) as critical,
                        COALESCE(SUM(CASE WHEN severity = 'warning'  THEN 1 ELSE 0 END), 0) as warning
                    FROM active_violations
                    WHERE resolved_at IS NULL
                    GROUP BY violation_type
                """)
            ).mappings().all()

            recent_checks = conn.execute(
                text("""
                    SELECT check_type, COUNT(*) as runs, AVG(duration_seconds) as avg_duration
                    FROM check_runs
                    WHERE started_at > :week_ago
                    GROUP BY check_type
                """),
                {"week_ago": week_ago},
            ).mappings().all()

            violation_list = [dict(r) for r in violation_stats]
            return {
                "violations_by_type": violation_list,
                "recent_checks": [dict(r) for r in recent_checks],
                "total_active_violations": sum(r["count"] for r in violation_list),
                "total_critical": sum(r["critical"] for r in violation_list),
                "total_warning": sum(r["warning"] for r in violation_list),
            }

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------

    def upsert_schedule(
        self, check_type: str, schedule_expr: str, description: str = ""
    ):
        """Insert or update a check schedule."""
        with self._conn() as conn:
            conn.execute(
                text("""
                    INSERT INTO check_schedules (check_type, schedule_expression, description, enabled)
                    VALUES (:check_type, :schedule_expr, :description, TRUE)
                    ON CONFLICT (check_type) DO UPDATE SET
                        schedule_expression = excluded.schedule_expression,
                        description         = excluded.description
                """),
                {
                    "check_type": check_type,
                    "schedule_expr": schedule_expr,
                    "description": description,
                },
            )

    def get_schedules(self) -> List[Dict]:
        """Return all check schedules ordered by type."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM check_schedules ORDER BY check_type")
            ).mappings().all()
            return [dict(r) for r in rows]


    # ------------------------------------------------------------------
    # Team members
    # ------------------------------------------------------------------

    def get_team_members(self, active_only: bool = False) -> List[Dict]:
        """Return all team members ordered by display name."""
        with self.engine.connect() as conn:
            if active_only:
                rows = conn.execute(
                    text("""
                        SELECT * FROM team_members
                        WHERE is_active = TRUE
                        ORDER BY display_name
                    """)
                ).mappings().all()
            else:
                rows = conn.execute(
                    text("SELECT * FROM team_members ORDER BY display_name")
                ).mappings().all()
            return [dict(r) for r in rows]

    def create_team_member(self, member: Dict) -> int:
        """Insert a new team member. Returns the new row id."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO team_members
                        (display_name, jira_account_id, jira_display_name,
                         slack_user_id, slack_display_name, email,
                         role, weekly_capacity_hours, is_active, notes, created_at, updated_at)
                    VALUES
                        (:display_name, :jira_account_id, :jira_display_name,
                         :slack_user_id, :slack_display_name, :email,
                         :role, :weekly_capacity_hours, :is_active, :notes, :created_at, :updated_at)
                    RETURNING id
                """),
                {
                    "display_name": member.get("display_name", ""),
                    "jira_account_id": member.get("jira_account_id"),
                    "jira_display_name": member.get("jira_display_name"),
                    "slack_user_id": member.get("slack_user_id"),
                    "slack_display_name": member.get("slack_display_name"),
                    "email": member.get("email"),
                    "role": member.get("role"),
                    "weekly_capacity_hours": member.get("weekly_capacity_hours", 40.0),
                    "is_active": member.get("is_active", True),
                    "notes": member.get("notes"),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            return result.scalar()

    def update_team_member(self, member_id: int, member: Dict):
        """Update an existing team member by id."""
        with self._conn() as conn:
            conn.execute(
                text("""
                    UPDATE team_members SET
                        display_name          = :display_name,
                        jira_account_id       = :jira_account_id,
                        jira_display_name     = :jira_display_name,
                        slack_user_id         = :slack_user_id,
                        slack_display_name    = :slack_display_name,
                        email                 = :email,
                        role                  = :role,
                        weekly_capacity_hours = :weekly_capacity_hours,
                        is_active             = :is_active,
                        notes                 = :notes,
                        updated_at            = :updated_at
                    WHERE id = :id
                """),
                {
                    "id": member_id,
                    "display_name": member.get("display_name", ""),
                    "jira_account_id": member.get("jira_account_id"),
                    "jira_display_name": member.get("jira_display_name"),
                    "slack_user_id": member.get("slack_user_id"),
                    "slack_display_name": member.get("slack_display_name"),
                    "email": member.get("email"),
                    "role": member.get("role"),
                    "weekly_capacity_hours": member.get("weekly_capacity_hours", 40.0),
                    "is_active": member.get("is_active", True),
                    "notes": member.get("notes"),
                    "updated_at": datetime.now().isoformat(),
                },
            )

    def delete_team_member(self, member_id: int):
        """Delete a team member by id."""
        with self._conn() as conn:
            conn.execute(
                text("DELETE FROM team_members WHERE id = :id"),
                {"id": member_id},
            )


# Singleton instance (production use)
_db_instance = None


def get_dashboard_db() -> DashboardDB:
    """Return the singleton DashboardDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DashboardDB()
    return _db_instance
