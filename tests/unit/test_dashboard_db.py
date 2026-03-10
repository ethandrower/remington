"""
Unit tests for src/database/dashboard_db.py

Uses an in-process SQLite engine (via SQLAlchemy) per test — no files written
to the real project database, no raw sqlite3 calls.
"""

import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect as sa_inspect, text

from src.database.dashboard_db import DashboardDB


@pytest.fixture
def engine(tmp_path):
    """Fresh SQLite engine per test."""
    return create_engine(
        f"sqlite:///{tmp_path}/test_dashboard.db",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def db(engine) -> DashboardDB:
    """DashboardDB backed by the per-test engine."""
    return DashboardDB(engine=engine)


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    def test_tables_are_created(self, db, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"active_violations", "check_runs", "check_schedules"}.issubset(tables)

    def test_indexes_are_created(self, db, engine):
        inspector = sa_inspect(engine)
        cr_indexes = {i["name"] for i in inspector.get_indexes("check_runs")}
        av_indexes = {i["name"] for i in inspector.get_indexes("active_violations")}
        assert "idx_check_runs_type" in cr_indexes
        assert "idx_check_runs_started" in cr_indexes
        assert "idx_violations_type" in av_indexes
        assert "idx_violations_resolved" in av_indexes


# ---------------------------------------------------------------------------
# Check runs
# ---------------------------------------------------------------------------

class TestCheckRuns:
    def test_log_check_start_returns_id(self, db):
        run_id = db.log_check_start("sla_check")
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_log_check_start_sets_running_status(self, db):
        db.log_check_start("sla_check", triggered_by="manual")
        history = db.get_check_history("sla_check")
        assert len(history) == 1
        assert history[0]["status"] == "running"
        assert history[0]["check_type"] == "sla_check"
        assert history[0]["triggered_by"] == "manual"

    def test_log_check_complete_success(self, db):
        run_id = db.log_check_start("sla_check")
        db.log_check_complete(
            run_id,
            violations_found=3,
            critical_count=1,
            warning_count=2,
            output_json={"items": [1, 2, 3]},
        )
        latest = db.get_latest_check("sla_check")
        assert latest["status"] == "success"
        assert latest["violations_found"] == 3
        assert latest["critical_count"] == 1
        assert latest["warning_count"] == 2
        assert json.loads(latest["output_json"]) == {"items": [1, 2, 3]}
        assert latest["error_message"] is None

    def test_log_check_complete_failure(self, db):
        run_id = db.log_check_start("sla_check")
        db.log_check_complete(run_id, error_message="Jira API timed out")
        latest = db.get_latest_check("sla_check")
        assert latest["status"] == "failed"
        assert latest["error_message"] == "Jira API timed out"

    def test_log_check_complete_calculates_duration(self, db):
        run_id = db.log_check_start("sla_check")
        db.log_check_complete(run_id)
        latest = db.get_latest_check("sla_check")
        assert latest["duration_seconds"] is not None
        assert latest["duration_seconds"] >= 0

    def test_get_check_history_returns_most_recent_first(self, db):
        for i in range(3):
            run_id = db.log_check_start("sla_check")
            db.log_check_complete(run_id, violations_found=i)
        history = db.get_check_history("sla_check")
        assert len(history) == 3
        assert history[0]["violations_found"] >= history[-1]["violations_found"]

    def test_get_check_history_filtered_by_type(self, db):
        run_id_a = db.log_check_start("sla_check")
        db.log_check_complete(run_id_a)
        run_id_b = db.log_check_start("blocked_tickets")
        db.log_check_complete(run_id_b)
        sla_history = db.get_check_history("sla_check")
        assert all(r["check_type"] == "sla_check" for r in sla_history)
        assert len(sla_history) == 1

    def test_get_check_history_limit(self, db):
        for _ in range(10):
            run_id = db.log_check_start("sla_check")
            db.log_check_complete(run_id)
        history = db.get_check_history(limit=3)
        assert len(history) == 3

    def test_get_latest_check_returns_none_when_empty(self, db):
        assert db.get_latest_check("nonexistent_type") is None

    def test_get_latest_check_returns_most_recent(self, db):
        run_id1 = db.log_check_start("sla_check")
        db.log_check_complete(run_id1, violations_found=5)
        run_id2 = db.log_check_start("sla_check")
        db.log_check_complete(run_id2, violations_found=10)
        latest = db.get_latest_check("sla_check")
        assert latest["violations_found"] == 10


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------

class TestViolations:
    def _make_violation(self, item_id="ECD-123", **kwargs):
        base = {
            "item_id": item_id,
            "type": "qa_stale",
            "severity": "warning",
            "detected_at": datetime.now().isoformat(),
            "hours_overdue": 5.5,
            "owner": "dev@example.com",
            "title": "Fix login bug",
            "link": "https://example.atlassian.net/browse/ECD-123",
            "slack_thread_ts": None,
            "escalation_level": 1,
            "metadata": {},
        }
        base.update(kwargs)
        return base

    def test_upsert_violation_inserts_new(self, db):
        db.upsert_violation(self._make_violation())
        violations = db.get_active_violations()
        assert len(violations) == 1
        assert violations[0]["item_id"] == "ECD-123"

    def test_upsert_violation_updates_on_conflict(self, db):
        db.upsert_violation(self._make_violation(hours_overdue=5.0, escalation_level=1))
        db.upsert_violation(self._make_violation(hours_overdue=10.0, escalation_level=2))
        violations = db.get_active_violations()
        assert len(violations) == 1
        assert violations[0]["hours_overdue"] == 10.0
        assert violations[0]["escalation_level"] == 2

    def test_get_active_violations_excludes_resolved(self, db):
        db.upsert_violation(self._make_violation("ECD-100"))
        db.upsert_violation(self._make_violation("ECD-101"))
        db.resolve_violation("ECD-100")
        active = db.get_active_violations()
        assert len(active) == 1
        assert active[0]["item_id"] == "ECD-101"

    def test_get_active_violations_filtered_by_type(self, db):
        db.upsert_violation(self._make_violation("ECD-100", **{"type": "qa_stale"}))
        db.upsert_violation(self._make_violation("ECD-101", **{"type": "blocked"}))
        qa_violations = db.get_active_violations(violation_type="qa_stale")
        assert len(qa_violations) == 1
        assert qa_violations[0]["violation_type"] == "qa_stale"

    def test_resolve_violation_is_idempotent(self, db):
        db.upsert_violation(self._make_violation())
        db.resolve_violation("ECD-123")
        db.resolve_violation("ECD-123")
        assert db.get_active_violations() == []

    def test_resolve_nonexistent_violation_does_not_raise(self, db):
        db.resolve_violation("NONEXISTENT-999")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_get_stats_empty_db(self, db):
        stats = db.get_stats()
        assert stats["total_active_violations"] == 0
        assert stats["total_critical"] == 0
        assert stats["total_warning"] == 0

    def test_get_stats_counts_correctly(self, db):
        violations = [
            {"item_id": "A", "type": "qa_stale", "severity": "critical"},
            {"item_id": "B", "type": "qa_stale", "severity": "warning"},
            {"item_id": "C", "type": "blocked", "severity": "critical"},
        ]
        for v in violations:
            db.upsert_violation({
                "item_id": v["item_id"],
                "type": v["type"],
                "severity": v["severity"],
                "detected_at": datetime.now().isoformat(),
                "hours_overdue": 1.0,
                "metadata": {},
            })
        stats = db.get_stats()
        assert stats["total_active_violations"] == 3
        assert stats["total_critical"] == 2
        assert stats["total_warning"] == 1

    def test_get_stats_excludes_resolved(self, db):
        db.upsert_violation({
            "item_id": "ECD-1",
            "type": "qa_stale",
            "severity": "critical",
            "detected_at": datetime.now().isoformat(),
            "hours_overdue": 1.0,
            "metadata": {},
        })
        db.resolve_violation("ECD-1")
        stats = db.get_stats()
        assert stats["total_active_violations"] == 0


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

class TestSchedules:
    def test_upsert_schedule_creates(self, db):
        db.upsert_schedule("sla_check", "0 9 * * 1-5", "Daily SLA check")
        schedules = db.get_schedules()
        assert len(schedules) == 1
        assert schedules[0]["check_type"] == "sla_check"
        assert schedules[0]["schedule_expression"] == "0 9 * * 1-5"

    def test_upsert_schedule_updates_on_conflict(self, db):
        db.upsert_schedule("sla_check", "0 9 * * 1-5", "Old description")
        db.upsert_schedule("sla_check", "0 10 * * 1-5", "New description")
        schedules = db.get_schedules()
        assert len(schedules) == 1
        assert schedules[0]["schedule_expression"] == "0 10 * * 1-5"

    def test_get_schedules_empty(self, db):
        assert db.get_schedules() == []

    def test_get_schedules_multiple(self, db):
        db.upsert_schedule("sla_check", "0 9 * * 1-5")
        db.upsert_schedule("blocked_tickets", "0 10 * * 1-5")
        schedules = db.get_schedules()
        assert len(schedules) == 2


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------

class TestTeamMembers:
    def _make_member(self, **kwargs):
        base = {
            "display_name": "Jane Smith",
            "jira_account_id": "abc123",
            "jira_display_name": "Jane Smith (Jira)",
            "slack_user_id": "U01ABC",
            "slack_display_name": "janesmith",
            "email": "jane@example.com",
            "is_active": True,
            "notes": None,
        }
        base.update(kwargs)
        return base

    def test_create_returns_id(self, db):
        member_id = db.create_team_member(self._make_member())
        assert isinstance(member_id, int)
        assert member_id > 0

    def test_get_team_members_returns_created(self, db):
        db.create_team_member(self._make_member())
        members = db.get_team_members()
        assert len(members) == 1
        assert members[0]["display_name"] == "Jane Smith"
        assert members[0]["jira_account_id"] == "abc123"
        assert members[0]["slack_user_id"] == "U01ABC"

    def test_get_team_members_empty(self, db):
        assert db.get_team_members() == []

    def test_get_team_members_ordered_by_name(self, db):
        db.create_team_member(self._make_member(display_name="Zara", jira_account_id="z1", slack_user_id="UZ"))
        db.create_team_member(self._make_member(display_name="Alice", jira_account_id="a1", slack_user_id="UA"))
        members = db.get_team_members()
        assert members[0]["display_name"] == "Alice"
        assert members[1]["display_name"] == "Zara"

    def test_update_team_member(self, db):
        member_id = db.create_team_member(self._make_member())
        db.update_team_member(member_id, {
            **self._make_member(),
            "email": "new@example.com",
            "notes": "Updated",
        })
        members = db.get_team_members()
        assert members[0]["email"] == "new@example.com"
        assert members[0]["notes"] == "Updated"

    def test_update_team_member_active_flag(self, db):
        member_id = db.create_team_member(self._make_member(is_active=True))
        db.update_team_member(member_id, self._make_member(is_active=False))
        members = db.get_team_members()
        assert members[0]["is_active"] == False

    def test_delete_team_member(self, db):
        member_id = db.create_team_member(self._make_member())
        db.delete_team_member(member_id)
        assert db.get_team_members() == []

    def test_delete_nonexistent_does_not_raise(self, db):
        db.delete_team_member(9999)

    def test_multiple_members(self, db):
        db.create_team_member(self._make_member(
            display_name="Alice", jira_account_id="a1", slack_user_id="UA"
        ))
        db.create_team_member(self._make_member(
            display_name="Bob", jira_account_id="b1", slack_user_id="UB"
        ))
        members = db.get_team_members()
        assert len(members) == 2

    def test_team_member_schema_created(self, db, engine):
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        assert "team_members" in inspector.get_table_names()
        cols = {c["name"] for c in inspector.get_columns("team_members")}
        assert {"id", "display_name", "jira_account_id", "slack_user_id", "email"}.issubset(cols)
