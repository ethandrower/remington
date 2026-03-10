"""
Unit tests for src/activity_tracker.py

Uses a per-test SQLAlchemy engine backed by SQLite — no real files written.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect as sa_inspect, text

from src.activity_tracker import ActivityTracker


@pytest.fixture
def engine(tmp_path):
    return create_engine(
        f"sqlite:///{tmp_path}/test_activity.db",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def tracker(engine) -> ActivityTracker:
    return ActivityTracker(engine=engine)


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    def test_table_is_created(self, tracker, engine):
        inspector = sa_inspect(engine)
        assert "activities" in inspector.get_table_names()

    def test_indexes_are_created(self, tracker, engine):
        inspector = sa_inspect(engine)
        indexes = {i["name"] for i in inspector.get_indexes("activities")}
        assert "idx_activity_timestamp" in indexes
        assert "idx_activity_type" in indexes


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------

class TestLog:
    def test_log_inserts_activity(self, tracker):
        tracker.log("polling_slack", details="Checked 5 messages", item_id="C01AB")
        recent = tracker.get_recent_activities(limit=1)
        assert len(recent) == 1
        assert recent[0]["type"] == "polling_slack"
        assert recent[0]["details"] == "Checked 5 messages"
        assert recent[0]["item_id"] == "C01AB"

    def test_log_success_defaults_to_true(self, tracker):
        tracker.log("heartbeat")
        assert tracker.get_recent_activities(limit=1)[0]["success"] is True

    def test_log_failure_stores_false(self, tracker):
        tracker.log("jira_comment_posted", success=False)
        assert tracker.get_recent_activities(limit=1)[0]["success"] is False

    def test_log_without_optional_fields(self, tracker):
        tracker.log("heartbeat")
        recent = tracker.get_recent_activities(limit=1)[0]
        assert recent["details"] is None
        assert recent["item_id"] is None

    def test_multiple_activities_are_stored(self, tracker):
        for t in ["polling_slack", "polling_jira", "sla_check"]:
            tracker.log(t)
        assert len(tracker.get_recent_activities(limit=10)) == 3


# ---------------------------------------------------------------------------
# get_recent_summary
# ---------------------------------------------------------------------------

class TestGetRecentSummary:
    def test_counts_by_type(self, tracker):
        tracker.log("polling_slack")
        tracker.log("polling_slack")
        tracker.log("polling_jira")
        summary = tracker.get_recent_summary(hours=1)
        assert summary.get("polling_slack") == 2
        assert summary.get("polling_jira") == 1

    def test_empty_summary_when_no_activities(self, tracker):
        assert tracker.get_recent_summary(hours=1) == {}

    def test_excludes_old_activities(self, tracker, engine):
        tracker.log("old_event")
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE activities SET timestamp = :ts WHERE activity_type = 'old_event'"),
                {"ts": (datetime.now() - timedelta(hours=2)).isoformat()},
            )
        assert "old_event" not in tracker.get_recent_summary(hours=1)


# ---------------------------------------------------------------------------
# get_last_activity
# ---------------------------------------------------------------------------

class TestGetLastActivity:
    def test_returns_none_when_no_matching_activity(self, tracker):
        assert tracker.get_last_activity("nonexistent_type") is None

    def test_returns_datetime(self, tracker):
        tracker.log("sla_check")
        assert isinstance(tracker.get_last_activity("sla_check"), datetime)

    def test_returns_most_recent_when_multiple(self, tracker, engine):
        tracker.log("sla_check")
        tracker.log("sla_check")
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE activities SET timestamp = :ts WHERE id = 1"),
                {"ts": (datetime.now() - timedelta(hours=1)).isoformat()},
            )
        result = tracker.get_last_activity("sla_check")
        assert (datetime.now() - result).total_seconds() < 60


# ---------------------------------------------------------------------------
# get_last_activity_details
# ---------------------------------------------------------------------------

class TestGetLastActivityDetails:
    def test_returns_none_when_no_matching_activity(self, tracker):
        assert tracker.get_last_activity_details("nonexistent_type") is None

    def test_returns_full_details(self, tracker):
        tracker.log("standup_report", details="Posted standup", item_id="standup-2026-02-21")
        result = tracker.get_last_activity_details("standup_report")
        assert result["details"] == "Posted standup"
        assert result["item_id"] == "standup-2026-02-21"
        assert result["success"] is True
        assert "timestamp" in result

    def test_returns_most_recent_entry(self, tracker):
        tracker.log("sla_check", details="Run 1")
        tracker.log("sla_check", details="Run 2")
        assert tracker.get_last_activity_details("sla_check")["details"] == "Run 2"


# ---------------------------------------------------------------------------
# get_recent_activities
# ---------------------------------------------------------------------------

class TestGetRecentActivities:
    def test_returns_most_recent_first(self, tracker):
        for i in range(5):
            tracker.log("polling_slack", details=f"Run {i}")
        recent = tracker.get_recent_activities(limit=5)
        assert recent[0]["details"] == "Run 4"

    def test_limit_is_respected(self, tracker):
        for _ in range(10):
            tracker.log("heartbeat")
        assert len(tracker.get_recent_activities(limit=3)) == 3

    def test_returns_empty_list_when_no_activities(self, tracker):
        assert tracker.get_recent_activities() == []
