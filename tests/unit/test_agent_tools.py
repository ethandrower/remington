"""
Unit tests for the @tool wrappers in src/agents/tools/jira_tools.py.

Strategy:
  - Patch the underlying trinity.jira.* functions (not the HTTP layer).
  - Verify each @tool function formats its output correctly and handles errors.
  - No network calls, no real credentials needed.

LangGraph @tool functions are invoked via .invoke({"arg": value}) —
that's the standard LangChain tool interface.
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# search_jira
# ---------------------------------------------------------------------------

class TestSearchJiraTool:

    def test_returns_formatted_ticket_list(self):
        fake_result = {
            "issues": [
                {"key": "ECD-100", "summary": "Fix login bug", "status": "In Progress", "assignee": "Alice"},
                {"key": "ECD-101", "summary": "Add dark mode", "status": "To Do", "assignee": None},
            ],
            "total": 2,
        }
        with patch("src.agents.tools.jira_tools._search_jira", return_value=fake_result):
            from src.agents.tools.jira_tools import search_jira
            result = search_jira.invoke({"jql": "project = ECD", "max_results": 10})

        assert "ECD-100" in result
        assert "Fix login bug" in result
        assert "In Progress" in result
        assert "Alice" in result
        assert "ECD-101" in result
        assert "Unassigned" in result  # None assignee → "Unassigned"
        assert "Found 2 tickets" in result

    def test_no_results_returns_clear_message(self):
        fake_result = {"issues": [], "total": 0}
        with patch("src.agents.tools.jira_tools._search_jira", return_value=fake_result):
            from src.agents.tools.jira_tools import search_jira
            result = search_jira.invoke({"jql": "project = ECD AND assignee = nobody"})

        assert "No tickets found" in result

    def test_api_error_returns_failure_message(self):
        fake_result = {"error": True, "message": "Unauthorized"}
        with patch("src.agents.tools.jira_tools._search_jira", return_value=fake_result):
            from src.agents.tools.jira_tools import search_jira
            result = search_jira.invoke({"jql": "project = ECD"})

        assert "failed" in result.lower()
        assert "Unauthorized" in result

    def test_max_results_capped_at_50(self):
        """max_results above 50 should be capped before calling the underlying function."""
        fake_result = {"issues": [], "total": 0}
        with patch("src.agents.tools.jira_tools._search_jira", return_value=fake_result) as mock_fn:
            from src.agents.tools.jira_tools import search_jira
            search_jira.invoke({"jql": "project = ECD", "max_results": 200})
            mock_fn.assert_called_once_with("project = ECD", max_results=50)

    def test_ticket_summary_truncated_to_70_chars(self):
        long_summary = "A" * 100
        fake_result = {
            "issues": [{"key": "ECD-100", "summary": long_summary, "status": "To Do", "assignee": "Alice"}],
            "total": 1,
        }
        with patch("src.agents.tools.jira_tools._search_jira", return_value=fake_result):
            from src.agents.tools.jira_tools import search_jira
            result = search_jira.invoke({"jql": "project = ECD"})

        # Summary capped at 70 chars — full 100-char string should NOT appear
        assert long_summary not in result
        assert "A" * 70 in result


# ---------------------------------------------------------------------------
# get_jira_ticket
# ---------------------------------------------------------------------------

class TestGetJiraTicketTool:

    def test_returns_basic_ticket_info(self):
        fake_result = {
            "summary": "Fix login bug",
            "status": "In Progress",
            "priority": "High",
            "type": "Bug",
            "assignee": "Alice",
            "reporter": "Bob",
        }
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-100", "include_comments": False})

        assert "ECD-100" in result
        assert "Fix login bug" in result
        assert "In Progress" in result
        assert "High" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_includes_sprint_when_present(self):
        fake_result = {
            "summary": "Fix login bug",
            "status": "In Progress",
            "priority": "High",
            "type": "Bug",
            "assignee": "Alice",
            "reporter": "Bob",
            "sprint": "Sprint 42",
        }
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-100"})

        assert "Sprint 42" in result

    def test_includes_comments_when_requested(self):
        fake_result = {
            "summary": "Fix login bug",
            "status": "In Progress",
            "priority": "High",
            "type": "Bug",
            "assignee": "Alice",
            "reporter": "Bob",
            "comments": [
                {"author": "Alice", "created": "2026-01-01T10:00:00", "text": "Working on it now."},
            ],
        }
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-100", "include_comments": True})

        assert "Working on it now." in result

    def test_does_not_include_comments_by_default(self):
        fake_result = {
            "summary": "Fix login bug",
            "status": "In Progress",
            "priority": "High",
            "type": "Bug",
            "assignee": "Alice",
            "reporter": "Bob",
            "comments": [
                {"author": "Alice", "created": "2026-01-01T10:00:00", "text": "Working on it now."},
            ],
        }
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-100", "include_comments": False})

        assert "Working on it now." not in result

    def test_error_response_includes_key(self):
        fake_result = {"error": True, "message": "Issue not found"}
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-999"})

        assert "Could not fetch" in result
        assert "ECD-999" in result

    def test_description_truncated_at_500_chars(self):
        fake_result = {
            "summary": "Test",
            "status": "To Do",
            "priority": "Low",
            "type": "Task",
            "assignee": "Alice",
            "reporter": "Bob",
            "description": "D" * 600,
        }
        with patch("src.agents.tools.jira_tools._get_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import get_jira_ticket
            result = get_jira_ticket.invoke({"issue_key": "ECD-100"})

        assert "..." in result
        assert "D" * 600 not in result


# ---------------------------------------------------------------------------
# add_jira_comment
# ---------------------------------------------------------------------------

class TestAddJiraCommentTool:

    def test_successful_comment_returns_confirmation(self):
        fake_result = {"error": False, "comment_id": "comment-789"}
        with patch("src.agents.tools.jira_tools._add_comment", return_value=fake_result):
            from src.agents.tools.jira_tools import add_jira_comment
            result = add_jira_comment.invoke({"issue_key": "ECD-100", "comment": "Status update: done."})

        assert "ECD-100" in result
        assert "comment-789" in result
        assert "Status update: done." in result

    def test_long_comment_text_is_truncated_in_confirmation(self):
        long_comment = "X" * 200
        fake_result = {"error": False, "comment_id": "comment-001"}
        with patch("src.agents.tools.jira_tools._add_comment", return_value=fake_result):
            from src.agents.tools.jira_tools import add_jira_comment
            result = add_jira_comment.invoke({"issue_key": "ECD-100", "comment": long_comment})

        # Confirmation shows ≤150 chars of comment text
        assert "..." in result
        assert long_comment not in result

    def test_error_returns_failure_message(self):
        fake_result = {"error": True, "message": "Permission denied"}
        with patch("src.agents.tools.jira_tools._add_comment", return_value=fake_result):
            from src.agents.tools.jira_tools import add_jira_comment
            result = add_jira_comment.invoke({"issue_key": "ECD-100", "comment": "Hello"})

        assert "Failed" in result
        assert "Permission denied" in result
        assert "ECD-100" in result


# ---------------------------------------------------------------------------
# transition_jira_ticket
# ---------------------------------------------------------------------------

class TestTransitionJiraTicketTool:

    def test_successful_transition_confirms_new_status(self):
        fake_result = {"error": False, "new_status": "Done"}
        with patch("trinity.jira.transition_issue.transition_jira_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import transition_jira_ticket
            result = transition_jira_ticket.invoke({"issue_key": "ECD-100", "new_status": "Done"})

        assert "ECD-100" in result
        assert "Done" in result

    def test_failed_transition_shows_available_options(self):
        fake_result = {
            "error": True,
            "message": "Transition not found",
            "available_transitions": ["In Progress", "Done", "Blocked"],
        }
        with patch("trinity.jira.transition_issue.transition_jira_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import transition_jira_ticket
            result = transition_jira_ticket.invoke({"issue_key": "ECD-100", "new_status": "Flying"})

        assert "Could not transition" in result
        assert "In Progress" in result
        assert "Done" in result
        assert "Blocked" in result

    def test_failed_transition_without_available_options(self):
        fake_result = {"error": True, "message": "Unknown error"}
        with patch("trinity.jira.transition_issue.transition_jira_issue", return_value=fake_result):
            from src.agents.tools.jira_tools import transition_jira_ticket
            result = transition_jira_ticket.invoke({"issue_key": "ECD-100", "new_status": "Nope"})

        assert "Could not transition" in result
        assert "Unknown error" in result


# ---------------------------------------------------------------------------
# lookup_jira_user
# ---------------------------------------------------------------------------

class TestLookupJiraUserTool:

    def test_single_user_returns_name_and_account_id(self):
        fake_result = {
            "users": [{"displayName": "Alice Smith", "accountId": "712020:abc-123"}]
        }
        with patch("src.agents.tools.jira_tools._lookup_user", return_value=fake_result):
            from src.agents.tools.jira_tools import lookup_jira_user
            result = lookup_jira_user.invoke({"name_or_email": "Alice"})

        assert "Alice Smith" in result
        assert "712020:abc-123" in result

    def test_multiple_users_lists_all_matches(self):
        fake_result = {
            "users": [
                {"displayName": "Alice Smith", "accountId": "712020:aaa"},
                {"displayName": "Alice Johnson", "accountId": "712020:bbb"},
            ]
        }
        with patch("src.agents.tools.jira_tools._lookup_user", return_value=fake_result):
            from src.agents.tools.jira_tools import lookup_jira_user
            result = lookup_jira_user.invoke({"name_or_email": "Alice"})

        assert "Multiple users" in result
        assert "Alice Smith" in result
        assert "Alice Johnson" in result

    def test_no_user_found_returns_helpful_message(self):
        fake_result = {"users": []}
        with patch("src.agents.tools.jira_tools._lookup_user", return_value=fake_result):
            from src.agents.tools.jira_tools import lookup_jira_user
            result = lookup_jira_user.invoke({"name_or_email": "Nobody Real"})

        assert "No Jira user found" in result
        assert "Nobody Real" in result

    def test_api_error_returns_failure_message(self):
        fake_result = {"error": True, "message": "Service unavailable"}
        with patch("src.agents.tools.jira_tools._lookup_user", return_value=fake_result):
            from src.agents.tools.jira_tools import lookup_jira_user
            result = lookup_jira_user.invoke({"name_or_email": "Alice"})

        assert "failed" in result.lower()
        assert "Service unavailable" in result
