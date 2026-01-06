# PM Agent - Comprehensive Test Plan

## Test Scenarios for Approval

This document outlines all PM processes and functionality that should be tested before deployment.

---

## 1. POLLING & EVENT DETECTION

### 1.1 Slack Polling
- [ ] **Test 1.1.1**: Slack monitor initializes with credentials
- [ ] **Test 1.1.2**: Poll returns list of new mentions
- [ ] **Test 1.1.3**: No duplicate processing (database tracking works)
- [ ] **Test 1.1.4**: Polling completes in < 5 seconds
- [ ] **Test 1.1.5**: Handles Slack API rate limits gracefully
- [ ] **Test 1.1.6**: Database persists across restarts

**Expected Behavior:**
- Poll every 15 seconds (configurable)
- Detect `@CiteMed PM` mentions in configured channel
- Track processed messages in SQLite (`.claude/data/bot-state/slack_state.db`)
- Never reprocess same message

---

### 1.2 Jira Polling
- [ ] **Test 1.2.1**: Jira monitor initializes with Atlassian credentials
- [ ] **Test 1.2.2**: Poll detects new comments on ECD tickets
- [ ] **Test 1.2.3**: No duplicate processing
- [ ] **Test 1.2.4**: Polling completes in < 5 seconds
- [ ] **Test 1.2.5**: Correctly parses ADF (Atlassian Document Format) comments
- [ ] **Test 1.2.6**: Detects service account mentions vs general comments

**Expected Behavior:**
- Poll every 30 seconds (backup to webhooks)
- Use JQL to find recent comments: `project = ECD AND updated >= -30s`
- Track processed comment IDs in SQLite (`.claude/data/bot-state/jira_state.db`)
- Extract plain text from ADF JSON format

---

### 1.3 Bitbucket Polling
- [ ] **Test 1.3.1**: Bitbucket monitor initializes
- [ ] **Test 1.3.2**: Poll detects PR comments mentioning service account
- [ ] **Test 1.3.3**: Multi-repository support (citemed_web + word_addon)
- [ ] **Test 1.3.4**: No duplicate processing
- [ ] **Test 1.3.5**: Correctly identifies @mentions in PR comments

**Expected Behavior:**
- Poll every 30 seconds (backup to webhooks)
- Check configured repos: `citemed_web`, `word_addon`
- Track processed PR comment IDs per repo
- Detect service account email mentions

---

## 2. AI BOT PROJECT MANAGER (Intelligence Layer)

**Purpose:** This is the core intelligence that responds to comments and direct mentions using Claude Code as the reasoning engine.

### 2.1 Bot Initialization
- [ ] **Test 2.1.1**: Claude CLI is detected (`claude --version`)
- [ ] **Test 2.1.2**: Settings file exists (`.claude/settings.local.json`)
- [ ] **Test 2.1.3**: MCP servers are enabled (atlassian, filesystem)
- [ ] **Test 2.1.4**: Fallback to SimpleOrchestrator if Claude Code unavailable

**Expected Behavior:**
- Verify Claude Code CLI 2.0+ installed
- Load MCP permissions from settings file
- Graceful degradation if unavailable

---

### 2.2 Business Context & Agent Knowledge
- [ ] **Test 2.2.1**: Reads agent file (`.claude/agents/jira-manager.md`)
- [ ] **Test 2.2.2**: Loads skills from `.claude/skills/`
- [ ] **Test 2.2.3**: Reads project context (`.claude/CLAUDE.md`)
- [ ] **Test 2.2.4**: Prompt includes agent-specific instructions

**Expected Behavior:**
- Prompt tells Claude Code to read agent instructions
- Agent has access to business rules, SLA definitions, team context

---

### 2.3 Smart Decision Making (MCP Tools)
- [ ] **Test 2.3.1**: Uses `mcp__atlassian__getJiraIssue()`
- [ ] **Test 2.3.2**: Uses `mcp__atlassian__searchJiraIssuesUsingJql()`
- [ ] **Test 2.3.3**: Uses `mcp__atlassian__addCommentToJiraIssue()`
- [ ] **Test 2.3.4**: Uses `mcp__atlassian__editJiraIssue()`
- [ ] **Test 2.3.5**: Uses `mcp__atlassian__lookupJiraAccountId()` for tagging
- [ ] **Test 2.3.6**: Uses `mcp__filesystem__read_text_file()` for reading codebase

