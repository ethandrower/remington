"""
Pytest configuration and fixtures for Atlassian CLI tests.
"""

import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import jira-cli modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)


@pytest.fixture(scope="session")
def jira_credentials():
    """Provide Jira credentials from environment."""
    email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL')
    token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN')
    cloud_id = os.getenv('ATLASSIAN_CLOUD_ID')

    assert email, "ATLASSIAN_SERVICE_ACCOUNT_EMAIL not set in .env"
    assert token, "ATLASSIAN_SERVICE_ACCOUNT_TOKEN not set in .env"
    assert cloud_id, "ATLASSIAN_CLOUD_ID not set in .env"

    return {
        'email': email,
        'token': token,
        'cloud_id': cloud_id
    }


@pytest.fixture(scope="session")
def test_project_key():
    """Project key to use for testing."""
    # Use environment variable or default to ECD
    return os.getenv('TEST_PROJECT_KEY', 'ECD')


@pytest.fixture(scope="function")
def created_issues():
    """
    Track created issues for cleanup.
    Returns a list that tests can append issue keys to.
    """
    issues = []
    yield issues
    # Cleanup happens in the jira_client fixture


@pytest.fixture(scope="function")
def jira_client(jira_credentials, created_issues):
    """
    Provide a JiraClient instance for testing.
    Automatically cleans up created issues after each test.
    """
    # Import JiraClient from jira_client module
    from jira_client import JiraClient

    client = JiraClient(
        email=jira_credentials['email'],
        token=jira_credentials['token'],
        cloud_id=jira_credentials['cloud_id']
    )

    yield client

    # Cleanup: Delete all created issues
    for issue_key in created_issues:
        try:
            # Jira API v3 delete endpoint
            response = client._request("DELETE", f"issue/{issue_key}")
            if response.status_code == 204:
                print(f"\n✓ Cleaned up test issue: {issue_key}")
            else:
                print(f"\n⚠ Failed to cleanup {issue_key}: {response.status_code}")
        except Exception as e:
            print(f"\n⚠ Error cleaning up {issue_key}: {e}")


@pytest.fixture(scope="function")
def test_issue(jira_client, test_project_key, created_issues):
    """
    Create a test issue for use in tests.
    Automatically cleaned up after the test.
    """
    result = jira_client.create_issue(
        project_key=test_project_key,
        issue_type="Task",
        summary=f"[TEST] Automated test issue - DO NOT MODIFY",
        description="This is an automated test issue created by pytest. It will be deleted automatically."
    )

    issue_key = result['key']
    created_issues.append(issue_key)

    # Return full issue data
    issue = jira_client.get_issue(issue_key)
    return issue


@pytest.fixture(scope="function")
def test_parent_issue(jira_client, test_project_key, created_issues):
    """
    Create a parent issue for subtask tests.
    Automatically cleaned up after the test.
    """
    result = jira_client.create_issue(
        project_key=test_project_key,
        issue_type="Story",
        summary=f"[TEST] Parent story for subtask tests",
        description="This is a parent issue for testing subtasks."
    )

    issue_key = result['key']
    created_issues.append(issue_key)

    return jira_client.get_issue(issue_key)
