# Jira Status Transitions - Skill

## Purpose
This skill provides the correct way to **change Jira ticket statuses** (e.g., move tickets from "In Progress" to "Done", "Blocked" to "In Progress", etc.).

## Problem
The Atlassian MCP tools do NOT provide status transition functionality. While you can use `editJiraIssue()` to update many fields, you **cannot directly change the status field** because Jira statuses work through a workflow transition system, not direct field updates.

## Solution
Use the **REST API directly** via the helper script at `scripts/transition_jira_ticket.py`.

## How to Transition a Jira Ticket Status

### Step 1: Determine Target Status
Identify the status you want to move the ticket to:
- Common statuses: "To Do", "In Progress", "In Review", "In QA", "Pending Approval", "Done", "Blocked", "Cancelled"
- Status names are case-insensitive (the script handles this)

### Step 2: Use the Helper Script

```bash
python scripts/transition_jira_ticket.py <TICKET_KEY> "<TARGET_STATUS>"
```

### Example: Move Ticket to Done

```bash
python scripts/transition_jira_ticket.py ECD-617 "Done"
```

**Output:**
```
Transitioning ECD-617 to 'Done'...
✅ Success! ECD-617 transitioned to 'Done'
   Transition ID: 31
```

### Example: Move Ticket to In Progress

```bash
python scripts/transition_jira_ticket.py ECD-123 "In Progress"
```

### Example: Mark Ticket as Blocked

```bash
python scripts/transition_jira_ticket.py ECD-456 "Blocked"
```

## Common Use Cases

### 1. Close Completed Ticket
When a ticket is fully completed and approved:
```bash
python scripts/transition_jira_ticket.py ECD-617 "Done"
```

### 2. Start Working on Ticket
When picking up a new ticket:
```bash
python scripts/transition_jira_ticket.py ECD-123 "In Progress"
```

### 3. Move to Code Review
When PR is ready for review:
```bash
python scripts/transition_jira_ticket.py ECD-456 "In Review"
```

### 4. Mark as Blocked
When encountering a blocker:
```bash
python scripts/transition_jira_ticket.py ECD-789 "Blocked"
```

### 5. Unblock Ticket
When blocker is resolved:
```bash
python scripts/transition_jira_ticket.py ECD-789 "In Progress"
```

## Error Handling

### Invalid Status
If you try to transition to a status that's not available from the current state:

```bash
python scripts/transition_jira_ticket.py ECD-123 "Done"
```

**Error Output:**
```
❌ Error: Status 'Done' not available for ECD-123.
Available statuses: In Progress, Blocked, In Review
```

**Solution:** Check the available statuses in the error message and use one of those.

### Invalid Ticket Key
If the ticket doesn't exist:

```bash
python scripts/transition_jira_ticket.py ECD-99999 "Done"
```

**Error Output:**
```
❌ Error: Failed to get transitions: Issue does not exist or you do not have permission to see it.
```

**Solution:** Verify the ticket key is correct using `mcp__atlassian__getJiraIssue()` first.

## Workflow Integration

### Complete Workflow: Respond to Comment + Update Status

```bash
# 1. Get issue context (use MCP)
mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-617")

# 2. Look up user account ID (use MCP)
mcp__atlassian__lookupJiraAccountId(searchString="Ethan")
# Returns: 712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e

# 3. Post comment with status update (use script)
python scripts/post_jira_comment.py ECD-617 \
  "Hi @Ethan, I've completed this ticket and it's ready for your review." \
  --mention-id "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e" \
  --mention-name "Ethan"

# 4. Transition ticket status (use script)
python scripts/transition_jira_ticket.py ECD-617 "In Review"

# 5. Verify success
# Both commands will output success messages
```

### Workflow: Handle SLA Escalation

When a ticket is overdue and needs to be closed:

```bash
# 1. Verify ticket is actually complete
mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-456")

# 2. Add closing comment
python scripts/post_jira_comment.py ECD-456 \
  "Closing ticket as all acceptance criteria have been met and code is in production." \

# 3. Move to Done
python scripts/transition_jira_ticket.py ECD-456 "Done"
```

### Workflow: Unblock After Dependency Resolved

```bash
# 1. Check current status
mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-789")

# 2. Add comment explaining resolution
python scripts/post_jira_comment.py ECD-789 \
  "Blocker resolved - ECD-500 is now complete. Resuming work."

# 3. Move back to In Progress
python scripts/transition_jira_ticket.py ECD-789 "In Progress"
```

## Technical Details

### How Jira Transitions Work

Jira uses a **workflow-based status system**:
- Each project has a defined workflow (e.g., To Do → In Progress → Done)
- You can only move between certain statuses based on the workflow
- Each movement is called a "transition" and has a unique transition ID
- The script automatically finds the correct transition ID for you

### Script Behavior

1. **Fetches available transitions** for the ticket via:
   ```
   GET https://citemed.atlassian.net/rest/api/3/issue/{ticket_key}/transitions
   ```

2. **Finds matching transition** by comparing status names (case-insensitive)