**Expected Behavior:**
- Claude Code invokes MCP tools via subprocess
- Tools return real data from Jira/Bitbucket/Filesystem
- Results influence decision-making

---

### 2.4 Intelligent Response Generation
- [ ] **Test 2.4.1**: Posts intelligent response to Jira comments
- [ ] **Test 2.4.2**: Applies SLA rules (2-day comment response time)
- [ ] **Test 2.4.3**: Tags developers correctly using account IDs
- [ ] **Test 2.4.4**: Detects urgency level (soft reminder vs escalation)
- [ ] **Test 2.4.5**: Handles edge cases (Draft tickets, blocked tickets)

**Expected Behavior:**
- Responses demonstrate business context awareness
- Follow escalation tone guidelines (Level 1-4)
- Never hallucinate - use MCP tools to verify facts

---

## 3. PM ROUTINE TASKS

### 3.1 SLA Monitoring

#### 3.1.1 Jira Comment Response Time SLA
- [ ] **Test**: Detect comments > 2 business days old without response
- [ ] **Test**: Calculate business hours (exclude weekends)
- [ ] **Test**: Apply escalation matrix (Level 1: 1-2 days, Level 2: 3-4 days, etc.)
- [ ] **Test**: Post soft reminder (Level 1)
- [ ] **Test**: Post + Slack notification (Level 2)
- [ ] **Test**: Tag team lead (Level 3)
- [ ] **Test**: Escalate to leadership (Level 4)

**SLA Definition:**
- **Target:** 2 business days maximum
- **Scope:** Developer response to stakeholder/PM comments
- **Exceptions:** Blocked tickets, waiting on external dependencies

**Test Scenario:**
1. Create Jira ticket with comment from stakeholder
2. Wait 2.5 business days (mocked time)
3. Run SLA check
4. Verify Level 2 escalation posted to Jira + Slack

---

#### 3.1.2 PR Review Turnaround SLA
- [ ] **Test**: Detect PRs waiting > 48 hours for review
- [ ] **Test**: Identify PRs with no "approve" or "changes requested"
- [ ] **Test**: Escalate to reviewers
- [ ] **Test**: Tag alternate reviewer if primary unresponsive

**SLA Definition:**
- **Target:** 24-48 hours per PR policy
- **Scope:** Time from "Ready for Review" to first substantive review
- **Exceptions:** Major architectural PRs (up to 72 hours)

**Test Scenario:**
1. PR created and marked "Ready for Review"
2. 50 hours pass (mocked)
3. Run SLA check
4. Verify escalation comment posted to Bitbucket PR

---

#### 3.1.3 Blocked Ticket Updates SLA
- [ ] **Test**: Detect tickets in "Blocked" status > 2 days without update
- [ ] **Test**: Require daily updates from assignee
- [ ] **Test**: Escalate if no blocker resolution plan

**SLA Definition:**
- **Target:** Daily updates required
- **Scope:** Tickets in "Blocked" status or with blocker flag
- **Escalation:** After 2 days without update

---

#### 3.1.4 Pending Approval Duration SLA
- [ ] **Test**: Detect tickets in "Pending Approval" > 48 hours
- [ ] **Test**: Tag approver for action
- [ ] **Test**: Escalate to tech lead if unresponsive

**SLA Definition:**
- **Target:** 48 hours maximum
- **Scope:** Tickets in "Pending Approval" status
- **Escalation:** After 48 hours, escalate to approver

---

### 3.2 Sprint Health Monitoring

#### 3.2.1 Sprint Burndown Analysis
- [ ] **Test**: Calculate current sprint velocity
- [ ] **Test**: Compare to historical average
- [ ] **Test**: Predict sprint completion risk
- [ ] **Test**: Identify bottlenecks (tickets stuck in status)

**Process:**
1. Use JQL to get current sprint tickets
2. Calculate: `(Points Completed) / (Total Points) vs (Days Elapsed) / (Sprint Length)`
3. Flag if < 70% on track

**Test Scenario:**
- Sprint: 10 days, 40 points total
- Day 7: Only 15 points done (53% vs 70% expected)
- Agent should flag: "Sprint at risk - 15pts done, need 28pts by day 7"

