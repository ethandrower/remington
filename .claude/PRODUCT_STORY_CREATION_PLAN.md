# Product Story Creation with Approval Workflow - Implementation Plan

**Status:** 📋 Planning Phase
**Last Updated:** 2025-11-11

## Overview

Enable PM agent to act as a product manager for story/epic/bug creation through natural language requests with an approval workflow loop.

### User Flow Example

```
User in Jira comment: "@remington can you create a bug report for this issue?"
  ↓
PM Agent: "📋 I'll create a bug report. Let me analyze this..."
  ↓
PM Agent: "Here's the draft bug report:

  # Bug: [Title]
  ## Description
  [Details...]

  Does this look accurate? Reply with:
  - ✅ 'approved' to create the Jira ticket
  - 📝 'changes: [description]' to refine
  - ❌ 'cancel' to discard"
  ↓
User replies: "approved"
  ↓
PM Agent: "✅ Created ECD-789: [Bug Title]
  Link: https://citemed.atlassian.net/browse/ECD-789"
```

## Architecture Components

### 1. Intent Detection

**Purpose:** Determine if a mention is a PM request vs code review/status update

**Implementation:** In `claude_code_orchestrator.py`

```python
def detect_pm_intent(self, comment_text: str, context: dict) -> dict:
    """
    Detect if this is a product management request

    Returns:
        {
            "is_pm_request": bool,
            "request_type": "story" | "bug" | "epic" | "feature",
            "confidence": float,
            "extracted_context": str
        }
    """
    # Use Claude Code to analyze the request
    # Look for keywords: "create a story", "file a bug", "new feature", etc.
    # Analyze context to extract requirements
```

**Detection Patterns:**
- "create a bug report"
- "file a bug for this"
- "this should be a separate feature"
- "make this into a story"
- "create an epic for..."
- "write up a ticket"

### 2. Approval Workflow Database

**Purpose:** Track pending PM requests awaiting approval

**Schema:** `pm_requests_state.db`

```sql
CREATE TABLE pending_pm_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,  -- UUID
    source TEXT NOT NULL,              -- 'jira' | 'slack' | 'bitbucket'
    source_id TEXT NOT NULL,           -- issue_key | thread_ts | pr_id
    request_type TEXT NOT NULL,        -- 'story' | 'bug' | 'epic' | 'feature'
    user_id TEXT NOT NULL,             -- requester account ID
    user_name TEXT NOT NULL,           -- requester display name
    original_context TEXT NOT NULL,    -- original comment/thread
    draft_content TEXT NOT NULL,       -- generated draft story/bug
    status TEXT DEFAULT 'pending',     -- 'pending' | 'approved' | 'changes_requested' | 'cancelled' | 'created'
    jira_ticket_key TEXT,              -- filled when ticket created
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    created_ticket_at TIMESTAMP
);

CREATE INDEX idx_request_id ON pending_pm_requests(request_id);
CREATE INDEX idx_source_id ON pending_pm_requests(source, source_id);
CREATE INDEX idx_status ON pending_pm_requests(status);

-- Track revision history
CREATE TABLE pm_request_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    draft_content TEXT NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES pending_pm_requests(request_id)
);
```

### 3. Product Management Documentation

**Location:** `.claude/agents/product-manager/`

**Files to Create:**

```
.claude/agents/product-manager/
├── agent.md                    # Main PM agent instructions
├── workflows/
│   ├── story-generation.md     # How to generate stories from conversations
│   ├── bug-generation.md       # How to generate bug reports
│   ├── epic-generation.md      # How to generate epics
│   └── approval-handling.md    # How to process feedback
├── templates/
│   ├── story-template.md       # (COPY from citemed_web)
│   ├── epic-template.md        # (COPY from citemed_web)
│   └── bug-template.md         # (CREATE - similar to story)
└── context/
    ├── platform-overview.md    # CiteMed platform context
    ├── module-descriptions.md  # CiteSource, Literature modules
    └── personas.md             # User personas
```

### 4. Story Generation Workflow

**Purpose:** Use Claude Code to generate draft stories from conversation context

**Workflow:** `.claude/agents/product-manager/workflows/story-generation.md`

