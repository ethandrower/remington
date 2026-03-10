"""
Unit tests for the database operations of all 4 monitor files:
  - src/monitors/slack_monitor.py
  - src/monitors/jira_monitor.py
  - src/monitors/bitbucket_monitor.py
  - src/monitors/confluence_monitor.py

Strategy:
  - Pass a per-test SQLAlchemy engine directly to each monitor via engine= parameter.
  - Environment variable mocks satisfy the required config checks in __init__.
  - BitbucketMonitor's external API client is patched out (no real credentials needed).
  - Only the DB helper methods are tested — API calls are not invoked.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, inspect as sa_inspect, text


# ---------------------------------------------------------------------------
# Shared env helpers
# ---------------------------------------------------------------------------

def _set_slack_env(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_CHANNEL_STANDUP", "C01TEST")
    monkeypatch.setenv("SLACK_BOT_USER_ID", "U01TEST")


def _set_jira_env(monkeypatch):
    monkeypatch.setenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN", "test-token")
    monkeypatch.setenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "test-cloud-id")
    monkeypatch.setenv("ATLASSIAN_PROJECT_KEY", "TEST")
    monkeypatch.setenv("JIRA_INSTANCE_URL", "https://example.atlassian.net")


def _set_bitbucket_env(monkeypatch):
    monkeypatch.setenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    monkeypatch.setenv("BITBUCKET_WORKSPACE", "test-workspace")
    monkeypatch.setenv("BITBUCKET_REPOS", "test_repo")


def _set_confluence_env(monkeypatch):
    monkeypatch.setenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN", "test-token")
    monkeypatch.setenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL", "test@example.com")
    monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "test-cloud-id")
    monkeypatch.setenv("ATLASSIAN_PROJECT_KEY", "TEST")
    monkeypatch.setenv("JIRA_INSTANCE_URL", "https://example.atlassian.net")


# ---------------------------------------------------------------------------
# SlackMonitor DB tests
# ---------------------------------------------------------------------------

class TestSlackMonitorDB:
    @pytest.fixture
    def engine(self, tmp_path):
        return create_engine(
            f"sqlite:///{tmp_path}/test_slack.db",
            connect_args={"check_same_thread": False},
        )

    @pytest.fixture
    def monitor(self, engine, monkeypatch):
        _set_slack_env(monkeypatch)
        from src.monitors.slack_monitor import SlackMonitor
        return SlackMonitor(engine=engine)

    def test_schema_creates_tables(self, monitor, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"slack_processed_messages", "slack_tracked_threads", "slack_sla_alerts"}.issubset(tables)

    def test_is_processed_returns_false_initially(self, monitor):
        assert monitor.is_processed("1234567890.000001") is False

    def test_mark_processed_then_is_processed(self, monitor):
        monitor.mark_processed("1234567890.000001", response="Done")
        assert monitor.is_processed("1234567890.000001") is True

    def test_mark_processed_is_idempotent(self, monitor):
        monitor.mark_processed("1234567890.000001")
        monitor.mark_processed("1234567890.000001")  # Should not raise
        assert monitor.is_processed("1234567890.000001") is True

    def test_get_last_processed_ts_returns_zero_when_empty(self, monitor):
        assert monitor.get_last_processed_ts() == 0.0

    def test_get_last_processed_ts_after_processing(self, monitor):
        monitor.mark_processed("1704470400.123456")
        result = monitor.get_last_processed_ts()
        assert result == pytest.approx(1704470400.123456, rel=1e-6)

    def test_register_thread_stores_context(self, monitor, engine):
        monitor.register_thread("1704470400.000001", context="SLA violation for ECD-123")
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT context FROM slack_tracked_threads WHERE thread_ts = :ts"),
                {"ts": "1704470400.000001"},
            ).fetchone()
        assert row is not None
        assert row[0] == "SLA violation for ECD-123"

    def test_different_timestamps_stored_independently(self, monitor):
        monitor.mark_processed("1704470400.000001")
        monitor.mark_processed("1704470400.000002")
        assert monitor.is_processed("1704470400.000001") is True
        assert monitor.is_processed("1704470400.000002") is True
        assert monitor.is_processed("9999999999.000000") is False


# ---------------------------------------------------------------------------
# JiraMonitor DB tests
# ---------------------------------------------------------------------------

class TestJiraMonitorDB:
    @pytest.fixture
    def engine(self, tmp_path):
        return create_engine(
            f"sqlite:///{tmp_path}/test_jira.db",
            connect_args={"check_same_thread": False},
        )

    @pytest.fixture
    def monitor(self, engine, monkeypatch):
        _set_jira_env(monkeypatch)
        from src.monitors.jira_monitor import JiraMonitor
        return JiraMonitor(engine=engine)

    def test_schema_creates_tables(self, monitor, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"jira_processed_mentions", "jira_last_check"}.issubset(tables)

    def test_is_processed_returns_false_initially(self, monitor):
        assert monitor.is_processed("ECD-123", "comment-456") is False

    def test_mark_processed_then_is_processed(self, monitor):
        monitor.mark_processed("ECD-123", "comment-456")
        assert monitor.is_processed("ECD-123", "comment-456") is True

    def test_mark_processed_is_idempotent(self, monitor):
        monitor.mark_processed("ECD-123", "comment-456")
        monitor.mark_processed("ECD-123", "comment-456")  # Should not raise
        assert monitor.is_processed("ECD-123", "comment-456") is True

    def test_different_issues_are_tracked_independently(self, monitor):
        monitor.mark_processed("ECD-100", "comment-1")
        assert monitor.is_processed("ECD-100", "comment-1") is True
        assert monitor.is_processed("ECD-200", "comment-1") is False

    def test_different_comments_same_issue_are_independent(self, monitor):
        monitor.mark_processed("ECD-100", "comment-1")
        assert monitor.is_processed("ECD-100", "comment-1") is True
        assert monitor.is_processed("ECD-100", "comment-2") is False

    def test_get_last_check_time_defaults_to_recent(self, monitor):
        result = monitor.get_last_check_time()
        assert isinstance(result, datetime)
        assert (datetime.now() - result).total_seconds() < 200

    def test_set_and_get_last_check_time(self, monitor):
        now = datetime.now().replace(microsecond=0)
        monitor.set_last_check_time(now)
        retrieved = monitor.get_last_check_time()
        assert abs((retrieved - now).total_seconds()) < 2

    def test_set_last_check_time_updates_existing(self, monitor):
        t1 = datetime.now() - timedelta(hours=1)
        t2 = datetime.now()
        monitor.set_last_check_time(t1)
        monitor.set_last_check_time(t2)
        retrieved = monitor.get_last_check_time()
        assert (retrieved - t1).total_seconds() > 0


# ---------------------------------------------------------------------------
# BitbucketMonitor DB tests
# ---------------------------------------------------------------------------

class TestBitbucketMonitorDB:
    @pytest.fixture
    def engine(self, tmp_path):
        return create_engine(
            f"sqlite:///{tmp_path}/test_bitbucket.db",
            connect_args={"check_same_thread": False},
        )

    @pytest.fixture
    def monitor(self, engine, monkeypatch):
        _set_bitbucket_env(monkeypatch)
        # Patch out the external Bitbucket API client — no real credentials needed
        mock_config = {"auth": {"workspace": "test-workspace"}}
        with patch("src.monitors.bitbucket_monitor.load_bb_config", return_value=mock_config), \
             patch("src.monitors.bitbucket_monitor.BitbucketAPI", return_value=MagicMock()):
            from src.monitors.bitbucket_monitor import BitbucketMonitor
            return BitbucketMonitor(engine=engine)

    def test_schema_creates_tables(self, monitor, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {"bb_processed_pr_comments", "bb_last_check_per_repo", "bb_reviewed_pr_commits", "bb_last_pr_commit"}
        assert expected.issubset(tables)

    def test_is_processed_returns_false_initially(self, monitor):
        assert monitor.is_processed("my_repo", 42, "comment-123") is False

    def test_mark_and_check_processed(self, monitor):
        monitor.mark_processed("my_repo", 42, "comment-123")
        assert monitor.is_processed("my_repo", 42, "comment-123") is True

    def test_mark_processed_is_idempotent(self, monitor):
        monitor.mark_processed("my_repo", 42, "comment-123")
        monitor.mark_processed("my_repo", 42, "comment-123")  # Should not raise
        assert monitor.is_processed("my_repo", 42, "comment-123") is True

    def test_different_repos_are_independent(self, monitor):
        monitor.mark_processed("repo_a", 1, "comment-1")
        assert monitor.is_processed("repo_a", 1, "comment-1") is True
        assert monitor.is_processed("repo_b", 1, "comment-1") is False

    def test_different_prs_are_independent(self, monitor):
        monitor.mark_processed("my_repo", 1, "comment-1")
        assert monitor.is_processed("my_repo", 1, "comment-1") is True
        assert monitor.is_processed("my_repo", 2, "comment-1") is False

    def test_get_last_check_time_defaults_to_past(self, monitor):
        result = monitor.get_last_check_time("test_repo")
        assert isinstance(result, datetime)
        assert result <= datetime.now()

    def test_set_and_get_last_check_time(self, monitor):
        now = datetime.now().replace(microsecond=0)
        monitor.set_last_check_time("test_repo", now)
        retrieved = monitor.get_last_check_time("test_repo")
        assert abs((retrieved - now).total_seconds()) < 2

    def test_different_repos_have_independent_check_times(self, monitor):
        t1 = datetime.now() - timedelta(hours=1)
        t2 = datetime.now()
        monitor.set_last_check_time("repo_a", t1)
        monitor.set_last_check_time("repo_b", t2)
        assert monitor.get_last_check_time("repo_a") < monitor.get_last_check_time("repo_b")

    def test_get_last_reviewed_commit_returns_none_initially(self, monitor):
        assert monitor.get_last_reviewed_commit("my_repo", 1) is None

    def test_mark_commit_reviewed_stores_sha(self, monitor):
        monitor.mark_commit_reviewed("my_repo", 1, "abc123def456")
        assert monitor.get_last_reviewed_commit("my_repo", 1) == "abc123def456"

    def test_mark_commit_reviewed_updates_on_new_commit(self, monitor):
        monitor.mark_commit_reviewed("my_repo", 1, "old_sha")
        monitor.mark_commit_reviewed("my_repo", 1, "new_sha")
        assert monitor.get_last_reviewed_commit("my_repo", 1) == "new_sha"

    def test_different_prs_have_independent_commits(self, monitor):
        monitor.mark_commit_reviewed("my_repo", 1, "sha_for_pr1")
        assert monitor.get_last_reviewed_commit("my_repo", 1) == "sha_for_pr1"
        assert monitor.get_last_reviewed_commit("my_repo", 2) is None


# ---------------------------------------------------------------------------
# ConfluenceMonitor DB tests
# ---------------------------------------------------------------------------

class TestConfluenceMonitorDB:
    @pytest.fixture
    def engine(self, tmp_path):
        return create_engine(
            f"sqlite:///{tmp_path}/test_confluence.db",
            connect_args={"check_same_thread": False},
        )

    @pytest.fixture
    def monitor(self, engine, monkeypatch):
        _set_confluence_env(monkeypatch)
        from src.monitors.confluence_monitor import ConfluenceMonitor
        return ConfluenceMonitor(engine=engine)

    def test_schema_creates_tables(self, monitor, engine):
        inspector = sa_inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"confluence_processed_comments", "confluence_last_check"}.issubset(tables)

    def test_is_processed_returns_false_initially(self, monitor):
        assert monitor.is_processed("page-123", "comment-456") is False

    def test_mark_and_check_processed(self, monitor):
        monitor.mark_processed("page-123", "comment-456")
        assert monitor.is_processed("page-123", "comment-456") is True

    def test_mark_processed_is_idempotent(self, monitor):
        monitor.mark_processed("page-123", "comment-456")
        monitor.mark_processed("page-123", "comment-456")  # Should not raise
        assert monitor.is_processed("page-123", "comment-456") is True

    def test_different_pages_are_independent(self, monitor):
        monitor.mark_processed("page-A", "comment-1")
        assert monitor.is_processed("page-A", "comment-1") is True
        assert monitor.is_processed("page-B", "comment-1") is False

    def test_get_last_check_time_defaults_to_recent_past(self, monitor):
        result = monitor.get_last_check_time()
        assert isinstance(result, datetime)
        assert result <= datetime.now()

    def test_set_and_get_last_check_time(self, monitor):
        now = datetime.now().replace(microsecond=0)
        monitor.set_last_check_time(now)
        retrieved = monitor.get_last_check_time()
        assert abs((retrieved - now).total_seconds()) < 2

    def test_set_last_check_time_updates_existing(self, monitor):
        t1 = datetime.now() - timedelta(hours=1)
        t2 = datetime.now()
        monitor.set_last_check_time(t1)
        monitor.set_last_check_time(t2)
        retrieved = monitor.get_last_check_time()
        assert (retrieved - t1).total_seconds() > 0
