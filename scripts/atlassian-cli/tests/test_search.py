"""
Test search and query operations.
"""

import pytest
import time


class TestJQLSearch:
    """Tests for JQL search functionality."""

    def test_search_by_project(self, jira_client, test_project_key):
        """Test searching issues by project."""
        jql = f"project = {test_project_key}"

        results = jira_client.search_issues(jql, max_results=10)

        # API returns either 'total', 'totalSize', or just 'issues' array
        assert 'issues' in results or 'values' in results
        issues = results.get('issues', results.get('values', []))

        # Verify all results are from the correct project (if any exist)
        for issue in issues:
            assert issue['fields']['project']['key'] == test_project_key

    def test_search_by_issue_key(self, jira_client, test_issue):
        """Test searching for a specific issue by key."""
        issue_key = test_issue['key']
        jql = f"key = {issue_key}"

        results = jira_client.search_issues(jql)

        issues = results.get('issues', results.get('values', []))
        assert len(issues) == 1
        assert issues[0]['key'] == issue_key

    def test_search_by_summary(self, jira_client, test_project_key, created_issues):
        """Test searching by summary text."""
        # Create issue with unique summary
        unique_summary = f"[TEST] Unique search term {time.time()}"
        result = jira_client.create_issue(
            project_key=test_project_key,
            issue_type="Task",
            summary=unique_summary
        )
        created_issues.append(result['key'])

        # Search for it
        jql = f'project = {test_project_key} AND summary ~ "Unique search term"'
        results = jira_client.search_issues(jql)

        issues = results.get('issues', results.get('values', []))
        assert len(issues) >= 1

        # Verify our issue is in results
        found_keys = [issue['key'] for issue in issues]
        assert result['key'] in found_keys

    def test_search_by_status(self, jira_client, test_project_key):
        """Test searching by status."""
        jql = f'project = {test_project_key} AND status = "To Do"'

        results = jira_client.search_issues(jql, max_results=5)

        issues = results.get('issues', results.get('values', []))

        # All results should have To Do status
        for issue in issues:
            status = issue['fields']['status']['name']
            assert status == "To Do" or "todo" in status.lower()

    def test_search_with_ordering(self, jira_client, test_project_key):
        """Test searching with ORDER BY clause."""
        jql = f"project = {test_project_key} ORDER BY created DESC"

        results = jira_client.search_issues(jql, max_results=5)

        issues = results.get('issues', results.get('values', []))

        if len(issues) >= 2:
            # Verify ordering (newer issues first)
            first_created = issues[0]['fields']['created']
            second_created = issues[1]['fields']['created']
            assert first_created >= second_created

    def test_search_with_field_selection(self, jira_client, test_project_key):
        """Test searching with specific field selection."""
        jql = f"project = {test_project_key}"
        fields = ['summary', 'status', 'created']

        results = jira_client.search_issues(jql, fields=fields, max_results=5)

        issues = results.get('issues', results.get('values', []))

        if len(issues) > 0:
            # Verify only requested fields are returned
            issue = issues[0]
            assert 'fields' in issue
            assert 'summary' in issue['fields']
            assert 'status' in issue['fields']

    def test_search_with_max_results(self, jira_client, test_project_key):
        """Test limiting search results."""
        max_results = 3
        jql = f"project = {test_project_key}"

        results = jira_client.search_issues(jql, max_results=max_results)

        issues = results.get('issues', results.get('values', []))
        assert len(issues) <= max_results

    def test_search_complex_jql(self, jira_client, test_project_key):
        """Test complex JQL query with multiple conditions."""
        jql = f'project = {test_project_key} AND (status = "To Do" OR status = "In Progress") AND created >= -30d'

        results = jira_client.search_issues(jql, max_results=10)

        # Should execute without error
        assert 'total' in results or 'totalSize' in results

    def test_search_no_results(self, jira_client):
        """Test search that returns no results."""
        jql = "project = NONEXISTENT_PROJECT_12345"

        results = jira_client.search_issues(jql)

        total = results.get('total', results.get('totalSize', 0))
        assert total == 0

        issues = results.get('issues', results.get('values', []))
        assert len(issues) == 0

    def test_search_created_today(self, jira_client, test_project_key, test_issue):
        """Test searching for issues created today."""
        jql = f'project = {test_project_key} AND created >= startOfDay()'

        results = jira_client.search_issues(jql)

        issues = results.get('issues', results.get('values', []))

        # Our test issue should be in the results
        issue_keys = [issue['key'] for issue in issues]
        assert test_issue['key'] in issue_keys


class TestUserSearch:
    """Tests for user search functionality."""

    def test_search_current_user(self, jira_client):
        """Test searching for current user."""
        # Get current user info
        response = jira_client._request("GET", "myself")
        response.raise_for_status()
        myself = response.json()

        my_email = myself['emailAddress']

        # Search for user
        users = jira_client.search_users(my_email)

        assert len(users) >= 1

        # Verify we found ourselves
        account_ids = [user['accountId'] for user in users]
        assert myself['accountId'] in account_ids

    def test_search_user_by_partial_email(self, jira_client):
        """Test searching for user with partial email."""
        # Get current user
        response = jira_client._request("GET", "myself")
        response.raise_for_status()
        myself = response.json()

        email = myself['emailAddress']
        # Use first part of email
        partial_email = email.split('@')[0][:5]

        users = jira_client.search_users(partial_email)

        # Should return at least some users
        assert len(users) >= 1

    def test_search_nonexistent_user(self, jira_client):
        """Test searching for non-existent user."""
        users = jira_client.search_users("nonexistent_user_12345_xyz")

        # Should return empty list
        assert len(users) == 0


class TestAdvancedQueries:
    """Tests for advanced query operations."""

    def test_search_by_assignee(self, jira_client, test_project_key):
        """Test searching by assignee."""
        # Get current user
        response = jira_client._request("GET", "myself")
        response.raise_for_status()
        myself = response.json()

        jql = f'project = {test_project_key} AND assignee = "{myself["accountId"]}"'

        results = jira_client.search_issues(jql, max_results=5)

        issues = results.get('issues', results.get('values', []))

        # Verify assignees
        for issue in issues:
            assignee = issue['fields'].get('assignee')
            if assignee:
                assert assignee['accountId'] == myself['accountId']

    def test_search_unassigned_issues(self, jira_client, test_project_key):
        """Test searching for unassigned issues."""
        jql = f'project = {test_project_key} AND assignee is EMPTY'

        results = jira_client.search_issues(jql, max_results=5)

        issues = results.get('issues', results.get('values', []))

        # All issues should have no assignee
        for issue in issues:
            assert issue['fields'].get('assignee') is None

    def test_search_by_type(self, jira_client, test_project_key):
        """Test searching by issue type."""
        jql = f'project = {test_project_key} AND type = Task'

        results = jira_client.search_issues(jql, max_results=5)

        issues = results.get('issues', results.get('values', []))

        # All should be tasks
        for issue in issues:
            issue_type = issue['fields']['issuetype']['name']
            assert issue_type == "Task"