```markdown
# Story Generation Workflow

When the PM agent receives a product management request:

## Step 1: Analyze Context
- Extract key requirements from the original comment/thread
- Identify affected modules/components
- Determine user personas involved
- Assess complexity and scope

## Step 2: Generate Draft Using Template
Load appropriate template:
- `.claude/agents/product-manager/templates/story-template.md` for features
- `.claude/agents/product-manager/templates/bug-template.md` for bugs
- `.claude/agents/product-manager/templates/epic-template.md` for epics

Fill in template sections based on context:
- Title: Clear, descriptive
- User Story: As a [persona], I want [capability], so that [outcome]
- Business Context: Why this matters
- Technical Scope: What will be built
- Acceptance Criteria: Testable requirements

## Step 3: Post Draft for Review
Reply to original comment with:
"📋 Here's the draft [story/bug/epic]:

[Formatted draft with markdown]

**Next Steps:**
- Reply **'approved'** to create Jira ticket ECD-XXX
- Reply **'changes: [feedback]'** to refine
- Reply **'cancel'** to discard

I'll monitor this thread for your response."

## Step 4: Store in Database
Save to `pending_pm_requests` with status='pending'

## Step 5: Monitor for Response
Polling checks for new comments on this thread:
- If 'approved': Create Jira ticket, update status='created'
- If 'changes: ...': Generate new revision, post updated draft
- If 'cancel': Update status='cancelled'
```

### 5. Orchestrator Integration

**File:** `src/orchestration/claude_code_orchestrator.py`

**New Methods:**

```python
def process_pm_request(self, comment_text: str, context: dict) -> dict:
    """
    Handle product management request (story/bug/epic creation)

    Steps:
    1. Detect PM intent and request type
    2. Extract context and requirements
    3. Invoke Claude Code with PM agent documentation
    4. Generate draft story/bug/epic
    5. Post draft for review
    6. Store in approval workflow database

    Returns:
        {
            "success": bool,
            "request_id": str,
            "draft_posted": bool,
            "message": str
        }
    """
    pass

def check_pm_approval_status(self, request_id: str) -> dict:
    """
    Check if a pending PM request has been approved/modified

    Returns:
        {
            "status": "pending" | "approved" | "changes_requested" | "cancelled",
            "feedback": str,  # if changes requested
            "should_create_ticket": bool
        }
    """
    pass

def create_jira_ticket_from_draft(self, request_id: str) -> dict:
    """
    Create actual Jira ticket from approved draft

    Returns:
        {
            "success": bool,
            "ticket_key": str,  # e.g., "ECD-789"
            "ticket_url": str
        }
    """
    pass
```

### 6. Approval Loop Monitoring

**Purpose:** Monitor pending requests for approval/feedback

**Implementation:** Add to polling loops in `src/pm_agent_service.py`

```python
def monitor_pm_approvals(self):
    """
    Check pending PM requests for approval responses

    For each pending request:
    1. Query Jira/Slack/Bitbucket for new comments on the source
    2. Parse for approval keywords ('approved', 'changes:', 'cancel')
    3. Take appropriate action:
       - approved → create_jira_ticket_from_draft()
       - changes → regenerate draft with feedback
       - cancel → mark as cancelled
    4. Update database status
    5. Post confirmation message
    """
    pass
```

**Polling Frequency:** Every 30 seconds (same as existing Jira/Slack/Bitbucket polling)

### 7. Template System

**Bug Report Template** (NEW - to create):

```markdown
# Bug: [Issue Title]

## Summary
[One-sentence description of the problem]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- **Browser/Version:** [if applicable]
- **User Role:** [persona experiencing the issue]
- **Module:** [CiteSource/Literature/etc.]

## Impact
- **Severity:** [Critical/High/Medium/Low]
- **Users Affected:** [Number or percentage]
- **Workaround:** [If available]

## Technical Details
- **Error Messages:** [Any errors in console/logs]
- **Related Components:** [Affected models/views]
- **Potential Cause:** [If known]

## Acceptance Criteria
- [ ] Bug is reproducible in test environment
- [ ] Fix implemented and tested
- [ ] No regressions introduced
- [ ] Edge cases handled
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
- ✅ Copy PM templates from citemed_web to project-manager
- ✅ Create PM agent documentation structure
- ✅ Design and implement approval workflow database
- ✅ Create bug report template

### Phase 2: Core Workflow (Week 2)
- ✅ Implement PM intent detection in orchestrator
- ✅ Create story generation workflow for Claude Code
- ✅ Build draft posting mechanism
- ✅ Implement database persistence

### Phase 3: Approval Loop (Week 3)
- ✅ Build approval monitoring system
- ✅ Implement feedback parsing logic
- ✅ Create revision generation for change requests
- ✅ Add Jira ticket creation from approved drafts

### Phase 4: Testing & Polish (Week 4)
- ✅ End-to-end testing (Jira, Slack, Bitbucket sources)
- ✅ Edge case handling (ambiguous requests, spam prevention)
- ✅ Documentation updates
- ✅ Logging to Slack #pm-agent-logs

## Integration Points

### With Existing Systems

1. **Jira Monitor** (`bots/jira_monitor.py`)
   - Already detects @remington mentions
   - Add PM intent check before code review flow
   - Monitor pending requests for approval comments

2. **Slack Monitor** (`bots/slack_monitor.py`)
   - Already detects @remington mentions
   - Add PM intent check
   - Support threaded approval workflow

3. **Bitbucket Monitor** (`bots/bitbucket_monitor.py`)
   - Detect PM requests in PR comments
   - Monitor for approval in comment threads

4. **Slack Logger** (`src/utils/slack_logger.py`)
   - Log all PM request creations
   - Log approval status changes
   - Log Jira ticket creation

## Success Metrics

- **Primary:** User can tag @remington with PM request → receive draft → approve → Jira ticket created
- **Speed:** Draft generated within 60 seconds
- **Accuracy:** Draft requires ≤1 revision on average
- **Adoption:** Team uses for 80%+ of new story creation

## Example Conversations

### Example 1: Bug Report

```
User (Jira comment on ECD-500):
"@remington can you create a bug report for this? The reference search isn't working for users with special characters in their names"

