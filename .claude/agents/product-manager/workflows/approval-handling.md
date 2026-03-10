# Approval Handling Workflow

This workflow guides the PM agent through monitoring and processing approval responses for pending PM requests (stories, bugs, epics).

## Overview

When a PM draft is posted, the user can respond with:
- **"approved"** → Create Jira ticket immediately
- **"changes: [feedback]"** → Regenerate draft with feedback incorporated
- **"cancel"** → Discard the request

This workflow handles monitoring for these responses and taking appropriate action.

## Step 1: Monitor for Approval Responses

### Detection Patterns

The PM agent service polls for new comments on threads where drafts were posted. Look for these patterns:

**Approval Keywords:**
- "approved" (exact match, case-insensitive)
- "approve"
- "looks good, create it"
- "go ahead"
- "✅" (checkmark emoji)

**Change Request Keywords:**
- "changes:" followed by feedback text
- "revise:" followed by feedback
- "update:" followed by feedback
- "modify:" followed by feedback
- "please change..." (extract feedback after "change")

**Cancel Keywords:**
- "cancel"
- "discard"
- "never mind"
- "don't create"
- "❌" (X emoji)

### Identify Request Context

For each new comment:
1. Check if comment is on a thread with a pending PM request
2. Query database for matching request:
   ```python
   db = get_pm_requests_db()
   request = db.get_request_by_source(
       source='jira',  # or 'slack', 'bitbucket'
       source_id='ECD-123'  # issue key, thread_ts, pr_id
   )
   ```
3. Verify request status is 'pending'
4. Verify commenter is the original requester (or authorized approver)

## Step 2: Parse Approval Decision

### Decision Types

#### Type 1: Approval
**Pattern:** "approved" OR similar approval keyword

**Action:**
```python
# Update request status to 'approved'
db.update_request_status(request_id, 'approved')

# Proceed to Jira ticket creation (Step 3)
```

#### Type 2: Change Request
**Pattern:** "changes: [feedback text]"

**Extract Feedback:**
```python
import re

# Extract feedback after "changes:", "revise:", etc.
patterns = [
    r'changes?:\s*(.+)',
    r'revise?:\s*(.+)',
    r'update:\s*(.+)',
    r'modify:\s*(.+)',
    r'please change\s*(.+)'
]

feedback = None
for pattern in patterns:
    match = re.search(pattern, comment_text, re.IGNORECASE | re.DOTALL)
    if match:
        feedback = match.group(1).strip()
        break
```

**Action:**
```python
# Update request status to 'changes_requested'
db.update_request_status(request_id, 'changes_requested')

# Proceed to revision generation (Step 4)
```

#### Type 3: Cancellation
**Pattern:** "cancel" OR similar cancel keyword

**Action:**
```python
# Update request status to 'cancelled'
db.update_request_status(request_id, 'cancelled')

# Post acknowledgment comment
# No further action needed
```

## Step 3: Create Jira Ticket (On Approval)

### Extract Ticket Data from Draft

Parse the approved draft markdown to extract:

**For Stories:**
- Title
- User story statement (As a... I want... So that...)
- Business context
- Technical scope
- Acceptance criteria (checklist)
- Implementation notes

**For Bugs:**
- Title
- Summary
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Severity
- Acceptance criteria

**For Epics:**
- Title
- Business justification
- Scope overview
- Success criteria
- Timeline expectations

### Map to Jira Fields

```python
# Jira field mapping
jira_fields = {
    "project": {"key": "ECD"},
    "issuetype": {"name": "Story"},  # or "Bug", "Epic"
    "summary": extracted_title,
    "description": formatted_description_adf,
    "priority": {"name": determine_priority(draft_content)},
    "labels": extract_labels(draft_content),
}

# Use Atlassian MCP to create ticket
issue = mcp__atlassian__createJiraIssue(
    cloudId="67bbfd03-b309-414f-9640-908213f80628",
    fields=jira_fields
)
```

### Format Description for Jira

Convert markdown to Atlassian Document Format (ADF):

```python
def markdown_to_adf(markdown_text: str) -> dict:
    """
    Convert markdown to ADF for Jira description field

    Supports:
    - Headers (# ## ###)
    - Bold (**text**)
    - Italic (*text*)
    - Lists (- item)
    - Code blocks (```code```)
    - Checkboxes (- [ ] item)
    """
    # Implementation would convert markdown to ADF JSON structure
    # For now, can use simple text with formatting
    pass
```

