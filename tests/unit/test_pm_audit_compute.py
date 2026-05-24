"""Unit tests for PM self-audit compute layer."""
import pytest
from datetime import datetime, timedelta

from src.dashboard.pm_audit_compute import (
    compute_pm_audit,
    _compute_approval_velocity,
    _compute_comment_activity,
    _compute_grooming,
    _compute_transitions,
    _compute_scope_management,
    _compute_blocker_response,
    _compute_grades,
    _business_hours_between,
    _pm_matches,
)

PM_ID = "pm-account-123"
PM_NAMES = ["Jane PM", "Jane"]


def _ts(days_ago=0, hour=12):
    """Generate ISO timestamp for N days ago (Jira-style)."""
    dt = datetime.utcnow() - timedelta(days=days_ago)
    dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


# ── Helper tests ──────────────────────────────────────────────────────────────

class TestHelpers:
    def test_pm_matches_by_id(self):
        assert _pm_matches(PM_ID, None, PM_ID, PM_NAMES)

    def test_pm_matches_by_name(self):
        assert _pm_matches("other-id", "Jane PM", PM_ID, PM_NAMES)

    def test_pm_no_match(self):
        assert not _pm_matches("other-id", "Bob Dev", PM_ID, PM_NAMES)

    def test_business_hours_same_day(self):
        start = datetime(2025, 3, 3, 9, 0)   # Monday 9am
        end = datetime(2025, 3, 3, 17, 0)     # Monday 5pm
        assert _business_hours_between(start, end) == 8.0

    def test_business_hours_weekend_skipped(self):
        start = datetime(2025, 3, 7, 9, 0)    # Friday 9am
        end = datetime(2025, 3, 10, 17, 0)    # Monday 5pm
        # Friday (8h) + Monday (8h) = 16h
        assert _business_hours_between(start, end) == 16.0


# ── Approval Velocity ─────────────────────────────────────────────────────────

class TestApprovalVelocity:
    def test_basic_approval(self):
        tickets = [
            {"key": "T-1", "summary": "Task 1", "status": "Done"},
        ]
        changelogs = {
            "T-1": [{
                "created": _ts(5, 10),  # entered PA
                "author": {"accountId": "dev-1", "displayName": "Dev"},
                "items": [{"field": "status", "fromString": "In Progress", "toString": "Pending Approval"}],
            }, {
                "created": _ts(4, 14),  # left PA (by PM)
                "author": {"accountId": PM_ID, "displayName": "Jane PM"},
                "items": [{"field": "status", "fromString": "Pending Approval", "toString": "Done"}],
            }],
        }
        result = _compute_approval_velocity(tickets, changelogs, PM_ID, PM_NAMES)
        assert result["approvals_completed"] == 1
        assert result["pending_approval_backlog"] == 0
        assert result["avg_pending_approval_hours"] > 0

    def test_currently_pending(self):
        tickets = [{"key": "T-2", "summary": "Pending", "status": "Pending Approval"}]
        changelogs = {
            "T-2": [{
                "created": _ts(2, 10),
                "author": {"accountId": "dev-1"},
                "items": [{"field": "status", "fromString": "QA", "toString": "Pending Approval"}],
            }],
        }
        result = _compute_approval_velocity(tickets, changelogs, PM_ID, PM_NAMES)
        assert result["pending_approval_backlog"] == 1
        assert result["approvals_completed"] == 0


# ── Comment Activity ──────────────────────────────────────────────────────────

class TestCommentActivity:
    def test_engagement_and_waiting(self):
        tickets = [
            {"key": "T-1", "summary": "Task 1", "status": "In Progress"},
            {"key": "T-2", "summary": "Task 2", "status": "In Progress"},
        ]
        comments = {
            "T-1": [
                {"author": {"accountId": PM_ID, "displayName": "Jane PM"}, "created": _ts(3)},
                {"author": {"accountId": "dev-1", "displayName": "Bob"}, "created": _ts(2)},
            ],
            "T-2": [
                {"author": {"accountId": "dev-1", "displayName": "Bob"}, "created": _ts(1)},
            ],
        }
        result = _compute_comment_activity(tickets, comments, PM_ID, PM_NAMES)
        assert result["total_pm_comments"] == 1
        assert result["tickets_engaged"] == 1
        assert result["total_sprint_tickets"] == 2
        assert result["engagement_ratio"] == 0.50
        # T-1: PM commented then dev replied → waiting on PM
        assert result["threads_waiting_on_pm"] == 1


# ── Grooming ──────────────────────────────────────────────────────────────────

class TestGrooming:
    def test_estimation_coverage(self):
        tickets = [
            {"key": "T-1", "reporter_id": PM_ID, "original_estimate_seconds": 3600},
            {"key": "T-2", "reporter_id": "dev-1", "original_estimate_seconds": 0},
            {"key": "T-3", "reporter_id": PM_ID, "original_estimate_seconds": 7200},
        ]
        result = _compute_grooming(tickets, PM_ID)
        assert result["tickets_created_by_pm"] == 2
        assert result["unestimated_count"] == 1
        assert 60 < result["estimation_coverage_pct"] < 70  # 2/3 ≈ 66.7%


# ── Transitions ───────────────────────────────────────────────────────────────

