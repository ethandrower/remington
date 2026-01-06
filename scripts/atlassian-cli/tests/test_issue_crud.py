"""
Test CRUD operations for Jira issues.
"""

import pytest


class TestIssueCreate:
    """Tests for creating issues."""

    def test_create_basic_issue(self, jira_client, test_project_key, created_issues):
        """Test creating a basic issue with minimal fields."""
        result = jira_client.create_issue(
            project_key=test_project_key,
            issue_type="Task",
            summary="[TEST] Basic issue creation"
        )

        assert 'key' in result
        assert 'id' in result

        issue_key = result['key']
        created_issues.append(issue_key)

        # Verify issue was created
        issue = jira_client.get_issue(issue_key)
        assert issue['key'] == issue_key
        assert issue['fields']['summary'] == "[TEST] Basic issue creation"

    def test_create_issue_with_description(self, jira_client, test_project_key, created_issues):
        """Test creating an issue with description."""
        description = "This is a test description with multiple lines.\n\nSecond paragraph here."

        result = jira_client.create_issue(
            project_key=test_project_key,
            issue_type="Task",
            summary="[TEST] Issue with description",
            description=description
        )

        issue_key = result['key']
        created_issues.append(issue_key)

        # Verify description was set
        issue = jira_client.get_issue(issue_key)
        issue_desc = issue['fields']['description']

        # Extract text from ADF (Atlassian Document Format)
        assert issue_desc is not None
        assert issue_desc['type'] == 'doc'

    def test_create_subtask(self, jira_client, test_parent_issue, created_issues):
        """Test creating a subtask under a parent issue."""
        parent_key = test_parent_issue['key']

        result = jira_client.create_subtask(
            parent_key=parent_key,
            summary="[TEST] Test subtask",
            description="This is a test subtask"
        )

        assert 'key' in result
        subtask_key = result['key']
        created_issues.append(subtask_key)

        # Verify subtask was created with correct parent
        subtask = jira_client.get_issue(subtask_key)
        assert subtask['fields']['issuetype']['subtask'] is True
        assert subtask['fields']['parent']['key'] == parent_key


class TestIssueRead:
    """Tests for reading issues."""

    def test_get_issue(self, jira_client, test_issue):
        """Test retrieving an issue."""
        issue_key = test_issue['key']

        issue = jira_client.get_issue(issue_key)

        assert issue['key'] == issue_key
        assert 'fields' in issue
        assert 'summary' in issue['fields']
        assert 'status' in issue['fields']

    def test_get_nonexistent_issue(self, jira_client):
        """Test retrieving a non-existent issue returns error."""
        with pytest.raises(Exception):
            jira_client.get_issue("NONEXISTENT-99999")


class TestIssueUpdate:
    """Tests for updating issues."""

    def test_update_summary(self, jira_client, test_issue):
        """Test updating issue summary."""
        issue_key = test_issue['key']
        new_summary = "[TEST] Updated summary"

        jira_client.update_issue(issue_key, summary=new_summary)

        # Verify update
        updated_issue = jira_client.get_issue(issue_key)
        assert updated_issue['fields']['summary'] == new_summary

    def test_update_description(self, jira_client, test_issue):
        """Test updating issue description."""
        issue_key = test_issue['key']
        new_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Updated description"}]
                }
            ]
        }

        jira_client.update_issue(issue_key, description=new_description)

        # Verify update
        updated_issue = jira_client.get_issue(issue_key)
        assert updated_issue['fields']['description'] is not None

    def test_update_multiple_fields(self, jira_client, test_issue):
        """Test updating multiple fields at once."""
        issue_key = test_issue['key']

        new_summary = "[TEST] Multi-field update"
        new_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Multi-field description"}]
                }
            ]
        }

        jira_client.update_issue(
            issue_key,
            summary=new_summary,
            description=new_description
        )

        # Verify updates
        updated_issue = jira_client.get_issue(issue_key)
        assert updated_issue['fields']['summary'] == new_summary
        assert updated_issue['fields']['description'] is not None


class TestIssueDelete:
    """Tests for deleting issues."""

    def test_delete_issue(self, jira_client, test_project_key):
        """Test deleting an issue."""
        # Create issue to delete
        result = jira_client.create_issue(
            project_key=test_project_key,
            issue_type="Task",
            summary="[TEST] Issue to be deleted"
        )

        issue_key = result['key']

        # Delete the issue
        response = jira_client._request("DELETE", f"issue/{issue_key}")
        assert response.status_code == 204

        # Verify issue is gone
        with pytest.raises(Exception):
            jira_client.get_issue(issue_key)

    def test_delete_nonexistent_issue(self, jira_client):
        """Test deleting a non-existent issue."""
        response = jira_client._request("DELETE", "issue/NONEXISTENT-99999")
        assert response.status_code in [404, 400]  # Expected error codes
