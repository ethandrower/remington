---
name: jira-best-practices
description: Provides knowledge about effective Jira usage including ticket formatting, workflow management, JQL queries, status transitions, and collaboration best practices. Use when creating or updating Jira tickets, running JQL queries, enforcing Jira workflows, commenting on tickets, or managing ticket relationships and links.
---

# Jira Best Practices Skill

## Purpose
This skill provides knowledge about effective Jira usage, including ticket formatting, workflow management, JQL queries, and collaboration best practices.

## Ticket Creation Best Practices

### User Story Format

**Template:**
```
As a [persona/user type],
I want [goal/desire],
So that [benefit/value].
```

**Example:**
```
As a researcher,
I want to cite articles directly from Microsoft Word,
So that I can maintain my writing flow without switching applications.
```

### Ticket Title Guidelines

**Good Titles:**
- ✅ "Add bulk reference upload to project library"
- ✅ "Fix: Comment response emails not sending"
- ✅ "Implement Microsoft Word authentication via OAuth"

**Bad Titles:**
- ❌ "Bug fix"
- ❌ "Updates"
- ❌ "Do the thing we discussed"

**Best Practices:**
- Start with verb (Add, Fix, Implement, Update, Refactor)
- Be specific and descriptive
- Keep under 100 characters
- Include context (which feature/module)
- Use keywords for searchability

### Acceptance Criteria

**Format: Given-When-Then**
```markdown
## Acceptance Criteria

- **Given** I am a logged-in user with project access
- **When** I click "Upload References" and select a .ris file
- **Then** all valid references are imported to the project library

- **Given** the .ris file contains invalid entries
- **When** I upload the file
- **Then** I see a validation error report with specific line numbers

- **Given** import is successful
- **When** import completes
- **Then** I see confirmation message with count of imported references
```

**Best Practices:**
- Make criteria testable and verifiable
- Include happy path and error cases
- Specify expected user experience
- Define validation rules
- Include edge cases

### Technical Details Section

```markdown
## Technical Details

### Implementation Approach
- Use RIS parser library for file parsing
- Validate entries against Zotero schema
- Batch insert references via Django ORM
- Display progress bar for large files

### API Endpoints
- POST /api/projects/{id}/references/upload/
- Response: {success: boolean, imported_count: number, errors: []}

### Database Changes
- No schema changes required
- Uses existing Reference model

### Dependencies
- Depends on ECD-123 (Reference validation service)
- Blocks ECD-456 (Bulk reference export)
```

### Labels and Components

**Common Labels:**
- `bug` - Defects and issues
- `enhancement` - New features
- `tech-debt` - Code quality improvements
- `documentation` - Docs updates
- `urgent` - High-priority items
- `blocked` - Waiting on external dependency
- `research` - Investigation needed
- `quick-win` - Small, easy improvements

**Components (by area):**
- `frontend` - UI/Vue.js work
- `backend` - Django/Python work
- `api` - API endpoints
- `database` - DB schema/migrations
- `infrastructure` - Deployment/DevOps
- `word-addon` - Microsoft Word integration
- `authentication` - Auth/permissions

## Ticket Workflow Best Practices

### Status Workflow

**Typical Flow:**
```
To Do → In Progress → In Review → In QA → Pending Approval → Done
             ↓
          Blocked (temporary)
```

**Status Definitions:**

**To Do**
- Ticket is ready to be worked on
- Has acceptance criteria
- Dependencies are resolved
- Developer assigned (optional)

**In Progress**
- Developer actively coding
- Git branch exists with ticket number
- Regular commits happening
- Daily progress updates in comments

**In Review**
- PR opened and linked to ticket
- Code review requested
- Developer available to address feedback
- PR meets quality standards

**In QA**
- Code merged to staging
- QA team testing functionality
- Test cases executed
- Bugs logged if found

**Pending Approval**
- Functionality complete and tested
- Awaiting Product Manager sign-off
- Demo scheduled or completed
- Ready for production deployment

**Done**
- All acceptance criteria met
- Code in production
- Product Manager approved
- Documentation updated

