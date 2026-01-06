# Integration Test Plan - PM Agent Service

**Date:** 2026-01-05
**Status:** DRAFT
**Priority:** HIGH

## Executive Summary

This document outlines a comprehensive integration testing strategy for the PM Agent Service, focusing on three critical areas:

1. **Conversational Context Preservation** - Ensuring thread/comment context is maintained across all platforms
2. **Detect → Respond → Mark Flow** - Preventing double replies and ensuring proper state management
3. **Major Feature Testing** - End-to-end testing of PR review, Jira Q&A, and organization features

## Current Test Coverage Analysis

### Existing Tests (1,900+ lines across 10 files)

#### ✅ What We Have

**1. test_orchestrator_integration.py (353 lines)**
- ✅ Claude Code subprocess invocation
- ✅ Tool availability and execution
- ✅ Prompt generation for Jira
- ✅ Basic error handling
- ❌ NO thread context preservation tests
- ❌ NO conversational flow tests

**2. test_polling_monitors.py (398 lines)**
- ✅ Slack/Jira/Bitbucket real API integration
- ✅ Basic deduplication (no reprocessing of same message)
- ✅ Database state tracking
- ❌ NO full detect→respond→mark flow test
- ❌ NO double-reply prevention verification

**3. test_sla_deduplication.py (119 lines)**
- ✅ SLA alert deduplication logic
- ✅ Escalation level change detection
- ✅ Thread tracking with `slack_thread_ts`
- ❌ NO integration with actual response flow

**4. test_jira_tools.py (405 lines)**
- ✅ Individual Jira tool execution
- ✅ JQL query validation
- ✅ Error handling for invalid inputs
- ❌ NO conversation context tests

#### ❌ What We're Missing

### Gap Analysis by User Concern

#### Concern 1: Conversational Context Preservation

**Current State:**
- ✅ Slack monitor has `get_thread_context()` method (slack_monitor.py:118-162)
- ✅ Thread context passed in event dict (`thread_context` key)
- ✅ Context formatted for Claude prompt (slack_monitor.py:452-461)
- ❌ NO tests verify context is correctly passed
- ❌ NO tests verify Claude receives full history
- ❌ NO tests verify responses use context appropriately

**Jira-Specific Gaps:**
- ❌ Jira monitor does NOT fetch comment thread context
- ❌ Only extracts single comment text (jira_monitor.py:191)
- ❌ No previous comments or issue description included
- ❌ CRITICAL GAP: Jira has no conversation context feature!

#### Concern 2: Detect → Respond → Mark Flow

**Current State:**
- ✅ Slack marks messages as processed BEFORE sending acknowledgment (slack_monitor.py:223, 331)
- ✅ `is_processed()` check prevents reprocessing (slack_monitor.py:218, 326)
- ✅ Database tracking in place
- ❌ NO end-to-end test of full flow
- ❌ NO test verifying only ONE reply is sent
- ❌ NO test for race conditions (multiple polls before DB write)

**Jira-Specific Issues:**
- ✅ Jira marks comments as processed on detection (jira_monitor.py:214)
- ❌ NO separate "replied" status after response sent
- ❌ If response fails, comment never re-attempted
- ❌ No test for this gap!

#### Concern 3: Major Feature Integration Testing

**Current State:**
- ✅ Basic Claude Code invocation test exists
- ✅ Tool execution verified
- ❌ NO complete PR review workflow test
- ❌ NO Jira Q&A workflow test
- ❌ NO organization/planning workflow test
- ❌ NO multi-step feature tests

## Proposed Test Suite Structure

```
tests/
├── integration/
│   ├── test_conversational_context.py      # NEW - Thread context preservation
│   ├── test_slack_context_flow.py         # NEW - Slack-specific context tests
│   ├── test_jira_context_flow.py          # NEW - Jira comment context (to be built)
│   ├── test_reply_flow_e2e.py             # NEW - Complete detect→respond→mark
│   ├── test_no_double_replies.py          # NEW - Double-reply prevention
│   ├── test_pr_review_workflow.py         # NEW - Full PR review feature
│   ├── test_jira_qa_workflow.py           # NEW - Jira Q&A feature
│   ├── test_organization_workflow.py       # NEW - Planning/organization features
│   ├── test_sla_deduplication.py          # EXISTS - Keep as-is
│   └── test_orchestrator_integration.py    # EXISTS - Enhance with context tests
├── e2e/
│   └── test_multi_platform_flow.py        # NEW - Cross-platform workflows
└── conftest.py                             # Shared fixtures
```

