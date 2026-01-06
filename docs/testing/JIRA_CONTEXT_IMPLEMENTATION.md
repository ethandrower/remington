# Jira Comment Thread Context - Implementation Guide

**Priority:** CRITICAL
**Effort:** ~4 hours
**Status:** NOT IMPLEMENTED

## Problem Statement

Currently, when the bot receives a Jira mention, it only sees **that single comment** - no issue description, no previous comments, no conversation context.

**Example Problem:**
```
Issue: ECD-862 "Implement user authentication"
Description: "Add OAuth2 authentication using Google provider"

Comment 1 (User): "@remington what's the status of this?"
Bot Reply: "ECD-862 is In Progress"

Comment 2 (User): "@remington can you add Microsoft as a provider too?"
Bot Reply: "Which issue do you want me to update? What provider should I add?"
            ^^^ WRONG! Bot should know we're talking about ECD-862 OAuth
```

## Required Changes

### 1. Add `get_issue_context()` Method

**File:** `src/monitors/jira_monitor.py`
**Location:** After `_is_service_account_mentioned()` method (around line 258)

```python
def get_issue_context(self, issue_key: str) -> Dict[str, Any]:
    """
    Fetch complete issue context: summary, description, and all comments

    Returns:
        {
            "issue_key": "ECD-862",
            "summary": "Implement user authentication",
            "description": "Add OAuth2 authentication...",
            "status": "In Progress",
            "priority": "High",
            "assignee": "Mohamed",
            "comments": [
                {
                    "id": "12345",
                    "author": "Ethan",
                    "text": "What's the status?",
                    "created": "2026-01-04T10:30:00Z"
                },
                {
                    "id": "12346",
                    "author": "Remington",
                    "text": "Working on OAuth implementation",
                    "created": "2026-01-04T11:00:00Z"
                }
            ]
        }
    """
    try:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

        # Fetch issue with expanded fields
        response = requests.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}",
            headers=headers,
            params={
                "fields": "summary,description,status,priority,assignee,comment",
                "expand": "renderedFields"
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"⚠️ Failed to fetch issue context for {issue_key}: {response.status_code}")
            return None

        data = response.json()
        fields = data.get("fields", {})

        # Extract all comments in chronological order
        comments = []
        for comment in fields.get("comment", {}).get("comments", []):
            comments.append({
                "id": comment["id"],
                "author": comment.get("author", {}).get("displayName", "Unknown"),
                "author_id": comment.get("author", {}).get("accountId", ""),
                "text": self._extract_comment_text(comment.get("body", {})),
                "created": comment.get("created", "")
            })

        return {
            "issue_key": issue_key,
            "summary": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "priority": fields.get("priority", {}).get("name", "None"),
            "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
            "comments": comments
        }

    except Exception as e:
        print(f"❌ Error fetching issue context for {issue_key}: {e}")
        return None
```

### 2. Update `_filter_new_mentions()` to Include Context

**File:** `src/monitors/jira_monitor.py`
**Location:** Line 197-211 (inside the event creation)

**BEFORE:**
```python
new_events.append({
    "source": "jira",
    "type": "comment_mention",
    "issue_key": issue_key,
    "issue_summary": fields.get("summary", ""),
    "issue_status": fields.get("status", {}).get("name", ""),
    "issue_priority": fields.get("priority", {}).get("name", ""),
    "comment_id": comment_id,
    "comment_text": comment_text,
    "author": comment.get("author", {}).get("displayName", "unknown"),
    "author_id": comment.get("author", {}).get("accountId", ""),
    "timestamp": comment.get("created", ""),
    "issue_url": f"https://citemed.atlassian.net/browse/{issue_key}",
})
```

**AFTER:**
```python
# Fetch complete issue context
issue_context = self.get_issue_context(issue_key)

new_events.append({
    "source": "jira",
    "type": "comment_mention",
    "issue_key": issue_key,
    "issue_summary": fields.get("summary", ""),
    "issue_status": fields.get("status", {}).get("name", ""),
    "issue_priority": fields.get("priority", {}).get("name", ""),
    "comment_id": comment_id,
    "comment_text": comment_text,
    "author": comment.get("author", {}).get("displayName", "unknown"),
    "author_id": comment.get("author", {}).get("accountId", ""),
    "timestamp": comment.get("created", ""),
    "issue_url": f"https://citemed.atlassian.net/browse/{issue_key}",
    "issue_context": issue_context,  # NEW - Include full context
})
```

### 3. Update Prompt Generation to Use Context

**File:** `src/pm_agent_service.py`
**Location:** Around line 370-377 (Jira event processing)

**Find this section:**
```python
print(f"Issue: {event['issue_key']}")
comment_text = event.get('comment_text', event.get('text', ''))
comment_preview = comment_text[:100]
print(f"Comment: {comment_preview}...")
```

**Add after:**
```python
# Format issue context for Claude prompt
issue_context = event.get('issue_context')
if issue_context:
    context_str = f"""
ISSUE CONTEXT:
--------------
Issue: {issue_context['issue_key']} - {issue_context['summary']}
Status: {issue_context['status']} | Priority: {issue_context['priority']}
Assignee: {issue_context['assignee']}

DESCRIPTION:
{issue_context['description']}

PREVIOUS COMMENTS ({len(issue_context['comments'])} total):
"""
    for i, comment in enumerate(issue_context['comments'], 1):
        context_str += f"\n[Comment {i}] {comment['author']} ({comment['created']}):\n{comment['text']}\n"

    context_str += f"\n\nLATEST COMMENT (requires your response):\n{comment_text}"
else:
    # Fallback if context fetch failed
    context_str = f"Comment on {event['issue_key']}: {comment_text}"

print(f"\n📜 Issue context prepared ({len(issue_context.get('comments', []))} previous comments)")
```