class TestTransitions:
    def test_pm_transitions_and_reopens(self):
        changelogs = {
            "T-1": [
                {
                    "created": _ts(3),
                    "author": {"accountId": PM_ID, "displayName": "Jane PM"},
                    "items": [{"field": "status", "fromString": "In Progress", "toString": "Done"}],
                },
                {
                    "created": _ts(2),
                    "author": {"accountId": PM_ID, "displayName": "Jane PM"},
                    "items": [{"field": "status", "fromString": "Done", "toString": "In Progress"}],
                },
                {
                    "created": _ts(1),
                    "author": {"accountId": "dev-1", "displayName": "Dev"},
                    "items": [{"field": "status", "fromString": "In Progress", "toString": "QA"}],
                },
            ],
        }
        result = _compute_transitions(changelogs, PM_ID, PM_NAMES)
        assert result["transitions_by_pm"] == 2  # only PM's entries
        assert result["reopens_rejections"] == 1  # Done → In Progress


# ── Scope Management ──────────────────────────────────────────────────────────

class TestScopeManagement:
    def test_assignment_balance(self):
        tickets = [
            {"key": "T-1", "assignee_id": "dev-1", "original_estimate_seconds": 36000},
            {"key": "T-2", "assignee_id": "dev-1", "original_estimate_seconds": 36000},
            {"key": "T-3", "assignee_id": "dev-2", "original_estimate_seconds": 36000},
        ]
        result = _compute_scope_management(tickets, {}, PM_ID, PM_NAMES)
        # dev-1 has 20h, dev-2 has 10h → CV should be > 0
        assert result["assignment_balance_cv"] > 0


# ── Blocker Response ──────────────────────────────────────────────────────────

class TestBlockerResponse:
    def test_pm_responded(self):
        tickets = [{"key": "T-1", "summary": "Blocked task", "status": "Blocked"}]
        changelogs = {
            "T-1": [{
                "created": _ts(5, 10),
                "author": {"accountId": "dev-1"},
                "items": [{"field": "status", "fromString": "In Progress", "toString": "Blocked"}],
            }],
        }
        comments = {
            "T-1": [
                {"author": {"accountId": PM_ID, "displayName": "Jane PM"}, "created": _ts(4, 14)},
            ],
        }
        result = _compute_blocker_response(tickets, changelogs, comments, PM_ID, PM_NAMES)
        assert result["avg_blocked_to_pm_comment_hours"] is not None
        assert result["avg_blocked_to_pm_comment_hours"] > 0
        assert result["blocked_no_pm_engagement"] == 0


# ── Grading ───────────────────────────────────────────────────────────────────

class TestGrading:
    def test_all_a_grades(self):
        metrics = {
            "avg_pending_approval_hours": 4,
            "pending_approval_backlog": 1,
            "engagement_ratio": 0.90,
            "avg_pm_response_hours": 2,
            "threads_waiting_on_pm": 1,
            "estimation_coverage_pct": 95,
            "transitions_by_pm": 25,
            "reopens_rejections": 5,
            "avg_blocked_to_pm_comment_hours": 2,
            "blocked_no_pm_engagement": 0,
        }
        grades = _compute_grades(metrics)
        assert grades["overall"] == "A"
        assert grades["approval"] == "A"
        assert grades["engagement"] == "A"

    def test_poor_grades(self):
        metrics = {
            "avg_pending_approval_hours": 100,
            "pending_approval_backlog": 20,
            "engagement_ratio": 0.10,
            "avg_pm_response_hours": 50,
            "threads_waiting_on_pm": 15,
            "estimation_coverage_pct": 20,
            "transitions_by_pm": 1,
            "reopens_rejections": 0,
            "avg_blocked_to_pm_comment_hours": 50,
            "blocked_no_pm_engagement": 10,
        }
        grades = _compute_grades(metrics)
        assert grades["overall"] == "D"


# ── Full Pipeline ─────────────────────────────────────────────────────────────

class TestFullPipeline:
    def test_compute_pm_audit_returns_all_fields(self):
        tickets = [
            {"key": "T-1", "summary": "Task 1", "status": "Done",
             "assignee": "Dev", "assignee_id": "dev-1", "reporter_id": PM_ID,
             "original_estimate_seconds": 7200},
            {"key": "T-2", "summary": "Task 2", "status": "In Progress",
             "assignee": "Dev", "assignee_id": "dev-1", "reporter_id": "dev-1",
             "original_estimate_seconds": 0},
        ]
        comments = {
            "T-1": [{"author": {"accountId": PM_ID, "displayName": "Jane PM"}, "created": _ts(2)}],
            "T-2": [],
        }
        changelogs = {"T-1": [], "T-2": []}
        sprint_meta = {"sprint_id": "100", "sprint_name": "Sprint 5", "start_date": "2025-03-01", "end_date": "2025-03-14"}

        result = compute_pm_audit(tickets, comments, changelogs, PM_ID, PM_NAMES, sprint_meta)

        assert result["pm_account_id"] == PM_ID
        assert result["sprint_name"] == "Sprint 5"
        assert result["overall_grade"] in ("A", "B", "C", "D")
        assert "grades" in result
        assert "detail" in result
        assert result["total_pm_comments"] == 1
        assert result["tickets_engaged"] == 1
        assert result["tickets_created_by_pm"] == 1
        assert result["unestimated_count"] == 1
