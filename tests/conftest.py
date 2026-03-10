"""
Pytest configuration and fixtures for project-manager tests
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


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

    # Cleanup after tests (if needed)
    pass


@pytest.fixture
def sample_jira_issue_context():
    """Provide sample Jira issue context for testing"""
    return {
        "issue_key": "PROJ-862",
        "summary": "Implement user authentication",
        "description": "Add OAuth2 authentication using Google provider. Should support login, logout, and session management.",
        "status": "In Progress",
        "priority": "High",
        "assignee": "John Doe",
        "comments": [
            {
                "id": "12345",
                "author": "Manager",
                "author_id": "712020:abc123",
                "text": "Started working on this. OAuth2 implementation in progress.",
                "created": "2026-01-04T10:30:00.000Z"
            },
            {
                "id": "12346",
                "author": "John Doe",
                "author_id": "712020:def456",
                "text": "Google OAuth is working. Need to add Microsoft as well.",
                "created": "2026-01-04T14:15:00.000Z"
            }
        ]
    }


@pytest.fixture
def sample_slack_thread_context():
    """Provide sample Slack thread context for testing"""
    return {
        "parent": {
            "text": "What's the status of PROJ-862?",
            "user": "U7L6RKG69",
            "ts": "1704470400.123456",
            "timestamp": "2026-01-04T10:30:00"
        },
        "replies": [
            {
                "text": "PROJ-862 is currently In Progress. John Doe is working on OAuth2 implementation.",
                "user": "U09BVV00XRP",  # Bot
                "ts": "1704470420.123457",
                "timestamp": "2026-01-04T10:30:20"
            },
            {
                "text": "<@U09BVV00XRP> Can you check if Microsoft OAuth is included?",
                "user": "U7L6RKG69",
                "ts": "1704470440.123458",
                "timestamp": "2026-01-04T10:30:40"
            }
        ]
    }


@pytest.fixture
def mock_jira_event_with_context(sample_jira_issue_context):
    """Provide mock Jira event with full issue context"""
    return {
        "source": "jira",
        "type": "comment_mention",
        "issue_key": "PROJ-862",
        "issue_summary": "Implement user authentication",
        "issue_status": "In Progress",
        "issue_priority": "High",
        "comment_id": "12347",
        "comment_text": "@remington can you update the priority to Highest?",
        "author": "Manager",
        "author_id": "712020:abc123",
        "timestamp": "2026-01-05T09:00:00.000Z",
        "issue_url": "https://example.atlassian.net/browse/PROJ-862",
        "issue_context": sample_jira_issue_context
    }


@pytest.fixture
def mock_slack_event_with_thread(sample_slack_thread_context):
    """Provide mock Slack event with full thread context"""
    return {
        "source": "slack",
        "type": "mention",
        "ts": "1704470440.123458",
        "channel": "C02NW7QN1RN",
        "user": "U7L6RKG69",
        "text": "<@U09BVV00XRP> Can you check if Microsoft OAuth is included?",
        "thread_ts": "1704470400.123456",
        "thread_context": sample_slack_thread_context,
        "timestamp": "2026-01-04T10:30:40"
    }