**Blocked**
- Cannot progress due to external dependency
- Blocker clearly documented in comments
- Daily updates required (SLA requirement)
- Expected resolution date noted

### Workflow Best Practices

**Moving to "In Progress":**
- Ensure you have capacity to work on it
- Create git branch following naming convention
- Add comment with implementation approach
- Update if approach changes

**Moving to "In Review":**
- PR must be opened first
- Link PR in ticket
- Tag reviewers in Jira comment
- Self-review code before requesting review

**Moving to "Blocked":**
- Add detailed comment explaining blocker
- Tag person/team who can unblock
- Estimate resolution timeframe
- Move back ticket to "In Progress" when unblocked
- Provide daily updates (SLA requirement)

**Moving to "Done":**
- All acceptance criteria checked off
- Product Manager approval documented
- Code deployed to production
- Add closing comment summarizing work

## Comment Etiquette

### Professional Commenting

**Good Comments:**
✅ "Implementation complete. Ready for review. PR: #123"
✅ "Blocked on backend API endpoint. @backend-dev, ETA for ECD-456?"
✅ "Found edge case during testing: [description]. Creating subtask to handle it."
✅ "Responded to all review feedback. Re-review requested."

**Bad Comments:**
❌ "Done"
❌ "Working on it"
❌ "This is broken"
❌ "@everyone URGENT"

### Status Update Comments

**Template:**
```markdown
## Status Update - [Date]

**Progress:**
- Completed authentication flow
- Implemented OAuth token refresh
- 80% done with UI integration

**Blockers:**
- None

**Next Steps:**
- Complete UI integration
- Write unit tests
- Request code review

**ETA:** Oct 22, 2025
```

### Blocker Reporting

**Template:**
```markdown
⚠️ **BLOCKED** - Waiting on [dependency]

**Blocker Details:**
- Cannot proceed without [specific requirement]
- Blocked since: Oct 19, 2025
- Required from: @developer / @team

**Impact:**
- Sprint timeline at risk if not resolved by [date]
- Currently working on [alternative task]

**Estimated Unblock Date:** Oct 21, 2025
```

### Tagging Best Practices

**When to Tag:**
- Asking direct question to specific person
- Requesting review or approval
- Escalating blocker
- Notifying stakeholder of important update

**When NOT to Tag:**
- General status updates
- FYI comments
- Self-notes
- Asking questions Google can answer

**Format:**
- Use Jira account ID: `[~accountId:xxxxx]`
- Be specific about what you need: "[@person], can you review the API contract in comment above?"
- Don't tag multiple people unless all need to respond

## Linking and Relationships

### Link Types

**Blocks / Is Blocked By**
- This ticket prevents another from starting
- Example: "ECD-123 blocks ECD-456" (Auth must complete before feature)

**Relates To**
- General association between tickets
- Example: "ECD-123 relates to ECD-789" (both in same feature area)

**Duplicates / Is Duplicated By**
- Two tickets describing same work
- Close duplicate, keep one active

**Parent / Subtask**
- Large ticket broken into smaller tasks
- Subtasks roll up to parent

**Epic Link**
- Story belongs to larger epic
- Use custom field `customfield_10014`

### Linking Best Practices

**When Creating Subtasks:**
- Parent ticket becomes container
- Each subtask is independent work item
- All subtasks must complete for parent to close
- Limit to 3-7 subtasks per parent

**When Using Blockers:**
- Be explicit about what's blocking
- Add comment explaining dependency
- Update when blocker is resolved
- Monitor blocked items via JQL: `project = ECD AND status = Blocked`

## JQL (Jira Query Language)

### Common Queries

**Current Sprint Tickets:**
```jql
project = ECD AND sprint in openSprints()
```

**My Open Tickets:**
```jql
project = ECD AND assignee = currentUser() AND status != Done
```

**Blocked Tickets:**
```jql
project = ECD AND status = Blocked ORDER BY created ASC
```

**Overdue Tickets (no activity in 3 days):**
```jql
project = ECD AND status = "In Progress" AND updated < -3d
```

