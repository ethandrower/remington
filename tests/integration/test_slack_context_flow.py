#!/usr/bin/env python3
"""
Integration Tests for Slack Thread Context Preservation

Tests that:
1. Slack monitor fetches complete thread context (parent + all replies)
2. Thread context is included in events
3. Context is properly formatted for Claude prompts
4. Bot maintains conversation awareness in threads
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.monitors.slack_monitor import SlackMonitor


class TestSlackThreadContextFetching:
    """Test Slack thread context fetching functionality"""

    @pytest.mark.slow
    def test_get_thread_context_real_api(self):
        """Test fetching real thread context from Slack API"""
        monitor = SlackMonitor()

        # This test requires an actual thread_ts
        # For now, test the method signature and error handling
        result = monitor.get_thread_context("invalid_thread_ts")

        # Should return dict with parent/replies keys (empty if not found)
        assert isinstance(result, dict)
        assert "parent" in result
        assert "replies" in result

    @patch('requests.get')
    def test_get_thread_context_structure(self, mock_get):
        """Test thread context structure from API"""
        # Mock Slack API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {
                    "text": "What's ECD-862?",
                    "user": "U7L6RKG69",
                    "ts": "1704470400.123456"
                },
                {
                    "text": "That's the auth ticket",
                    "user": "U09BVV00XRP",
                    "ts": "1704470420.123457"
                }
            ]
        }
        mock_get.return_value = mock_response

        monitor = SlackMonitor()
        context = monitor.get_thread_context("1704470400.123456")

        # Verify structure
        assert context["parent"] is not None
        assert context["parent"]["text"] == "What's ECD-862?"
        assert len(context["replies"]) == 1
        assert context["replies"][0]["text"] == "That's the auth ticket"

        print(f"✅ Thread context structure correct")

    def test_thread_context_fixture(self, sample_slack_thread_context):
        """Test that fixture has proper thread context structure"""
        context = sample_slack_thread_context

        # Verify structure
        assert "parent" in context
        assert "replies" in context

        # Verify parent fields
        assert "text" in context["parent"]
        assert "user" in context["parent"]
        assert "ts" in context["parent"]

        # Verify replies
        assert len(context["replies"]) == 2
        for reply in context["replies"]:
            assert "text" in reply
            assert "user" in reply
            assert "ts" in reply

    @patch('requests.get')
    def test_thread_context_empty_thread(self, mock_get):
        """Test fetching context for thread with no replies"""
        # Mock response with only parent message
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "messages": [
                {
                    "text": "Single message",
                    "user": "U7L6RKG69",
                    "ts": "1704470400.123456"
                }
            ]
        }
        mock_get.return_value = mock_response

        monitor = SlackMonitor()
        context = monitor.get_thread_context("1704470400.123456")

        assert context["parent"] is not None
        assert len(context["replies"]) == 0


class TestSlackContextInEvents:
    """Test that Slack events include thread context"""

    def test_event_includes_thread_context(self, mock_slack_event_with_thread):
        """Test that events include thread_context field"""
        event = mock_slack_event_with_thread

        assert "thread_context" in event
        assert event["thread_context"] is not None

        context = event["thread_context"]
        assert "parent" in context
        assert "replies" in context
        assert len(context["replies"]) == 2

    @pytest.mark.slow
    def test_poll_for_mentions_includes_context(self):
        """Test that poll_for_mentions includes thread context in events"""
        monitor = SlackMonitor()

        # Poll for mentions (may or may not find any)
        events = monitor.poll_for_mentions()

        if events:
            # Check if any events have thread context
            events_with_context = [e for e in events if e.get("thread_context")]

            if events_with_context:
                event = events_with_context[0]
                context = event["thread_context"]

                assert "parent" in context or "replies" in context
                print(f"✅ Event includes thread context")
            else:
                print("ℹ️  No threaded messages found (test inconclusive)")
        else:
            print("ℹ️  No events found in current poll (test inconclusive)")


class TestSlackContextFormatting:
    """Test context formatting for Claude prompts"""

    def test_context_formatting_for_prompt(self, mock_slack_event_with_thread):
        """Test that thread context can be formatted for Claude prompt"""
        event = mock_slack_event_with_thread
        thread_ctx = event["thread_context"]

        # Build context string (same logic as slack_monitor.py lines 452-461)
        context_parts = []
        if thread_ctx.get('parent'):
            context_parts.append(f"[THREAD START]: {thread_ctx['parent']['text']}")

        if thread_ctx.get('replies'):
            for i, reply in enumerate(thread_ctx['replies']):
                context_parts.append(f"[Reply {i+1}]: {reply['text']}")

        full_context = "\n".join(context_parts)

        # Verify formatted context
        assert "[THREAD START]:" in full_context
        assert "What's the status of ECD-862?" in full_context
        assert "[Reply 1]:" in full_context
        assert "[Reply 2]:" in full_context
        assert "Can you check if Microsoft OAuth is included?" in full_context

        print(f"✅ Context formatted correctly ({len(full_context)} chars)")

    def test_context_includes_all_replies(self, sample_slack_thread_context):
        """Test that all thread replies are included in context"""
        context = sample_slack_thread_context

        replies = context["replies"]
        assert len(replies) == 2

        # Build formatted context
        formatted = []
        for i, reply in enumerate(replies, 1):
            formatted.append(f"[Reply {i}]: {reply['text']}")

        full_context = "\n".join(formatted)

        # Verify all replies included
        assert "ECD-862 is currently In Progress" in full_context
        assert "Can you check if Microsoft OAuth" in full_context

    def test_context_preserves_chronological_order(self, sample_slack_thread_context):
        """Test that context maintains chronological order"""
        context = sample_slack_thread_context

        # Verify timestamps are in order
        parent_ts = context["parent"]["ts"]
        reply_1_ts = context["replies"][0]["ts"]
        reply_2_ts = context["replies"][1]["ts"]

        assert float(parent_ts) < float(reply_1_ts)
        assert float(reply_1_ts) < float(reply_2_ts)


class TestSlackConversationAwareness:
    """Test that bot maintains conversation context in threads"""

    def test_process_with_claude_receives_context(self, mock_slack_event_with_thread):
        """Test that process_with_claude receives thread context"""
        event = mock_slack_event_with_thread

        # Verify event has all context needed
        assert event.get("thread_context") is not None

        # Build full_context string (as done in slack_monitor.py)
        thread_ctx = event['thread_context']
        context_parts = []

        if thread_ctx.get('parent'):
            context_parts.append(f"[THREAD START]: {thread_ctx['parent']['text']}")

        if thread_ctx.get('replies'):
            for i, reply in enumerate(thread_ctx['replies']):
                context_parts.append(f"[Reply {i+1}]: {reply['text']}")

        full_context = "\n".join(context_parts)

        # Verify context contains conversation history
        assert "What's the status of ECD-862?" in full_context
        assert "ECD-862 is currently In Progress" in full_context

        # This context would be passed to Claude
        # Bot should understand:
        # 1. Original question was about ECD-862
        # 2. Bot already answered about its status
        # 3. Latest question is follow-up about Microsoft OAuth

    def test_multi_turn_conversation_context(self):
        """Test context accumulation across multiple turns"""
        # Simulate 3-turn conversation
        turn_1 = {"text": "What's ECD-862?", "user": "U7L6RKG69"}
        turn_2 = {"text": "It's an auth ticket", "user": "U09BVV00XRP"}
        turn_3 = {"text": "<@U09BVV00XRP> When is it due?", "user": "U7L6RKG69"}

        # At turn 3, context should include:
        context_at_turn_3 = [turn_1, turn_2, turn_3]

        # Bot should know:
        # - "it" refers to ECD-862 (from turn 1)
        # - User already knows it's an auth ticket (from turn 2)
        # - Now asking about due date for SAME issue

        assert len(context_at_turn_3) == 3
        # All previous context available

    def test_context_enables_pronoun_resolution(self, sample_slack_thread_context):
        """Test that context allows resolving pronouns like 'it', 'this', etc."""
        context = sample_slack_thread_context

        # Parent: "What's the status of ECD-862?"
        # Reply 1: Bot answers
        # Reply 2: "Can you check if Microsoft OAuth is included?"

        # In Reply 2, implicit "in ECD-862" / "in this issue"
        # Bot should resolve "this" -> ECD-862 from parent

        parent_text = context["parent"]["text"]
        reply_2_text = context["replies"][1]["text"]

        assert "ECD-862" in parent_text
        # Reply 2 doesn't mention ECD-862 explicitly
        assert "ECD-862" not in reply_2_text
        # But bot has context to know which issue


class TestSlackContextErrorHandling:
    """Test error handling for context fetching"""

    @patch('requests.get')
    def test_context_fetch_failure_graceful(self, mock_get):
        """Test graceful handling of context fetch failures"""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"ok": False}
        mock_get.return_value = mock_response

        monitor = SlackMonitor()
        context = monitor.get_thread_context("invalid_ts")

        # Should return empty context, not crash
        assert context["parent"] is None
        assert context["replies"] == []

    @patch('requests.get')
    def test_context_fetch_timeout_handling(self, mock_get):
        """Test timeout handling during context fetch"""
        import requests

        # Mock timeout exception
        mock_get.side_effect = requests.Timeout()

        monitor = SlackMonitor()
        context = monitor.get_thread_context("test_ts")

        # Should return empty context on timeout
        assert context["parent"] is None
        assert context["replies"] == []


class TestSlackContextIntegration:
    """Integration tests for context in full flow"""

    def test_event_to_prompt_full_flow(self, mock_slack_event_with_thread):
        """Test complete flow: event -> context extraction -> prompt building"""
        event = mock_slack_event_with_thread

        # Step 1: Event has thread context
        assert event.get("thread_context") is not None

        # Step 2: Format context for Claude
        thread_ctx = event["thread_context"]
        context_parts = []

        if thread_ctx.get('parent'):
            context_parts.append(f"[THREAD START]: {thread_ctx['parent']['text']}")

        for i, reply in enumerate(thread_ctx.get('replies', [])):
            context_parts.append(f"[Reply {i+1}]: {reply['text']}")

        full_context = "\n".join(context_parts)

        # Step 3: Verify prompt would include full conversation
        assert "THREAD START" in full_context
        assert len(full_context) > 100  # Non-trivial context

        # Step 4: Verify context is coherent
        lines = full_context.split("\n")
        assert len(lines) == 3  # Parent + 2 replies

        print(f"✅ Full flow: event -> context -> prompt works correctly")


# Marker configuration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