PM Agent:
"📋 Creating bug report based on this issue. Analyzing context...

Here's the draft bug report:

# Bug: Reference Search Fails for Users with Special Characters in Names

## Summary
Reference search functionality fails when the user's name contains special characters (e.g., accents, hyphens), preventing them from searching their project references.

## Steps to Reproduce
1. Log in as a user with special characters in name (e.g., "José García-Smith")
2. Navigate to CiteSource > My References
3. Enter search term in reference search box
4. Click Search button

## Expected Behavior
Search results should display matching references regardless of special characters in user name.

## Actual Behavior
Search returns error or no results. User cannot search references.

## Environment
- Module: CiteSource
- User Role: Regulatory Affairs Specialist
- Affected Users: ~15% (users with non-ASCII names)

## Impact
- Severity: High
- Workaround: None currently available

## Acceptance Criteria
- [ ] Search works for users with special characters (accents, hyphens, apostrophes)
- [ ] Search works for all UTF-8 character sets
- [ ] Existing search functionality not affected
- [ ] Unit tests added for edge cases

**Next Steps:**
- Reply **'approved'** to create Jira ticket
- Reply **'changes: [feedback]'** to refine
- Reply **'cancel'** to discard"

User:
"approved"

PM Agent:
"✅ Created ECD-789: Reference Search Fails for Users with Special Characters in Names
Link: https://citemed.atlassian.net/browse/ECD-789

The bug report has been filed and is ready for the development team."
```

### Example 2: Feature Story with Revision

```
User (Slack):
"@remington we should create a story for bulk reference import from EndNote"

PM Agent:
"📋 I'll create a story for bulk EndNote reference import. Let me gather requirements..."

[Draft posted]

User:
"changes: also needs to support RIS format, not just EndNote XML"

PM Agent:
"📝 Updated the story to include RIS format support. Here's revision 2:

[Updated draft with RIS support added]

Does this look better?"

User:
"approved"

PM Agent:
"✅ Created ECD-790: Bulk Reference Import from EndNote and RIS Files
Link: https://citemed.atlassian.net/browse/ECD-790"
```

## Technical Considerations

### Performance
- Claude Code invocations: ~30-60 seconds per draft
- Database queries: < 100ms
- Polling overhead: Negligible (same as existing polling)

### Security
- Validate user permissions before creating Jira tickets
- Prevent spam: Max 5 pending requests per user
- Rate limiting: Max 10 PM requests per hour per user

### Error Handling
- Claude Code timeout: Retry once, then notify user
- Jira API failure: Store draft, retry ticket creation
- Ambiguous requests: Ask clarifying questions

### Monitoring
- Log all PM requests to Slack #pm-agent-logs
- Track approval rates and revision counts
- Monitor Claude Code performance

## Future Enhancements

- **Auto-prioritization:** Suggest priority based on keywords ("urgent", "blocking")
- **Related ticket search:** "Similar to ECD-123, should I link them?"
- **Epic management:** "Add this story to Epic ECD-45?"
- **Sprint planning:** "Shall I add this to the current sprint?"
- **Assignee suggestion:** "Based on expertise, suggest assigning to Mohamed?"

## Open Questions

1. Should we auto-create tickets after N hours if no response? (Suggest: No, require explicit approval)
2. What if multiple people reply with conflicting feedback? (Suggest: Take first response, notify requester)
3. Should we support editing existing drafts after posting? (Suggest: Yes, via 'changes:' command)
4. Notification strategy for approval requests? (Suggest: Tag requester in the draft post)

## Dependencies

- **Claude Code CLI:** Required for draft generation
- **Filesystem MCP:** To access citemed_web/.claude/ documentation
- **Atlassian MCP:** For Jira ticket creation
- **Slack SDK:** For Slack thread monitoring (already installed)

## Documentation Updates

- README.md: Add PM story creation to capability matrix
- FUTURE_WORK.md: Move from "Planned" to "Operational" once complete
- New: PM_STORY_CREATION_USER_GUIDE.md for team

---

**Next Step:** Review this plan, then proceed with Phase 1 implementation.