## Detailed Test Scenarios

### 1. Conversational Context Preservation Tests

#### Test File: `tests/integration/test_slack_context_flow.py`

**Scenario 1.1: Thread Context Fetching**
```python
def test_slack_thread_context_fetching():
    """Verify thread context is fetched correctly"""
    # Setup: Create a thread with multiple messages
    # Action: Call get_thread_context(thread_ts)
    # Assert:
    #   - Parent message included
    #   - All replies included in order
    #   - Timestamps preserved
    #   - User IDs correct
```

**Scenario 1.2: Context Passed to Claude**
```python
def test_slack_context_passed_to_claude():
    """Verify full thread context reaches Claude prompt"""
    # Setup: Mock thread with 3 messages
    # Action: Trigger mention in thread
    # Assert:
    #   - process_with_claude() receives full_context parameter
    #   - Prompt contains all previous messages
    #   - Format: "[THREAD START]: msg1, [Reply 1]: msg2, [Reply 2]: msg3"
```

**Scenario 1.3: Contextual Response Generation**
```python
@pytest.mark.slow
def test_slack_contextual_response():
    """Verify Claude uses thread context in response"""
    # Setup: Thread with "What's ECD-123?" → Bot replies → "When is it due?"
    # Action: Send second question in thread
    # Assert:
    #   - Response references "this issue" (not asking which issue)
    #   - Response shows awareness of previous context
    #   - Response doesn't repeat information from earlier in thread
```

#### Test File: `tests/integration/test_jira_context_flow.py`

**Scenario 1.4: Jira Comment Thread Context (TO BE IMPLEMENTED)**
```python
def test_jira_fetch_issue_description_and_comments():
    """Verify Jira includes issue description + previous comments"""
    # Current State: NOT IMPLEMENTED
    # Needed Implementation:
    #   1. Fetch issue details (summary, description)
    #   2. Fetch ALL previous comments in chronological order
    #   3. Include in event['issue_context'] dict
    # Assert:
    #   - Issue description included
    #   - All previous comments included
    #   - Comments in chronological order
```

**Scenario 1.5: Jira Multi-Comment Conversation**
```python
@pytest.mark.slow
def test_jira_multi_comment_conversation():
    """Test bot maintains context across multiple Jira comments"""
    # Setup:
    #   1. User posts comment "@remington what's the status?"
    #   2. Bot replies with status
    #   3. User posts follow-up "@remington can you update the priority?"
    # Assert:
    #   - Bot understands "the priority" refers to same issue
    #   - Bot doesn't ask "which issue?"
    #   - Response shows context awareness
```

### 2. Detect → Respond → Mark Flow Tests

#### Test File: `tests/integration/test_reply_flow_e2e.py`

**Scenario 2.1: Complete Slack Flow**
```python
@pytest.mark.slow
def test_slack_complete_reply_flow():
    """Test complete flow: detect → respond → mark → verify no re-reply"""
    # Setup: Fresh database, mock Slack API
    # Step 1: Post message with @bot mention
    # Step 2: Poll for mentions
    # Assert: Event detected, is_processed=False
    # Step 3: Process event (triggers response)
    # Assert: Response sent to Slack
    # Step 4: Check database
    # Assert: Message marked as processed (ts in processed_messages table)
    # Step 5: Poll again immediately
    # Assert: is_processed=True, no event returned
    # Step 6: Verify Slack API
    # Assert: Only ONE message sent (no duplicate replies)
```

**Scenario 2.2: Race Condition Prevention**
```python
def test_slack_concurrent_polling_no_double_reply():
    """Test that concurrent polls don't cause double replies"""
    # Setup: Same message timestamp, two polling threads
    # Action: Start two poll_for_mentions() calls simultaneously
    # Assert:
    #   - Only ONE thread processes the message
    #   - Database INSERT OR IGNORE prevents duplicate marking
    #   - Only ONE response sent to Slack
    #   - Second thread sees is_processed=True
```

