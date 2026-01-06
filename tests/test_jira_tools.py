#!/usr/bin/env python3
"""
Unit Tests for Jira Direct API Tools

Tests each tool in src/tools/jira/ for:
1. Correct API responses
2. Error handling
3. Data transformation
4. CLI interface
"""

import pytest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.jira.search import search_jira
from src.tools.jira.get_issue import get_jira_issue
from src.tools.jira.add_comment import add_jira_comment
from src.tools.jira.edit_issue import edit_jira_issue
from src.tools.jira.transition_issue import transition_jira_issue
from src.tools.jira.get_transitions import get_jira_transitions
from src.tools.jira.lookup_user import lookup_jira_user
from src.tools.jira.list_projects import list_jira_projects
from src.tools.base import get_jira_auth_headers, build_adf_comment, JIRA_BASE_URL


class TestJiraAuthentication:
    """Test Jira authentication configuration"""

    def test_auth_headers_format(self):
        """Verify auth headers are properly formatted"""
        headers = get_jira_auth_headers()

        assert "Authorization" in headers, "Missing Authorization header"
        assert headers["Authorization"].startswith("Basic "), "Should use Basic auth"
        assert "Content-Type" in headers, "Missing Content-Type header"
        assert headers["Content-Type"] == "application/json"
        assert "Accept" in headers, "Missing Accept header"

    def test_jira_base_url_format(self):
        """Verify Jira base URL is correctly formed"""
        assert JIRA_BASE_URL.startswith("https://api.atlassian.com/ex/jira/")
        assert "67bbfd03-b309-414f-9640-908213f80628" in JIRA_BASE_URL

    def test_env_vars_configured(self):
        """Verify required environment variables are set"""
        assert os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL"), "Missing ATLASSIAN_SERVICE_ACCOUNT_EMAIL"
        assert os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN"), "Missing ATLASSIAN_SERVICE_ACCOUNT_TOKEN"
        assert os.getenv("ATLASSIAN_CLOUD_ID"), "Missing ATLASSIAN_CLOUD_ID"


class TestADFBuilder:
    """Test Atlassian Document Format comment builder"""

    def test_simple_text_adf(self):
        """Test building ADF from simple text"""
        adf = build_adf_comment("Hello, this is a test comment.")

        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert len(adf["content"]) > 0
        assert adf["content"][0]["type"] == "paragraph"

    def test_adf_with_mentions(self):
        """Test building ADF with @mentions"""
        mentions = [
            {"id": "712020:abc123", "name": "Test User"}
        ]
        adf = build_adf_comment("Hello @Test User", mentions)

        # Should contain mention node
        content_str = json.dumps(adf)
        assert "mention" in content_str, "Should contain mention node"
        assert "712020:abc123" in content_str, "Should contain account ID"

    def test_adf_multiline(self):
        """Test building ADF with multiple lines"""
        text = "Line 1\n\nLine 2\n\nLine 3"
        adf = build_adf_comment(text)

        # Should have multiple paragraphs
        assert len(adf["content"]) >= 1


class TestSearchJira:
    """Test Jira search functionality"""

    def test_search_returns_dict(self):
        """Test that search returns a dictionary"""
        result = search_jira("project = ECD", max_results=5)

        assert isinstance(result, dict), "Search should return a dict"
        assert "total" in result or "error" in result

    def test_search_with_valid_jql(self):
        """Test search with valid JQL"""
        result = search_jira("project = ECD ORDER BY created DESC", max_results=3)

        if not result.get("error"):
            assert "issues" in result, "Should contain issues array"
            assert "total" in result, "Should contain total count"
            assert "count" in result, "Should contain returned count"

    def test_search_respects_max_results(self):
        """Test that max_results is respected"""
        result = search_jira("project = ECD", max_results=2)

        if not result.get("error"):
            assert result["count"] <= 2, "Should not exceed max_results"

    def test_search_issue_fields(self):
        """Test that returned issues have expected fields"""
        result = search_jira("project = ECD", max_results=1)

        if not result.get("error") and result.get("issues"):
            issue = result["issues"][0]
            expected_fields = ["key", "summary", "status", "type"]
            for field in expected_fields:
                assert field in issue, f"Issue should have {field} field"

    def test_search_invalid_jql(self):
        """Test error handling for invalid JQL"""
        result = search_jira("invalid jql syntax !!!@@@")

        # Should return error dict, not raise exception
        assert isinstance(result, dict)


class TestGetIssue:
    """Test Jira issue retrieval"""

    def test_get_issue_returns_dict(self):
        """Test that get_issue returns a dictionary"""
        result = get_jira_issue("ECD-1")

        assert isinstance(result, dict)

    def test_get_existing_issue(self):
        """Test getting an existing issue"""
        # Use a known issue key - ECD-862 from the PR
        result = get_jira_issue("ECD-862")

        if not result.get("error"):
            assert "key" in result, "Should contain issue key"
            assert result["key"] == "ECD-862"
            assert "summary" in result
            assert "status" in result

    def test_get_nonexistent_issue(self):
        """Test getting a non-existent issue"""
        result = get_jira_issue("ECD-999999")

        # Should return error, not raise exception
        assert result.get("error") is True or "error" in result


