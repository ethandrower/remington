"""
Unit tests for src/database/pm_requests_db.py

Uses a per-test SQLAlchemy engine backed by SQLite — no real files written.
"""

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text

from src.database.pm_requests_db import PMRequestsDB


@pytest.fixture
def engine(tmp_path):
    return create_engine(
        f"sqlite:///{tmp_path}/test_pm_requests.db",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def db(engine) -> PMRequestsDB:
    instance = PMRequestsDB(engine=engine)
    yield instance
    instance.close()


def _make_request_kwargs(**overrides):
    defaults = dict(
        source="slack",
        source_id="1704470400.123456",
        request_type="story",
        user_id="U01AB2CD3EF",
        user_name="Jane Smith",
        original_context="Can we add a dark mode?",
        draft_content="## Story\nAs a user I want dark mode...",
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    def test_tables_are_created(self, db, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"pending_pm_requests", "pm_request_revisions"}.issubset(tables)

    def test_indexes_are_created(self, db, engine):
        inspector = sa_inspect(engine)
        req_indexes = {i["name"] for i in inspector.get_indexes("pending_pm_requests")}
        rev_indexes = {i["name"] for i in inspector.get_indexes("pm_request_revisions")}
        assert "idx_pm_request_id" in req_indexes
        assert "idx_pm_status" in req_indexes
        assert "idx_pm_revision_request" in rev_indexes


# ---------------------------------------------------------------------------
# create_request
# ---------------------------------------------------------------------------

class TestCreateRequest:
    def test_returns_uuid_string(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        assert isinstance(request_id, str) and len(request_id) == 36

    def test_creates_request_in_pending_status(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        request = db.get_request(request_id)
        assert request is not None
        assert request["status"] == "pending"
        assert request["request_id"] == request_id

    def test_stores_all_fields(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        req = db.get_request(request_id)
        assert req["source"] == "slack"
        assert req["source_id"] == "1704470400.123456"
        assert req["request_type"] == "story"
        assert req["user_id"] == "U01AB2CD3EF"
        assert req["user_name"] == "Jane Smith"
        assert req["original_context"] == "Can we add a dark mode?"
        assert req["draft_content"] == "## Story\nAs a user I want dark mode..."

    def test_creates_initial_revision(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        revisions = db.get_revisions(request_id)
        assert len(revisions) == 1
        assert revisions[0]["revision_number"] == 1
        assert revisions[0]["draft_content"] == "## Story\nAs a user I want dark mode..."

    def test_multiple_requests_are_independent(self, db):
        id1 = db.create_request(**_make_request_kwargs(user_name="Alice"))
        id2 = db.create_request(**_make_request_kwargs(user_name="Bob", source_id="other"))
        assert id1 != id2
        assert db.get_request(id1)["user_name"] == "Alice"
        assert db.get_request(id2)["user_name"] == "Bob"


# ---------------------------------------------------------------------------
# get_request / get_request_by_source
# ---------------------------------------------------------------------------

class TestGetRequest:
    def test_get_request_returns_none_for_unknown_id(self, db):
        assert db.get_request("nonexistent-uuid") is None

    def test_get_request_by_source_returns_most_recent(self, db, engine):
        id1 = db.create_request(**_make_request_kwargs(draft_content="Draft 1"))
        # Age the first record so ordering is unambiguous
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE pending_pm_requests SET created_at = '2020-01-01 00:00:00' WHERE request_id = :id"),
                {"id": id1},
            )
        db.create_request(**_make_request_kwargs(draft_content="Draft 2"))
        result = db.get_request_by_source("slack", "1704470400.123456")
        assert result["draft_content"] == "Draft 2"

    def test_get_request_by_source_returns_none_when_missing(self, db):
        assert db.get_request_by_source("jira", "PROJ-999") is None


# ---------------------------------------------------------------------------
# get_pending_requests
# ---------------------------------------------------------------------------

class TestGetPendingRequests:
    def test_returns_only_pending(self, db):
        id1 = db.create_request(**_make_request_kwargs(source_id="ts1"))
        id2 = db.create_request(**_make_request_kwargs(source_id="ts2"))
        db.update_request_status(id1, "cancelled")
        pending = db.get_pending_requests()
        assert len(pending) == 1
        assert pending[0]["request_id"] == id2

    def test_filtered_by_user_id(self, db):
        db.create_request(**_make_request_kwargs(user_id="USER_A", source_id="ts1"))
        db.create_request(**_make_request_kwargs(user_id="USER_B", source_id="ts2"))
        result = db.get_pending_requests(user_id="USER_A")
        assert len(result) == 1
        assert result[0]["user_id"] == "USER_A"

    def test_empty_when_no_pending(self, db):
        assert db.get_pending_requests() == []


# ---------------------------------------------------------------------------
# update_request_status
# ---------------------------------------------------------------------------

class TestUpdateRequestStatus:
    def test_approve_sets_approved_at(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.update_request_status(request_id, "approved")
        req = db.get_request(request_id)
        assert req["status"] == "approved"
        assert req["approved_at"] is not None

    def test_created_sets_jira_key_and_timestamp(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.update_request_status(request_id, "created", jira_ticket_key="ECD-999")
        req = db.get_request(request_id)
        assert req["status"] == "created"
        assert req["jira_ticket_key"] == "ECD-999"
        assert req["created_ticket_at"] is not None

    def test_cancel_updates_status(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        success = db.update_request_status(request_id, "cancelled")
        assert success is True
        assert db.get_request(request_id)["status"] == "cancelled"

    def test_update_nonexistent_returns_false(self, db):
        assert db.update_request_status("nonexistent-uuid", "cancelled") is False


# ---------------------------------------------------------------------------
# add_revision / get_revisions
# ---------------------------------------------------------------------------

class TestRevisions:
    def test_add_revision_increments_number(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        rev2 = db.add_revision(request_id, "v2", feedback="Make it shorter")
        rev3 = db.add_revision(request_id, "v3", feedback="Looks good")
        assert rev2 == 2
        assert rev3 == 3

    def test_add_revision_updates_draft_content(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.add_revision(request_id, "New draft content")
        assert db.get_request(request_id)["draft_content"] == "New draft content"

    def test_add_revision_resets_status_to_pending(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.update_request_status(request_id, "changes_requested")
        db.add_revision(request_id, "Revised draft")
        assert db.get_request(request_id)["status"] == "pending"

    def test_get_revisions_ordered_ascending(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.add_revision(request_id, "v2")
        db.add_revision(request_id, "v3")
        numbers = [r["revision_number"] for r in db.get_revisions(request_id)]
        assert numbers == sorted(numbers)

    def test_get_revisions_stores_feedback(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        db.add_revision(request_id, "v2", feedback="Add acceptance criteria")
        revisions = db.get_revisions(request_id)
        assert revisions[1]["feedback"] == "Add acceptance criteria"


# ---------------------------------------------------------------------------
# get_user_pending_count
# ---------------------------------------------------------------------------

class TestUserPendingCount:
    def test_counts_only_pending_for_user(self, db):
        db.create_request(**_make_request_kwargs(user_id="U_ALICE", source_id="ts1"))
        db.create_request(**_make_request_kwargs(user_id="U_ALICE", source_id="ts2"))
        id3 = db.create_request(**_make_request_kwargs(user_id="U_ALICE", source_id="ts3"))
        db.update_request_status(id3, "cancelled")
        assert db.get_user_pending_count("U_ALICE") == 2

    def test_returns_zero_for_unknown_user(self, db):
        assert db.get_user_pending_count("UNKNOWN_USER") == 0


# ---------------------------------------------------------------------------
# cleanup_old_requests
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_removes_old_completed(self, db, engine):
        request_id = db.create_request(**_make_request_kwargs())
        db.update_request_status(request_id, "created", jira_ticket_key="ECD-1")
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE pending_pm_requests SET updated_at = '2020-01-01T00:00:00' WHERE request_id = :id"),
                {"id": request_id},
            )
        removed = db.cleanup_old_requests(days=30)
        assert removed == 1

    def test_cleanup_preserves_pending_requests(self, db):
        request_id = db.create_request(**_make_request_kwargs())
        removed = db.cleanup_old_requests(days=0)
        assert removed == 0
        assert db.get_request(request_id) is not None


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_empty_db_stats(self, db):
        stats = db.get_stats()
        assert stats["total_requests"] == 0
        assert stats["pending"] == 0
        assert stats["total_revisions"] == 0

    def test_stats_counts_by_status(self, db):
        id1 = db.create_request(**_make_request_kwargs(source_id="ts1"))
        id2 = db.create_request(**_make_request_kwargs(source_id="ts2"))
        id3 = db.create_request(**_make_request_kwargs(source_id="ts3"))
        db.update_request_status(id2, "approved")
        db.update_request_status(id3, "created", jira_ticket_key="ECD-1")
        stats = db.get_stats()
        assert stats["total_requests"] == 3
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["created"] == 1
        assert stats["total_revisions"] == 3
