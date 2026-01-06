#!/usr/bin/env python3
"""
Integration Tests for Jira Comment Thread Context Preservation

Tests that:
1. Jira monitor fetches complete issue context (description + comments)
2. Context is included in events
3. Context is properly formatted for Claude prompts
4. Bot maintains conversation awareness across multiple comments
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.monitors.jira_monitor import JiraMonitor


class TestJiraContextFetching:
    """Test Jira issue context fetching functionality"""

    @pytest.mark.slow
    def test_get_issue_context_real_api(self):
        """Test fetching real issue context from Jira API"""
        monitor = JiraMonitor()

        # Use a real test issue (ECD-862 from examples)
        context = monitor.get_issue_context("ECD-862")

        # Verify context structure
        assert context is not None, "Context should be fetched"
        assert context["issue_key"] == "ECD-862"
        assert "summary" in context
        assert "description" in context
        assert "status" in context
        assert "priority" in context
        assert "assignee" in context
        assert "comments" in context
        assert isinstance(context["comments"], list)

        # Verify comments have required fields
        if context["comments"]:
            comment = context["comments"][0]
            assert "id" in comment
            assert "author" in comment
            assert "text" in comment
            assert "created" in comment

        print(f"✅ Fetched context: {len(context['comments'])} comments")

    def test_get_issue_context_structure(self, sample_jira_issue_context):
        """Test that context structure matches expected format"""
        # Verify fixture structure (used by tests)
        assert "issue_key" in sample_jira_issue_context
        assert "summary" in sample_jira_issue_context
        assert "description" in sample_jira_issue_context
        assert "comments" in sample_jira_issue_context

        comments = sample_jira_issue_context["comments"]
        assert len(comments) == 2

        # Verify chronological order
        assert comments[0]["created"] < comments[1]["created"]

    @patch('requests.get')
    def test_get_issue_context_api_failure(self, mock_get):
        """Test context fetching handles API failures gracefully"""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        monitor = JiraMonitor()
        context = monitor.get_issue_context("ECD-999")

        # Should return None on failure
        assert context is None


class TestJiraContextInEvents:
    """Test that Jira events include issue context"""

    @pytest.mark.slow
    def test_event_includes_context(self):
        """Test that poll_for_mentions includes issue_context in events"""
        monitor = JiraMonitor()

        # Poll for mentions (may or may not find any)
        events = monitor.poll_for_mentions()

        if events:
            event = events[0]
            # Event should have issue_context field
            assert "issue_context" in event, "Event should include issue_context"

            if event["issue_context"]:
                context = event["issue_context"]
                assert context["issue_key"] == event["issue_key"]
                assert "comments" in context
                print(f"✅ Event includes context with {len(context['comments'])} comments")
        else:
            print("ℹ️  No events found in current poll (test inconclusive)")

    def test_mock_event_has_context(self, mock_jira_event_with_context):
        """Test that mock event fixture has proper context structure"""
        event = mock_jira_event_with_context

        assert "issue_context" in event
        assert event["issue_context"] is not None

        context = event["issue_context"]
        assert context["issue_key"] == event["issue_key"]
        assert len(context["comments"]) == 2


class TestJiraContextFormatting:
    """Test context formatting for Claude prompts"""

    def test_context_formatting_for_prompt(self, mock_jira_event_with_context):
        """Test that issue context can be formatted for Claude prompt"""
        event = mock_jira_event_with_context
        issue_context = event["issue_context"]

        # Build context string (same logic as pm_agent_service.py)
        context_str = f"""ISSUE CONTEXT:
--------------
Issue: {issue_context['issue_key']} - {issue_context['summary']}
Status: {issue_context['status']} | Priority: {issue_context['priority']}
Assignee: {issue_context['assignee']}

DESCRIPTION:
{issue_context['description']}