---

#### 3.2.2 Workload Balance Analysis
- [ ] **Test**: Count in-progress tickets per developer
- [ ] **Test**: Identify developers with > 5 active tickets
- [ ] **Test**: Suggest rebalancing workload

**Process:**
1. Query: `assignee = "Mohamed" AND status = "In Progress"`
2. If count > 5: Flag for review
3. Suggest moving low-priority items to backlog

---

#### 3.2.3 Epic Progress Tracking
- [ ] **Test**: Map tickets to parent epics
- [ ] **Test**: Calculate epic completion percentage
- [ ] **Test**: Identify blocked epics

**Process:**
1. For each epic: Get child tickets
2. Calculate: `(Done tickets) / (Total tickets)`
3. Flag if < 50% complete and sprint ends in < 3 days

---

### 3.3 Developer Productivity Audit

#### 3.3.1 Timesheet vs Code Complexity
- [ ] **Test**: Read timesheet entries from `.claude/data/timesheets/`
- [ ] **Test**: Analyze actual commits using Filesystem MCP
- [ ] **Test**: Calculate code complexity score (lines changed, files touched)
- [ ] **Test**: Flag discrepancies (8 hours logged, 5-line change)
- [ ] **Test**: Recognize exceptional work (complex refactor, thorough testing)

**Process:**
1. Read timesheet: "Mohamed - 8 hours - ECD-123"
2. Use `mcp__filesystem__read_text_file()` to analyze commit
3. Calculate score: `lines_changed * file_count * complexity_factor`
4. Compare: logged hours vs expected hours for complexity
5. Flag if > 50% variance

**Test Scenarios:**
- **Gap**: 8 hours logged, 10-line trivial change → Flag for review
- **Exceptional**: 6 hours logged, 500-line refactor with tests → Recognize

---

#### 3.3.2 Ticket-to-Code Gap Detection
- [ ] **Test**: Find Jira tickets marked "Done" without merged PR
- [ ] **Test**: Find merged PRs without corresponding Jira ticket
- [ ] **Test**: Verify branch naming convention (`ECD-XXX-description`)

**Process:**
1. Query tickets: `status = Done AND updated >= -7d`
2. For each ticket, search git history for branch `ECD-XXX`
3. Flag if no matching branch/PR found

---

### 3.4 Daily Standup Orchestration

#### 3.4.1 5-Part Workflow
- [ ] **Test Part 1**: Sprint burndown analysis
- [ ] **Test Part 2**: Code-ticket gap detection
- [ ] **Test Part 3**: Developer productivity audit
- [ ] **Test Part 4**: Timesheet analysis
- [ ] **Test Part 5**: SLA violation monitoring

**Process:**
1. Run all 5 subagents sequentially
2. Compile comprehensive report
3. Post to Slack channel
4. Create Jira comment on standup ticket

**Expected Output:**
```markdown
# Daily Standup - 2025-11-08

## 📊 Sprint Health
- Velocity: 18/40 points (45% complete, Day 7/14)
- Status: ⚠️ Below target (need 70% by day 7)

## 🔍 SLA Violations
- ECD-456: Comment waiting 3 days (Level 2 escalation)
- PR #789: Review pending 52 hours

## 👥 Developer Updates
- Mohamed: 3 tickets in progress (ECD-123, ECD-124, ECD-125)
- Ahmed: Blocked on ECD-130 for 2 days

## ⚠️ Action Items
1. Review ECD-456 comment urgently
2. Assign reviewer to PR #789
3. Unblock ECD-130 or provide daily update
```

---

## 4. WEBHOOK HANDLING

### 4.1 Jira Webhooks
- [ ] **Test**: Receive webhook POST to `/webhooks/jira`
- [ ] **Test**: Parse `comment_created` event
- [ ] **Test**: Extract ADF comment body to plain text
- [ ] **Test**: Return 200 OK in < 100ms
- [ ] **Test**: Process in background task (non-blocking)
- [ ] **Test**: Log to database (`webhook_events` table)

**Webhook Flow:**
1. Jira POSTs to `/webhooks/jira`
2. FastAPI logs to database (webhook_id)
3. Returns 200 OK immediately
4. Background task → Orchestrator → Claude Code
5. Claude Code posts response to Jira