### Update Database

```python
# Mark request as created with Jira ticket key
db.update_request_status(
    request_id=request_id,
    status='created',
    jira_ticket_key=issue_key
)
```

### Post Confirmation Comment

Reply to the original thread:

```markdown
✅ Created {issue_key}: {title}

Link: https://citemed.atlassian.net/browse/{issue_key}

The ticket is ready for the development team. I've set:
- Priority: {priority}
- Issue Type: {issue_type}
- Labels: {labels}

{Optional: Sprint assignment if requested}
```

## Step 4: Regenerate Draft (On Change Request)

### Load Feedback Context

```python
# Get original request
request = db.get_request(request_id)

original_draft = request['draft_content']
original_context = request['original_context']
feedback = extracted_feedback_text
```

### Invoke Claude Code for Revision

Create a revision prompt:

```markdown
You are revising a {request_type} based on user feedback.

**Original Context:**
{original_context}

**Previous Draft (Revision {current_revision}):**
{original_draft}

**User Feedback:**
{feedback}

**Task:**
Apply the user's feedback to create an improved draft. Make the requested changes while maintaining the overall structure and quality of the original draft.

Follow the {request_type} template structure:
- For stories: Use story-template.md
- For bugs: Use bug-template.md
- For epics: Use epic-template.md

**Output:**
Provide the complete revised draft in markdown format.
```

### Generate Revised Draft

```python
from src.orchestration.claude_code_orchestrator import ClaudeCodeOrchestrator

orchestrator = ClaudeCodeOrchestrator()

revised_draft = orchestrator.invoke_claude_code(
    prompt=revision_prompt,
    context={
        'agent': 'product-manager',
        'workflow': f'{request_type}-generation',
        'revision': True
    }
)
```

### Store Revision in Database

```python
# Add revision to history
revision_number = db.add_revision(
    request_id=request_id,
    draft_content=revised_draft,
    feedback=feedback
)
```

### Post Updated Draft for Re-approval

Reply to the thread:

```markdown
📝 Updated draft based on your feedback (Revision {revision_number})

**Changes Made:**
{summarize_changes(original_draft, revised_draft, feedback)}

---

{revised_draft}

---

**Next Steps:**
- Reply **'approved'** to create Jira ticket
- Reply **'changes: [more feedback]'** to revise again
- Reply **'cancel'** to discard

Does this look better?
```

## Step 5: Handle Edge Cases

### Multiple Responses

**Scenario:** Multiple people respond with different decisions

**Solution:**
- Only accept responses from the original requester
- Check `user_id` matches `request['user_id']`
- Ignore other responses (optionally notify that only requester can approve)

### Conflicting Responses

**Scenario:** User says "approved" then "wait, changes: ..."

**Solution:**
- Process responses in chronological order
- First approval creates ticket immediately (race condition)
- Subsequent change requests are ignored with message:
  "Ticket ECD-XXX has already been created. Please comment on the ticket directly for changes."

### Ambiguous Responses

**Scenario:** "This looks mostly good but can you add more detail?"

**Solution:**
- Does NOT match "approved" or "changes:" pattern
- Post clarification request:
  ```markdown
  I'm not sure if you're approving or requesting changes. Please reply with:
  - **'approved'** if you'd like me to create the ticket as-is
  - **'changes: [specific feedback]'** if you'd like revisions
  ```

### Timeout Handling

**Scenario:** No response after 7 days

**Solution:**
- Keep request in 'pending' status (no auto-approval)
- Optionally: Send reminder after 3 days
- Optionally: Auto-cancel after 14 days with notification

## Step 6: Logging and Notifications

### Database Logging

All state changes are logged:
```python
# Approval logged
db.update_request_status(request_id, 'approved')

# Revision logged
db.add_revision(request_id, revised_draft, feedback)

# Creation logged
db.update_request_status(request_id, 'created', jira_ticket_key)
```

### Slack Notifications

Post to #pm-agent-logs:

**On Approval:**
```python
slack_logger.post_activity(
    "PM Request Approved",
    f"User approved {request_type} draft for {source_id}",
    link=f"https://citemed.atlassian.net/browse/{issue_key}"
)
```

