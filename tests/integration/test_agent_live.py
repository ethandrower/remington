"""
Integration tests for the LangGraph agent — uses REAL APIs.

These tests make actual calls to:
  - Anthropic API (Claude)
  - Jira REST API

Run them only when you have valid credentials and want to verify end-to-end:

    pytest tests/integration/test_agent_live.py -m slow -v

Skip them in fast CI runs:

    pytest -m "not slow"

Requirements:
  - ANTHROPIC_API_KEY (or ANTRHOPIC_API_KEY) in .env
  - ATLASSIAN_SERVICE_ACCOUNT_TOKEN, ATLASSIAN_SERVICE_ACCOUNT_EMAIL in .env
  - ATLASSIAN_PROJECT_KEY, JIRA_INSTANCE_URL in .env
"""

import pytest
import time


@pytest.mark.slow
class TestAgentLive:
    """End-to-end tests against real Jira + Claude APIs."""

    def test_agent_responds_to_simple_question(self):
        """Agent should return a non-empty string without crashing."""
        from src.agents.conversation_agent import run_agent

        result = run_agent(
            thread_ts=f"integration-test-{time.time()}",
            channel="C_TEST",
            author="Integration Test",
            message="What Jira project key are you configured for?",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_agent_can_search_jira(self):
        """Agent should be able to call search_jira and return results."""
        from src.agents.conversation_agent import run_agent

        result = run_agent(
            thread_ts=f"integration-search-{time.time()}",
            channel="C_TEST",
            author="Integration Test",
            message="Search for any 3 open tickets in the current sprint and list their keys.",
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Response should contain at least one ticket key pattern (e.g. ECD-123)
        import re
        has_ticket_key = bool(re.search(r"[A-Z]+-\d+", result))
        assert has_ticket_key, f"Expected ticket key in response, got: {result}"

    def test_agent_remembers_context_across_turns(self):
        """Two messages in the same thread should share conversation history."""
        from src.agents.conversation_agent import run_agent

        thread_ts = f"integration-memory-{time.time()}"

        # First message: ask something with a memorable answer
        run_agent(
            thread_ts=thread_ts,
            channel="C_TEST",
            author="Integration Test",
            message="Remember the number 42 for me.",
        )

        # Second message: reference the prior turn
        second_result = run_agent(
            thread_ts=thread_ts,
            channel="C_TEST",
            author="Integration Test",
            message="What number did I ask you to remember?",
        )

        assert "42" in second_result, (
            f"Expected agent to recall '42' from prior turn, got: {second_result}"
        )