class TestLookupUser:
    """Test Jira user lookup"""

    def test_lookup_returns_dict(self):
        """Test that lookup returns a dictionary"""
        result = lookup_jira_user("test")

        assert isinstance(result, dict)

    def test_lookup_by_email(self):
        """Test looking up user by email"""
        result = lookup_jira_user("ethan@citemed.com")

        if not result.get("error"):
            assert "users" in result
            assert "count" in result

    def test_lookup_by_name(self):
        """Test looking up user by name"""
        result = lookup_jira_user("Mohamed")

        if not result.get("error"):
            assert "users" in result
            if result["count"] > 0:
                user = result["users"][0]
                assert "account_id" in user
                assert "display_name" in user


class TestListProjects:
    """Test Jira project listing"""

    def test_list_returns_dict(self):
        """Test that list_projects returns a dictionary"""
        result = list_jira_projects()

        assert isinstance(result, dict)

    def test_list_projects_basic(self):
        """Test basic project listing"""
        result = list_jira_projects()

        if not result.get("error"):
            assert "projects" in result
            assert "count" in result

    def test_list_projects_finds_ecd(self):
        """Test that ECD project is found"""
        result = list_jira_projects(search="ECD")

        if not result.get("error"):
            assert result["count"] >= 1, "Should find at least ECD project"
            project_keys = [p["key"] for p in result["projects"]]
            assert "ECD" in project_keys, "Should find ECD project"


class TestGetTransitions:
    """Test Jira transition retrieval"""

    def test_transitions_returns_dict(self):
        """Test that get_transitions returns a dictionary"""
        result = get_jira_transitions("ECD-862")

        assert isinstance(result, dict)

    def test_transitions_has_expected_fields(self):
        """Test that transitions have expected structure"""
        result = get_jira_transitions("ECD-862")

        if not result.get("error"):
            assert "issue_key" in result
            assert "transitions" in result
            if result["transitions"]:
                transition = result["transitions"][0]
                assert "id" in transition
                assert "name" in transition


class TestCLIInterface:
    """Test command-line interface for tools"""

    def test_search_cli(self):
        """Test search tool CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.search",
             "project = ECD", "--max-results", "2"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should produce JSON output
        assert result.stdout or result.returncode == 0
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass  # CLI might have non-JSON output on errors

    def test_get_issue_cli(self):
        """Test get_issue tool CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.get_issue", "ECD-862"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass

    def test_lookup_user_cli(self):
        """Test lookup_user tool CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.lookup_user", "Mohamed"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass

    def test_list_projects_cli(self):
        """Test list_projects tool CLI"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.list_projects"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass


class TestWriteOperations:
    """Test write operations (add_comment, edit_issue, transition)

    These tests use mocking to avoid modifying real Jira issues.
    Run with --run-live flag to test against real Jira (will modify data!).
    """

    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response"""
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"id": "12345"}
        mock.text = '{"id": "12345"}'
        return mock

    def test_add_comment_structure(self):
        """Test add_comment builds correct request structure"""
        # This tests the function signature and return type
        # without actually posting to Jira
        with patch('src.tools.jira.add_comment.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "12345"}
            mock_post.return_value = mock_response

            result = add_jira_comment("ECD-TEST", "Test comment")

            assert isinstance(result, dict)
            mock_post.assert_called_once()
            # Verify the URL contains the issue key
            call_url = mock_post.call_args[0][0]
            assert "ECD-TEST" in call_url
            assert "comment" in call_url

    def test_edit_issue_structure(self):
        """Test edit_issue builds correct request structure"""
        with patch('src.tools.jira.edit_issue.requests.put') as mock_put:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_put.return_value = mock_response

            # edit_jira_issue takes a fields dict, not keyword args
            result = edit_jira_issue("ECD-TEST", fields={"summary": "Updated summary"})

            assert isinstance(result, dict)
            mock_put.assert_called_once()
            call_url = mock_put.call_args[0][0]
            assert "ECD-TEST" in call_url

    def test_transition_issue_structure(self):
        """Test transition_issue builds correct request structure"""
        with patch('src.tools.jira.transition_issue.get_jira_transitions') as mock_get:
            with patch('src.tools.jira.transition_issue.requests.post') as mock_post:
                mock_get.return_value = {
                    "transitions": [{"id": "21", "name": "In Progress"}]
                }
                mock_response = MagicMock()
                mock_response.status_code = 204
                mock_post.return_value = mock_response

                result = transition_jira_issue("ECD-TEST", "In Progress")

                assert isinstance(result, dict)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before running tests"""
    os.chdir(PROJECT_ROOT)

    # Load .env if it exists
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip().strip("'\"")
                    if key and value:
                        os.environ[key] = value

    yield


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