3. **Executes transition** via:
   ```
   POST https://citemed.atlassian.net/rest/api/3/issue/{ticket_key}/transitions
   Body: {"transition": {"id": "31"}}
   ```

### Authentication
The script uses environment variables from `.env`:
- `JIRA_URL` - Jira instance URL (default: https://citemed.atlassian.net)
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - Your Jira API token

## Important Notes

1. **Always use the script for status transitions** - Don't try to use MCP `editJiraIssue()`
2. **MCP is fine for other field updates** - Use `editJiraIssue()` for assignee, priority, labels, etc.
3. **Status names are case-insensitive** - "done", "Done", and "DONE" all work
4. **Check available transitions first** - If a transition fails, the error will list valid options
5. **Some transitions may require fields** - If a transition requires additional fields (rare), the script will fail with details

## Common Mistakes to Avoid

❌ **DON'T**: Use `mcp__atlassian__editJiraIssue()` to change status
❌ **DON'T**: Assume all statuses are available from any state
❌ **DON'T**: Forget to add a comment explaining why you're changing the status

✅ **DO**: Use `scripts/transition_jira_ticket.py`
✅ **DO**: Check available transitions if you get an error
✅ **DO**: Add a Jira comment before/after transitioning to explain the change
✅ **DO**: Follow team workflow conventions (e.g., add PR link before moving to "In Review")

## Jira Workflow States (CiteMed ECD Project)

### Standard Workflow Path
```
Draft → In Refinement → Ready For Development → In Progress → QA →
  Pending Approval → Complete
          ↓
       Blocked
```

### Available Status Names (CiteMed)
- **Draft** - Initial story creation
- **In Refinement** - Story being refined
- **Pending Approval** - Awaiting stakeholder approval
- **Approved** - Approved for development
- **Spring Planning** - Being planned for sprint
- **Ready For Development** - Ready to be picked up
- **In Progress** - Developer actively working
- **QA** - Quality assurance testing
- **Complete** - Finished and deployed (equivalent to "Done")
- **Ready for Design** - Needs design work
- **Pending Design Approval** - Awaiting design approval
- **Blocked** - Cannot progress due to blocker

### When to Use Each Status

**Ready For Development**
- Ticket is ready to be worked on
- All dependencies resolved
- Acceptance criteria defined

**In Progress**
- Developer actively coding
- Git branch exists
- Regular progress updates

**QA**
- Code merged to staging
- QA team testing
- Bugs logged if found

**Pending Approval**
- Functionality complete and tested
- Awaiting PM sign-off
- Ready for production

**Complete**
- All acceptance criteria met
- Code in production
- PM approved
- **NOTE:** Use "Complete", not "Done" for CiteMed tickets!

**Blocked**
- Cannot progress due to external dependency
- Blocker documented in comments
- Daily updates required (SLA)

## Related Files
- **Script**: `scripts/transition_jira_ticket.py`
- **Comment Script**: `scripts/post_jira_comment.py`
- **Jira Best Practices**: `.claude/skills/jira-best-practices/SKILL.md`

## Troubleshooting

**Issue**: Script fails with "Missing Jira configuration"
**Fix**: Ensure `.env` has `JIRA_EMAIL` and `JIRA_API_TOKEN`

**Issue**: "Status 'X' not available" error
**Fix**: Check the error message for available statuses and use one of those

**Issue**: Permission denied
**Fix**: Verify you have permission to edit the ticket in Jira

**Issue**: Ticket doesn't exist
**Fix**: Double-check the ticket key (e.g., "ECD-617" not "617")

## Examples in Context

### Example 1: Claude Code Response to Slack Mention
When user asks: "@remington can you close ECD-617 as done?"

Claude Code should:
1. Verify ticket status: `mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-617")`
2. Check if it's actually ready to close (review comments, PR status)
3. Add closing comment: `python scripts/post_jira_comment.py ECD-617 "Closing ticket as requested - all work completed."`
4. Transition to Done: `python scripts/transition_jira_ticket.py ECD-617 "Done"`
5. Reply in Slack: "✅ Closed ECD-617: https://citemed.atlassian.net/browse/ECD-617"

### Example 2: SLA Violation Escalation
When SLA monitor detects stale "Pending Approval" ticket:

```bash
# Add escalation comment
python scripts/post_jira_comment.py ECD-456 \
  "@stakeholder This ticket has been pending approval for 3 days (SLA: 48h). Please review and approve, or provide feedback for revisions." \
  --mention-id "..." --mention-name "stakeholder"

# If approved verbally, close it
python scripts/transition_jira_ticket.py ECD-456 "Done"
```

### Example 3: Blocked Ticket Resolution
When dependency is resolved:

```bash
# Comment on unblocking
python scripts/post_jira_comment.py ECD-789 "Blocker resolved - backend API (ECD-500) is now deployed. Resuming frontend integration work."

# Move back to In Progress
python scripts/transition_jira_ticket.py ECD-789 "In Progress"
```

---

**This skill enables Claude Code to properly manage Jira ticket statuses through workflow transitions, ensuring tickets move through the development lifecycle correctly and team workflows are followed.**