**Scenario 2.3: Failed Response Retry**
```python
def test_slack_failed_response_retry_logic():
    """Test behavior when response sending fails"""
    # Setup: Mock Slack API to fail first time, succeed second time
    # Action: Process mention, API fails
    # Assert:
    #   - Message still marked as processed (prevents infinite retries)
    #   - OR: Implement retry logic with exponential backoff
    #   - Document expected behavior
```

#### Test File: `tests/integration/test_no_double_replies.py`

**Scenario 2.4: Slack Double-Reply Prevention**
```python
def test_slack_no_double_reply_on_reprocess():
    """Verify no duplicate replies if same message reprocessed"""
    # Setup: Post message, process it, get response
    # Action: Clear last_processed_ts, poll again (simulates restart)
    # Assert:
    #   - Message detected in poll
    #   - is_processed() returns True
    #   - No new event generated
    #   - No second reply sent
```

**Scenario 2.5: Jira Double-Reply Prevention**
```python
def test_jira_no_double_reply_on_reprocess():
    """Verify Jira doesn't reply twice to same comment"""
    # Setup: Post Jira comment, process it
    # Action: Poll again
    # Assert:
    #   - Comment detected in API response
    #   - is_processed(issue_key, comment_id) returns True
    #   - No new event generated
    #   - No second comment added
```

**Scenario 2.6: Thread Reply Deduplication**
```python
def test_slack_thread_reply_no_duplicate():
    """Verify replies in threads don't get processed twice"""
    # Setup:
    #   1. Create thread (parent + 2 replies)
    #   2. Mention bot in reply #3
    # Action:
    #   1. Poll threads (poll_thread_replies)
    #   2. Process reply #3
    #   3. Poll threads again
    # Assert:
    #   - Reply #3 marked as processed
    #   - last_checked_ts updated for thread
    #   - Second poll skips reply #3
    #   - No duplicate response
```

### 3. Major Feature Integration Tests

#### Test File: `tests/integration/test_pr_review_workflow.py`

**Scenario 3.1: Complete PR Review Workflow**
```python
@pytest.mark.slow
def test_complete_pr_review_workflow():
    """Test full PR review: detect PR → analyze → comment → mark reviewed"""
    # Setup: Create test PR in Bitbucket
    # Step 1: Webhook/polling detects new PR
    # Assert: Event created with PR details
    # Step 2: Claude Code analyzes PR
    # Assert:
    #   - Git diff fetched
    #   - Code complexity analyzed
    #   - Review comments generated
    # Step 3: Post comments to Bitbucket
    # Assert:
    #   - Comments posted with line numbers
    #   - Overall review summary posted
    # Step 4: Mark PR as reviewed
    # Assert:
    #   - PR marked in database
    #   - No re-review on next poll
```

**Scenario 3.2: PR Review with Context**
```python
@pytest.mark.slow
def test_pr_review_with_ticket_context():
    """Test PR review includes Jira ticket context"""
    # Setup:
    #   - Create Jira ticket ECD-999
    #   - Create PR with branch "ECD-999-feature"
    # Action: Trigger PR review
    # Assert:
    #   - Bot fetches Jira ticket details
    #   - Review references ticket requirements
    #   - Comments mention ticket context
```

#### Test File: `tests/integration/test_jira_qa_workflow.py`

**Scenario 3.3: Jira Question-Answer Workflow**
```python
@pytest.mark.slow
def test_jira_question_answer_workflow():
    """Test bot answers Jira question using Claude Code"""
    # Setup: Post Jira comment "@remington what's the status of ECD-862?"
    # Step 1: Detect mention
    # Assert: Event created with question
    # Step 2: Claude Code processes question
    # Assert:
    #   - Uses src.tools.jira.get_issue to fetch ECD-862
    #   - Extracts status, assignee, summary
    # Step 3: Post answer to Jira
    # Assert:
    #   - Answer includes specific status
    #   - Answer formatted professionally
    #   - Comment posted successfully
```

**Scenario 3.4: Multi-Ticket Query**
```python
@pytest.mark.slow
def test_jira_multi_ticket_query():
    """Test bot handles questions about multiple tickets"""
    # Setup: "@remington compare ECD-100 and ECD-200"
    # Action: Process request
    # Assert:
    #   - Bot fetches both tickets
    #   - Comparison includes status, priority, assignee
    #   - Response is structured and clear
```

#### Test File: `tests/integration/test_organization_workflow.py`