**Then pass context to orchestrator:**
```python
# OLD: Simple comment text
result = self.orchestrator.invoke_jira(
    event['issue_key'],
    comment_text
)

# NEW: Full context
result = self.orchestrator.invoke_jira(
    event['issue_key'],
    context_str  # Use formatted context instead of just comment_text
)
```

### 4. Update Orchestrator Prompt Generation (Optional Enhancement)

**File:** `src/orchestration/claude_code_orchestrator.py`
**Location:** `_build_jira_prompt()` method

Add context awareness instructions:
```python
def _build_jira_prompt(self, issue_key: str, comment_text: str, **kwargs):
    """Build prompt for Jira mention with context awareness"""

    # Check if comment_text includes full context (multi-line with ISSUE CONTEXT header)
    has_full_context = "ISSUE CONTEXT:" in comment_text

    prompt = f"""You are responding to a Jira comment mention.

{comment_text}

IMPORTANT CONTEXT AWARENESS:
- You have been given the complete issue context above
- You can see the issue description and ALL previous comments
- Use this context to provide informed, relevant responses
- Don't ask for information that's already in the context
- Reference previous comments when relevant

TOOLS AVAILABLE:
- python -m src.tools.jira.get_issue {issue_key}
- python -m src.tools.jira.edit_issue {issue_key} --summary "..." --description "..."
- python -m src.tools.jira.add_comment {issue_key} "your response text"
- python -m src.tools.jira.transition_issue {issue_key} --status "In Progress"

RESPONSE GUIDELINES:
1. Acknowledge the full conversation context
2. Provide specific, actionable responses
3. Use Jira tools to take actions if needed
4. Reference previous comments when relevant (e.g., "As mentioned in the earlier comment...")

Please respond to the latest comment while being aware of the full issue context.
"""
    return prompt
```

## Testing the Implementation

### Manual Test

1. **Create test issue with comments:**
```bash
# Using Jira UI or API, create:
Issue: ECD-999 "Test context feature"
Description: "This is a test issue for context awareness"

Comment 1: "Initial comment about this feature"
Comment 2: "@remington what's the status?"
# Bot should reply with context awareness

Comment 3: "@remington can you update the priority to High?"
# Bot should know which issue without asking
```

2. **Check bot logs:**
```bash
# Should see:
📜 Issue context prepared (2 previous comments)
🤖 Processing Jira mention with Claude Code...
```

3. **Verify response:**
- Bot should NOT ask "which issue?"
- Bot should reference issue description if relevant
- Bot should show awareness of previous comments

### Automated Test

**File:** `tests/integration/test_jira_context_flow.py`

```python
import pytest
from src.monitors.jira_monitor import JiraMonitor

def test_jira_get_issue_context():
    """Test fetching complete issue context"""
    monitor = JiraMonitor()

    # Use real test issue (or mock API)
    context = monitor.get_issue_context("ECD-862")

    assert context is not None
    assert context["issue_key"] == "ECD-862"
    assert "summary" in context
    assert "description" in context
    assert "comments" in context
    assert isinstance(context["comments"], list)

    # Verify comments are in chronological order
    if len(context["comments"]) > 1:
        assert context["comments"][0]["created"] < context["comments"][1]["created"]

@pytest.mark.slow
def test_jira_context_in_event():
    """Test that events include issue context"""
    monitor = JiraMonitor()

    events = monitor.poll_for_mentions()

    if events:
        event = events[0]
        assert "issue_context" in event

        context = event["issue_context"]
        assert context["issue_key"] == event["issue_key"]
        assert "comments" in context

@pytest.mark.slow
def test_jira_multi_comment_conversation():
    """Test bot maintains context across multiple comments"""
    # This test requires real Jira interaction or sophisticated mocking
    # See INTEGRATION_TEST_PLAN.md Scenario 1.5 for full implementation
    pass
```

## Verification Checklist

- [ ] `get_issue_context()` method added to jira_monitor.py
- [ ] Method fetches summary, description, status, priority, assignee
- [ ] Method fetches ALL comments in chronological order
- [ ] `_filter_new_mentions()` includes `issue_context` in events
- [ ] `pm_agent_service.py` formats context for Claude prompt
- [ ] Orchestrator prompt includes context awareness instructions
- [ ] Manual test confirms bot uses context (doesn't ask redundant questions)
- [ ] Automated tests added to verify context fetching
- [ ] Bot logs show "Issue context prepared (N previous comments)"

## Expected Impact

### Before Implementation
```
Comment 1: "@remington what's the priority of this?"
Bot: "The priority is High"

Comment 2: "@remington can you change it to Highest?"
Bot: "Which issue do you want me to update?" ❌
```

### After Implementation
```
Comment 1: "@remington what's the priority of this?"
Bot: "The priority of ECD-862 (Implement user authentication) is High"

Comment 2: "@remington can you change it to Highest?"
Bot: "I've updated ECD-862 priority to Highest" ✅
```

## Rollback Plan

If implementation causes issues:

1. **Quick rollback:**
   ```bash
   git checkout HEAD~1 -- src/monitors/jira_monitor.py src/pm_agent_service.py
   ```

2. **Disable context feature:**
   ```python
   # In _filter_new_mentions(), comment out:
   # "issue_context": self.get_issue_context(issue_key),

   # Add fallback:
   "issue_context": None,
   ```

## Performance Considerations

- **Extra API Call:** Adds 1 Jira API call per mention (to fetch full issue)
- **Rate Limiting:** Jira has rate limits (~100 requests/min)
- **Mitigation:**
  - Cache issue context for 5 minutes (optional)
  - Context fetch happens AFTER deduplication check
  - Only fetches for new mentions (not reprocessed)

**Estimated Impact:** +200-500ms per mention (acceptable)