**On Revision:**
```python
slack_logger.post_activity(
    "PM Request Revised",
    f"Generated revision {revision_number} for {request_type} based on user feedback",
    link=f"source_url"
)
```

**On Creation:**
```python
slack_logger.post_activity(
    "Jira Ticket Created",
    f"Created {issue_key} from approved PM request",
    link=f"https://citemed.atlassian.net/browse/{issue_key}"
)
```

## Complete Approval Flow Example

### Scenario: Story with Revision

**Step 1: User Requests Story**
```
User (ECD-123 comment): "@remington create a story for bulk EndNote import"
```

**Step 2: PM Agent Posts Draft**
```
PM Agent: "📋 Here's the draft story:

# Story: Bulk Import References from EndNote XML

[... draft content ...]

**Next Steps:**
- Reply 'approved' to create Jira ticket
- Reply 'changes: [feedback]' to refine
- Reply 'cancel' to discard"
```

**Database State:**
```python
{
    "request_id": "abc-123-def",
    "source": "jira",
    "source_id": "ECD-123",
    "request_type": "story",
    "status": "pending",
    "draft_content": "[full draft markdown]"
}
```

**Step 3: User Requests Changes**
```
User: "changes: also needs to support RIS format, not just EndNote XML"
```

**Step 4: PM Agent Detects Change Request**
- Polls ECD-123 comments
- Finds "changes:" pattern
- Extracts feedback: "also needs to support RIS format, not just EndNote XML"

**Step 5: PM Agent Generates Revision**
- Invokes Claude Code with revision prompt
- Incorporates RIS format support
- Adds RIS to acceptance criteria
- Stores as Revision 2

**Database State:**
```python
{
    "request_id": "abc-123-def",
    "status": "pending",  # back to pending after changes
    "draft_content": "[revised draft markdown]",
    ...
}

# In pm_request_revisions table:
{
    "request_id": "abc-123-def",
    "revision_number": 2,
    "draft_content": "[revised draft]",
    "feedback": "also needs to support RIS format, not just EndNote XML"
}
```

**Step 6: PM Agent Posts Revision**
```
PM Agent: "📝 Updated draft based on your feedback (Revision 2)

**Changes Made:**
- Added RIS format support to import engine
- Updated acceptance criteria to include RIS validation
- Added RIS to technical scope

[... revised draft ...]

Does this look better?"
```

**Step 7: User Approves**
```
User: "approved"
```

**Step 8: PM Agent Creates Jira Ticket**
- Parses approved draft
- Extracts title, description, acceptance criteria
- Creates ECD-456 via Atlassian MCP
- Updates database: status='created', jira_ticket_key='ECD-456'

**Step 9: PM Agent Confirms Creation**
```
PM Agent: "✅ Created ECD-456: Bulk Import References from EndNote XML and RIS

Link: https://citemed.atlassian.net/browse/ECD-456

The ticket is ready for the development team. I've set:
- Priority: High
- Issue Type: Story
- Labels: import, references, enhancement"
```

**Final Database State:**
```python
{
    "request_id": "abc-123-def",
    "status": "created",
    "jira_ticket_key": "ECD-456",
    "approved_at": "2025-11-13T14:23:00Z",
    "created_ticket_at": "2025-11-13T14:23:15Z"
}
```

---

## Implementation Checklist

When implementing this workflow in the orchestrator:

- [ ] Poll for new comments on pending PM request threads
- [ ] Parse comments for approval/changes/cancel keywords
- [ ] Validate commenter is authorized (original requester)
- [ ] Extract feedback text for change requests
- [ ] Invoke Claude Code with revision prompt when changes requested
- [ ] Store revisions in database with feedback tracking
- [ ] Create Jira tickets via Atlassian MCP when approved
- [ ] Update database status appropriately
- [ ] Post confirmation comments to original thread
- [ ] Log all actions to Slack #pm-agent-logs
- [ ] Handle edge cases (multiple responses, conflicts, ambiguity)
- [ ] Add timeout handling (optional reminders, auto-cancel)

---

**Remember:** The approval workflow ensures stakeholder alignment before creating Jira tickets, reducing rework and improving ticket quality.