**Scenario 3.5: Sprint Planning Feature**
```python
@pytest.mark.slow
def test_sprint_planning_workflow():
    """Test bot can create sprint plan"""
    # Setup: "@remington plan next sprint with ECD tickets"
    # Action: Process request
    # Assert:
    #   - Bot searches for unscheduled ECD tickets
    #   - Groups by priority/component
    #   - Generates sprint plan
    #   - Posts plan to Confluence or Slack
```

**Scenario 3.6: Ticket Organization**
```python
@pytest.mark.slow
def test_ticket_organization_workflow():
    """Test bot can organize/categorize tickets"""
    # Setup: "@remington categorize all open ECD bugs by severity"
    # Action: Process request
    # Assert:
    #   - Bot searches for open bugs
    #   - Analyzes severity/priority
    #   - Generates categorized report
    #   - Posts results
```

### 4. Cross-Platform Integration Tests

#### Test File: `tests/e2e/test_multi_platform_flow.py`

**Scenario 4.1: Slack → Jira → Slack Flow**
```python
@pytest.mark.slow
def test_slack_triggers_jira_update_reports_back():
    """Test request from Slack → action in Jira → report to Slack"""
    # Setup: Slack message "@remington create bug ticket for login issue"
    # Step 1: Detect Slack mention
    # Step 2: Claude Code creates Jira ticket
    # Assert: Ticket created with proper fields
    # Step 3: Bot replies to Slack with ticket key
    # Assert: "Created ECD-XXX: Login issue" posted to thread
```

**Scenario 4.2: Jira → Slack Notification Flow**
```python
@pytest.mark.slow
def test_jira_comment_triggers_slack_notification():
    """Test Jira mention triggers Slack notification"""
    # Setup: Jira comment "@remington escalate this to team"
    # Step 1: Detect Jira mention
    # Step 2: Claude Code analyzes issue
    # Step 3: Bot posts to Slack channel
    # Assert:
    #   - Slack message includes issue key, summary
    #   - Link to Jira ticket included
    #   - Posted to correct channel
```

## Implementation Priority

### Phase 1: Critical Gaps (Week 1)
1. ✅ `test_slack_context_flow.py` - Scenarios 1.1, 1.2, 1.3
2. ✅ `test_reply_flow_e2e.py` - Scenarios 2.1, 2.2
3. ✅ `test_no_double_replies.py` - Scenarios 2.4, 2.5, 2.6

### Phase 2: Feature Tests (Week 2)
4. ✅ `test_jira_qa_workflow.py` - Scenarios 3.3, 3.4
5. ✅ `test_jira_context_flow.py` - Scenarios 1.4, 1.5 (requires implementation)

### Phase 3: Advanced Features (Week 3)
6. ✅ `test_pr_review_workflow.py` - Scenarios 3.1, 3.2
7. ✅ `test_organization_workflow.py` - Scenarios 3.5, 3.6
8. ✅ `test_multi_platform_flow.py` - Scenarios 4.1, 4.2

## Test Fixtures and Utilities

### Shared Fixtures (`tests/conftest.py`)

```python
import pytest
from pathlib import Path
import sqlite3
import tempfile

@pytest.fixture
def fresh_slack_db():
    """Provide clean Slack state database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)

    # Initialize schema
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE processed_messages (
                ts TEXT PRIMARY KEY,
                channel TEXT,
                user_id TEXT,
                text TEXT,
                response TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE tracked_threads (
                thread_ts TEXT PRIMARY KEY,
                channel TEXT,
                context TEXT,
                last_checked_ts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    yield db_path
    db_path.unlink()  # Cleanup

@pytest.fixture
def fresh_jira_db():
    """Provide clean Jira state database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE processed_mentions (
                issue_key TEXT,
                comment_id TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (issue_key, comment_id)
            )
        """)

    yield db_path
    db_path.unlink()

@pytest.fixture
def mock_slack_api():
    """Mock Slack API responses"""
    # Use responses library or similar to mock HTTP calls
    pass

@pytest.fixture
def mock_jira_api():
    """Mock Jira API responses"""
    pass

@pytest.fixture
def test_thread_messages():
    """Provide sample thread conversation for testing"""
    return {
        "parent": {
            "text": "What's the status of ECD-862?",
            "user": "U7L6RKG69",
            "ts": "1704470400.123456"
        },
        "replies": [
            {
                "text": "That ticket is currently in progress.",
                "user": "U09BVV00XRP",  # Bot
                "ts": "1704470420.123457"
            },
            {
                "text": "<@U09BVV00XRP> When will it be done?",
                "user": "U7L6RKG69",
                "ts": "1704470440.123458"
            }
        ]
    }
```