**High Priority Bugs:**
```jql
project = ECD AND type = Bug AND priority in (Highest, High) AND status != Done
```

**Epic Stories:**
```jql
project = ECD AND "Epic Link" = ECD-77
```

**Unassigned To Do Items:**
```jql
project = ECD AND status = "To Do" AND assignee is EMPTY
```

### Advanced JQL

**Tickets Without Epic:**
```jql
project = ECD AND "Epic Link" is EMPTY AND type = Story
```

**Sprint Burndown (by status):**
```jql
project = ECD AND sprint in openSprints() ORDER BY status, priority DESC
```

**Code-Ticket Gaps (In Progress but no updates):**
```jql
project = ECD AND status = "In Progress" AND updated < -2d
```

**PR Review Bottleneck:**
```jql
project = ECD AND status = "In Review" AND updated < -2d
```

### JQL Best Practices

- Save frequently used queries as filters
- Share filters with team for consistency
- Use ORDER BY for better readability
- Combine with dashboards for visualization
- Use relative dates (`-1d`, `-1w`) for dynamic queries

## Custom Fields

### Common Custom Fields

**Epic Link** (`customfield_10014`)
- Links story to parent epic
- Required for epic progress tracking
- Set during story creation

**Story Points** (`customfield_10016`)
- Relative size estimate
- Used for velocity tracking
- Set during sprint planning

**Sprint** (`customfield_10020`)
- Assigns ticket to sprint
- Auto-managed by sprint board
- Can be set via JQL

### Using Custom Fields in JQL

```jql
# Stories in specific epic
"Epic Link" = ECD-77

# High point stories
"Story Points" > 5

# Stories not in any sprint
sprint is EMPTY AND type = Story
```

## Dashboard Best Practices

### Useful Gadgets

**Sprint Health Dashboard:**
- Sprint burndown chart
- Sprint velocity chart
- Days remaining in sprint
- Blocked items list

**Developer Dashboard:**
- Assigned to me (current sprint)
- Recently updated tickets
- Tickets in review
- Blockers I'm waiting on

**PM Dashboard:**
- Epic progress bars
- Sprint completion rate
- SLA compliance metrics
- Bug trend chart

### Dashboard Tips

- One dashboard per persona (Dev, PM, QA)
- Update gadgets weekly to stay relevant
- Share dashboards with team
- Use color coding for priorities
- Keep gadget count under 10 for performance

## Notification Management

### When to Watch a Ticket

**Always Watch:**
- Tickets you created
- Tickets assigned to you
- Tickets you're actively reviewing
- Blocked tickets you're waiting on

**Don't Watch:**
- Every ticket you comment on once
- Entire epics (too noisy)
- Tickets you're just curious about

### Managing Notification Overload

**Personal Settings:**
- Disable "mentioned in a comment" emails (use @mentions sparingly)
- Enable daily digest instead of real-time emails
- Set up filters to route Jira emails to folder
- Use "watch" strategically, not automatically

## Ticket Hygiene

### Regular Maintenance

**Daily:**
- Update tickets you're working on
- Respond to comments/questions
- Move tickets through workflow promptly

**Weekly:**
- Review assigned tickets for stale items
- Close tickets that are actually done
- Un-assign tickets you won't work on
- Update estimates if scope changes

**Sprint Planning:**
- Close or defer incomplete tickets
- Remove labels that are no longer relevant
- Archive old discussions
- Update epic links if priorities changed

### Ticket Anti-Patterns

❌ **Zombie Tickets** - In Progress for months, no updates
❌ **Kitchen Sink Tickets** - Trying to do too many things in one ticket
❌ **Novel-Length Descriptions** - Descriptions should be concise, use attachments for details
❌ **Vague Acceptance Criteria** - "Make it work" is not criteria
❌ **Missing Context** - No description, no AC, just a title
❌ **Eternal Blockers** - Blocked for weeks without escalation

---

**This skill enables the PM agent to understand and enforce Jira best practices, ensuring tickets are well-structured, workflows are followed, and team collaboration is effective.**