---

### 4.2 Bitbucket Webhooks
- [ ] **Test**: Receive PR comment webhook
- [ ] **Test**: Parse event type (comment created, PR updated)
- [ ] **Test**: Trigger orchestrator for PR review requests

---

### 4.3 Slack Webhooks
- [ ] **Test**: Handle URL verification challenge
- [ ] **Test**: Receive app_mention events

---

## 5. DATABASE & PERSISTENCE

### 5.1 Webhook Events Log
- [ ] **Test**: All webhooks logged to `webhook_events` table
- [ ] **Test**: Includes: source, event_type, payload, timestamp
- [ ] **Test**: Tracks processing status (pending/processed/failed)

---

### 5.2 Agent Cycles Log
- [ ] **Test**: All orchestrator cycles logged to `agent_cycles` table
- [ ] **Test**: Includes: trigger_type, trigger_data, claude_response, status
- [ ] **Test**: Queryable for audit trail

---

### 5.3 Bot State Databases
- [ ] **Test**: Slack: `slack_state.db` - processed message timestamps
- [ ] **Test**: Jira: `jira_state.db` - processed comment IDs
- [ ] **Test**: Bitbucket: `bitbucket_state.db` - processed PR comment IDs
- [ ] **Test**: Persistence across service restarts

---

## 6. ERROR HANDLING & RESILIENCE

### 6.1 API Failures
- [ ] **Test**: Handles Jira API 401 (expired token)
- [ ] **Test**: Handles Slack API rate limit (429)
- [ ] **Test**: Handles Bitbucket API timeout
- [ ] **Test**: Retries failed requests (max 2 retries)

---

### 6.2 Claude Code Failures
- [ ] **Test**: Handles Claude Code timeout (> 10 minutes)
- [ ] **Test**: Handles Claude Code error (invalid prompt)
- [ ] **Test**: Fallback to SimpleOrchestrator if Claude Code unavailable
- [ ] **Test**: Logs error to database

---

### 6.3 Database Failures
- [ ] **Test**: Creates database if doesn't exist
- [ ] **Test**: Handles locked database (retry)
- [ ] **Test**: Graceful degradation if database unreachable

---

## 7. PERFORMANCE

### 7.1 Polling Speed
- [ ] **Test**: Slack poll < 5 seconds
- [ ] **Test**: Jira poll < 5 seconds
- [ ] **Test**: Bitbucket poll < 5 seconds
- [ ] **Test**: No LLM cost if no new items

---

### 7.2 Webhook Response Time
- [ ] **Test**: Webhook returns 200 OK < 100ms
- [ ] **Test**: Background processing doesn't block server

---

### 7.3 Resource Usage
- [ ] **Test**: Memory usage < 200MB
- [ ] **Test**: CPU usage < 5% during polling (idle)
- [ ] **Test**: CPU spike during Claude Code processing (expected)

---

## 8. INTEGRATION TESTS

### 8.1 End-to-End Flows
- [ ] **Test E2E-1**: Jira comment → Poll → Detect → Process → Respond
- [ ] **Test E2E-2**: Slack mention → Poll → Detect → Process → Respond
- [ ] **Test E2E-3**: PR comment → Poll → Detect → Process → Respond
- [ ] **Test E2E-4**: Webhook → Process → Database log → Response

---

### 8.2 Multi-Component Tests
- [ ] **Test**: Polling + Webhooks (hybrid architecture)
- [ ] **Test**: Multiple monitors running concurrently
- [ ] **Test**: Database isolation (no cross-contamination)

---

## SUMMARY

**Total Test Scenarios: ~100+**

**Categories:**
1. Polling & Event Detection (18 tests)
2. AI Bot Project Manager - Intelligence Layer (17 tests)
3. PM Routine Tasks (24 tests)
4. Webhook Handling (8 tests)
5. Database & Persistence (9 tests)
6. Error Handling (10 tests)
7. Performance (7 tests)
8. Integration (6 tests)

**Approval Required:**
Please review this test plan and confirm:
1. ✅ All critical PM processes are covered
2. ✅ Test scenarios are realistic
3. ✅ Priority order for implementation

Once approved, I'll implement the test suite with:
- Real API integration tests
- Mocked response tests
- Performance benchmarks
- End-to-end validation