## Success Metrics

### Coverage Targets
- ✅ **Thread Context**: 100% coverage of context fetching, passing, and usage
- ✅ **No Double Replies**: 100% coverage of deduplication logic across all platforms
- ✅ **Major Features**: 80%+ coverage of end-to-end workflows

### Test Execution Time
- **Fast Tests** (<5s): Unit tests, basic integration - Run on every commit
- **Slow Tests** (@pytest.mark.slow, 10s-2min): Feature workflows - Run before merge
- **E2E Tests** (@pytest.mark.e2e, 2min+): Cross-platform flows - Run nightly

### Reliability
- ✅ All tests must be **deterministic** (no flaky tests)
- ✅ Tests must **clean up** resources (temp files, DB, API mocks)
- ✅ Tests must **document** expected behavior clearly

## Known Gaps Requiring Implementation

### Critical: Jira Comment Thread Context
**Current State:** Jira monitor only extracts single comment text

**Required Implementation:**
1. **Fetch Issue Details** (jira_monitor.py)
   ```python
   def get_issue_context(self, issue_key: str) -> Dict[str, Any]:
       """Fetch issue summary, description, and all comments"""
       # GET /rest/api/3/issue/{issueKey}?fields=summary,description,comment
       # Return: {
       #   "summary": "...",
       #   "description": "...",
       #   "comments": [{"author": "...", "text": "...", "created": "..."}, ...]
       # }
   ```

2. **Include in Event** (_filter_new_mentions)
   ```python
   # Line 198 - Add to event dict:
   "issue_context": self.get_issue_context(issue_key),
   ```

3. **Format for Claude** (process method)
   ```python
   # Include issue description + previous comments in prompt
   context = f"""
   ISSUE: {issue_key} - {issue_summary}
   DESCRIPTION: {issue_description}

   PREVIOUS COMMENTS:
   {format_comments_chronologically(previous_comments)}

   LATEST COMMENT: {current_comment}
   """
   ```

### Medium Priority: Response Failure Retry
**Current State:** If Slack/Jira response fails, message marked processed, never retried

**Required Implementation:**
- Add `response_status` field to processed_messages table
- Implement retry logic with exponential backoff
- Max 3 retries before marking as "failed"

## Test Execution Commands

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run only fast tests (skip @pytest.mark.slow)
pytest tests/integration/ -v -m "not slow"

# Run specific test suite
pytest tests/integration/test_slack_context_flow.py -v

# Run with coverage
pytest tests/integration/ --cov=src --cov-report=html

# Run slow tests only (for pre-merge checks)
pytest tests/integration/ -v -m slow

# Run E2E tests (nightly)
pytest tests/e2e/ -v -m e2e
```

## Appendix: Test Data Requirements

### Mock Slack Thread
```json
{
  "channel": "C02NW7QN1RN",
  "messages": [
    {"ts": "1704470400.123456", "user": "U7L6RKG69", "text": "What's ECD-862?"},
    {"ts": "1704470420.123457", "user": "U09BVV00XRP", "text": "ECD-862 is..."},
    {"ts": "1704470440.123458", "user": "U7L6RKG69", "text": "<@U09BVV00XRP> When is it due?"}
  ]
}
```

### Mock Jira Issue with Comments
```json
{
  "key": "ECD-862",
  "fields": {
    "summary": "Implement user authentication",
    "description": "Add OAuth2 authentication to the application",
    "status": {"name": "In Progress"},
    "comment": {
      "comments": [
        {"id": "12345", "author": {"displayName": "Ethan"}, "body": "Started work on this"},
        {"id": "12346", "author": {"displayName": "Mohamed"}, "body": "@remington what's the priority?"}
      ]
    }
  }
}
```

---

**Next Steps:**
1. Review and approve this test plan
2. Implement Phase 1 tests (Week 1)
3. Add Jira comment thread context feature (required for Phase 2)
4. Implement Phase 2 and 3 tests progressively
5. Set up CI/CD pipeline with test automation