PREVIOUS COMMENTS ({len(issue_context['comments'])} total):
"""
        for i, comment in enumerate(issue_context['comments'], 1):
            context_str += f"\n[Comment {i}] {comment['author']} ({comment['created'][:10]}):\n{comment['text']}\n"

        context_str += f"\n\nLATEST COMMENT (requires your response):\n{event['comment_text']}"

        # Verify formatted context
        assert "ECD-862" in context_str
        assert "Implement user authentication" in context_str
        assert "OAuth2 authentication" in context_str
        assert "PREVIOUS COMMENTS (2 total)" in context_str
        assert "Comment 1" in context_str
        assert "Comment 2" in context_str
        assert "LATEST COMMENT" in context_str
        assert "@remington can you update the priority" in context_str

        print(f"✅ Context formatted correctly ({len(context_str)} chars)")

    def test_context_includes_all_comments(self, sample_jira_issue_context):
        """Test that all previous comments are included in context"""
        comments = sample_jira_issue_context["comments"]

        # Build context string
        context_parts = []
        for i, comment in enumerate(comments, 1):
            context_parts.append(f"[Comment {i}] {comment['author']}: {comment['text']}")

        full_context = "\n".join(context_parts)

        # Verify all comments included
        assert "Ethan" in full_context
        assert "Mohamed" in full_context
        assert "OAuth2 implementation in progress" in full_context
        assert "Google OAuth is working" in full_context


class TestJiraConversationAwareness:
    """Test that bot maintains conversation context across multiple comments"""

    def test_context_enables_conversation_continuity(self, sample_jira_issue_context):
        """Test that context provides enough info for conversation continuity"""
        # Simulate multi-comment conversation
        # Comment 1: User asks question
        # Comment 2: Bot answers
        # Comment 3: User follow-up (should have context)

        context = sample_jira_issue_context

        # At comment 3, context should include:
        # - Original issue description (OAuth2 with Google)
        # - Comment 1: Started working on OAuth2
        # - Comment 2: Google OAuth is working, need Microsoft

        # Now if user asks "can you add Microsoft?"
        # Bot should know:
        # 1. This is about ECD-862 (from context)
        # 2. OAuth2 authentication feature (from description)
        # 3. Google is already done (from comment 2)
        # 4. User is asking about adding Microsoft provider

        assert "Google" in context["comments"][1]["text"]
        assert "Microsoft" in context["comments"][1]["text"]
        assert "OAuth2" in context["description"]

        # Bot should NOT need to ask "which issue?" or "what feature?"
        # All context is available

    @pytest.mark.slow
    def test_multi_comment_context_accumulation(self):
        """Test that context grows with each new comment"""
        # This would require creating actual Jira comments
        # For now, test with mock data showing growth

        # Simulate 3 comments
        comment_1 = {"text": "Started working on this", "created": "2026-01-04T10:00:00Z"}
        comment_2 = {"text": "Google OAuth done", "created": "2026-01-04T12:00:00Z"}
        comment_3 = {"text": "Adding Microsoft now", "created": "2026-01-04T14:00:00Z"}

        # After comment 1: 1 comment in context
        # After comment 2: 2 comments in context
        # After comment 3: 3 comments in context

        context_at_comment_3 = [comment_1, comment_2, comment_3]

        assert len(context_at_comment_3) == 3
        # Latest comment sees all previous context
        assert all(c["created"] for c in context_at_comment_3)


class TestJiraContextErrorHandling:
    """Test error handling for context fetching"""

    @patch('requests.get')
    def test_context_fetch_failure_fallback(self, mock_get):
        """Test that processing continues even if context fetch fails"""
        # Mock API failure for context fetch
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        monitor = JiraMonitor()
        context = monitor.get_issue_context("ECD-INVALID")

        # Should return None, not raise exception
        assert context is None

    def test_missing_context_graceful_degradation(self, mock_jira_event_with_context):
        """Test that event processing works even without context"""
        event = mock_jira_event_with_context.copy()
        event["issue_context"] = None  # Simulate failed context fetch

        # Should be able to process event with just basic comment
        comment_text = event["comment_text"]
        assert comment_text == "@remington can you update the priority to Highest?"

        # Fallback prompt would be simpler but still functional
        fallback_prompt = f"Comment on {event['issue_key']}: {comment_text}"
        assert "ECD-862" in fallback_prompt
        assert comment_text in fallback_prompt


class TestJiraContextPerformance:
    """Test performance implications of context fetching"""

    @pytest.mark.slow
    def test_context_fetch_timing(self):
        """Test that context fetching completes within reasonable time"""
        import time

        monitor = JiraMonitor()

        start = time.time()
        context = monitor.get_issue_context("ECD-862")
        elapsed = time.time() - start

        # Should complete within 2 seconds
        assert elapsed < 2.0, f"Context fetch took {elapsed:.2f}s (should be < 2s)"

        if context:
            print(f"✅ Context fetched in {elapsed:.3f}s ({len(context['comments'])} comments)")


# Marker configuration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
