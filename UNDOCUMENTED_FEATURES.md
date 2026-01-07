# Undocumented Functionality in Remington

**Last Updated:** January 6, 2026

This document lists all functionality that exists in the codebase but is NOT documented in the main README. Use this as a comprehensive test checklist when deploying to new environments.

---

## ❌ NOT Documented in README (but exists in codebase)

### 1. **Confluence Monitor**
- **Location:** `src/monitors/confluence_monitor.py`
- **What it does:** Monitors Confluence pages for @mentions of the bot
- **Status:** Implemented but not mentioned in README
- **How it works:** Polls Confluence API for page updates mentioning bot account
- **Test:** Post @mention in Confluence page, verify bot responds

### 2. **Product Manager Agent**
- **Location:** `.claude/agents/product-manager/`
- **What it does:**
  - Transforms user requests into well-structured Jira tickets
  - Creates bugs, stories, and epics from natural language
  - Uses templates for consistent formatting
- **Workflows:** `bug-generation`, `story-generation`, `epic-generation`
- **Trigger:** User tags @remington with "create a ticket", "file a bug", etc.
- **Templates:**
  - `.claude/agents/product-manager/templates/bug-template.md`
  - `.claude/agents/product-manager/templates/story-template.md`
  - `.claude/agents/product-manager/templates/epic-template.md`
- **Test:** Ask bot "create a bug report for login failing after password reset"

### 3. **Release Notes Generator Agent**
- **Location:** `.claude/agents/release-notes-generator/AGENT.md`
- **What it does:**
  - Auto-generates customer-facing release notes from Jira completed issues
  - Posts to Confluence in structured format
  - Runs during sprint close or on-demand
- **Command:** `/release-notes` (via `.claude/commands/release-notes.md`)
- **Output:** Creates Confluence pages under "Release Ops" space
- **Test:** Run `/release-notes` command, verify Confluence page created

### 4. **User-Facing Commands** (3 commands)
- **Location:** `.claude/commands/`
- **Available commands:**
  1. `/idea` - Capture product improvement ideas (`.claude/commands/idea.md`)
  2. `/future` - Add items to future backlog (`.claude/commands/future.md`)
  3. `/release-notes` - Generate release notes (`.claude/commands/release-notes.md`)
- **How to use:** Tag @remington with the command (e.g., "@remington /idea add dark mode")
- **Test:** Try each command in Slack or Jira

### 5. **Utility Scripts** (5 scripts not mentioned)
**Location:** `scripts/utilities/`

1. **dor_enforcement.py** - Definition of Ready enforcement
   - Validates tickets meet DoR criteria before sprint starts
   - Checks: acceptance criteria, story points, assignee, etc.

2. **generate_release_notes.py** - Release notes generation script
   - CLI tool for generating release notes
   - Works with release-notes-generator agent

3. **lookup_slack_ids.py** - Slack user ID lookup
   - Finds Slack user IDs from display names
   - Useful for @mention formatting

4. **sla_alert_tracker.py** - SLA violation tracking/deduplication
   - Ensures same violation doesn't alert multiple times
   - Tracks escalation history

5. **sync_team_from_confluence.py** - Team roster sync from Confluence
   - Pulls team member list from Confluence page
   - Auto-updates team roster configuration

### 6. **Additional Workflows** (11 total, only 3 mentioned in README)
**Location:** `.claude/workflows/`

**Documented in README:**
- `standup-analysis.md` - Daily standup
- `sla-monitoring.md` - SLA checks
- ~~`sprint-burndown.md` - Sprint analysis~~ (mentioned in README but `run_agent.py` doesn't support it!)

**NOT documented:**
1. `developer-productivity-audit.md` - Detailed code quality analysis
2. `jira-sprint-search.md` - Advanced sprint queries
3. `manual-productivity-audit.md` - One-off developer audits
4. `pr-git-branch-analysis.md` - PR-to-branch correlation checking
5. `pr-review-automation.md` - Automated PR code reviews
6. `release-notes-generation.md` - Release notes workflow
7. `timesheet-code-correlation.md` - Timesheet vs code output validation
8. `standup-command.md` - Standup invocation procedures

### 7. **MCP Tool Integration** (Partially Documented)
- **What:** Direct integration with Atlassian MCP tools for API access
- **Tools available:**
  - `mcp__atlassian__searchJiraIssuesUsingJql`
  - `mcp__atlassian__getJiraIssue`
  - `mcp__atlassian__createJiraIssue`
  - `mcp__atlassian__editJiraIssue`
  - `mcp__atlassian__addCommentToJiraIssue`
  - `mcp__atlassian__transitionJiraIssue`
  - `mcp__atlassian__searchConfluenceUsingCql`
  - `mcp__atlassian__getConfluencePage`
  - `mcp__atlassian__updateConfluencePage`
- **Clarification:** README has section "Why We Don't Use MCP" but we DO use Atlassian MCP for API access. We don't use it for local filesystem or authentication servers.

### 8. **Additional Sub-Agents** (8 total, only 6 in README)
**Location:** `.claude/agents/`

**README mentions 6:**
- standup-orchestrator
- sprint-analyzer
- sla-monitor
- developer-auditor
- jira-manager
- deadline-risk-analyzer

**NOT mentioned:**
- **product-manager** - Ticket creation from natural language requests
- **release-notes-generator** - Automated release notes to Confluence

---

## ✅ Documented but INCOMPLETE/INCORRECT in README

### 1. **run_agent.py Commands**
- **README says:** Supports `standup`, `sla-check`, AND `sprint-analysis`
- **REALITY:** Only supports `standup` and `sla-check`
- **Fix needed:** Either:
  - Remove `sprint-analysis` from README examples, OR
  - Implement `sprint-analysis` command in `run_agent.py`

### 2. **MCP Usage Statement**
- **README says:** "Why We Don't Use MCP" (entire section explaining we don't use it)
- **REALITY:** We DO use Atlassian MCP for Jira/Confluence API access
- **Clarification needed:** We don't use MCP for:
  - Local filesystem servers
  - Authentication/OAuth flows
  - Node.js runtime servers
- **But we DO use:** Atlassian MCP for API tool access (see item #7 above)

### 3. **Number of Sub-Agents**
- **README says:** "6 specialized sub-agents"
- **REALITY:** 8 sub-agents (product-manager and release-notes-generator missing)

### 4. **Number of Monitors**
- **README says:** Monitors Jira, Slack, Bitbucket
- **REALITY:** Also monitors Confluence (4 monitors total)

---

## 📊 Comprehensive Test Plan for Deployment

Use this checklist when deploying to a new environment:

### Phase 1: Core Monitoring (Priority: Critical)

- [ ] **Jira Monitor**
  - Post @mention in Jira ticket
  - Verify bot responds within 60 seconds
  - Check database deduplication (same comment shouldn't trigger twice)

- [ ] **Slack Monitor**
  - Post @mention in Slack channel
  - Verify bot responds in thread
  - Test multiple rapid mentions (deduplication)

- [ ] **Bitbucket Monitor**
  - Post comment on PR with @mention
  - Verify bot responds
  - Test PR review workflow

- [ ] **Confluence Monitor** (undocumented!)
  - Post @mention in Confluence page
  - Verify bot detects and responds
  - Check Confluence API permissions

### Phase 2: Automated Workflows (Priority: High)

- [ ] **Daily Standup**
  - Run: `python run_agent.py standup`
  - Verify 5-section report posts to Slack
  - Check all metrics populate correctly

- [ ] **SLA Monitoring**
  - Run: `python run_agent.py sla-check`
  - Create test SLA violation (PR waiting 3 days)
  - Verify escalation messages sent

- [ ] **Sprint Analysis** (if implemented)
  - Run: `python run_agent.py sprint-analysis`
  - OR verify this command doesn't exist

### Phase 3: Sub-Agents (Priority: Medium)

- [ ] **Product Manager Agent** (undocumented!)
  - Test: "@remington create a bug for login failing"
  - Verify Jira ticket created with proper format
  - Check all required fields populated

- [ ] **Release Notes Generator** (undocumented!)
  - Test: "@remington /release-notes"
  - Verify Confluence page created
  - Check release notes formatting

- [ ] **Jira Manager**
  - Test ticket creation
  - Test status transitions
  - Test comment posting with @mentions

- [ ] **Developer Auditor**
  - Run productivity audit workflow
  - Verify timesheet correlation works
  - Check code complexity analysis

- [ ] **Deadline Risk Analyzer**
  - Create ticket with due date tomorrow
  - Verify appears in standup report
  - Check risk level calculation

- [ ] **SLA Monitor**
  - Test all 5 SLA types
  - Verify 4-level escalation matrix
  - Check deduplication working

- [ ] **Sprint Analyzer**
  - Query sprint burndown
  - Check velocity calculations
  - Verify epic progress tracking

- [ ] **Standup Orchestrator**
  - Verify 5-part analysis runs
  - Check integration with other agents
  - Confirm Slack posting works

### Phase 4: User Commands (Priority: Low)

- [ ] **/idea command** (undocumented!)
  - Test: "@remington /idea add export to Excel"
  - Verify idea captured

- [ ] **/future command** (undocumented!)
  - Test: "@remington /future mobile app support"
  - Verify added to backlog

- [ ] **/release-notes command** (tested in Phase 3)

### Phase 5: Utility Scripts (Priority: Low)

- [ ] **Definition of Ready Enforcement**
  - Run: `python scripts/utilities/dor_enforcement.py`
  - Verify ticket validation works

- [ ] **Team Roster Sync**
  - Run: `python scripts/utilities/sync_team_from_confluence.py`
  - Verify team members loaded

- [ ] **SLA Alert Tracker**
  - Create duplicate SLA violation
  - Verify only one alert sent

- [ ] **Slack ID Lookup**
  - Run: `python scripts/utilities/lookup_slack_ids.py`
  - Verify user IDs returned

- [ ] **Release Notes Generator Script**
  - Run: `python scripts/utilities/generate_release_notes.py`
  - Verify output matches Confluence format

---

## 🔧 Recommended Documentation Updates

### High Priority

1. **Add Confluence to monitoring section**
   - Update "What It Does" to mention 4 platforms (not 3)
   - Add Confluence interaction example
   - Document Confluence setup in installation guide

2. **Document Product Manager Agent**
   - Add to sub-agents list (update 6 → 8)
   - Provide examples of ticket creation requests
   - Show generated ticket format

3. **Document Release Notes Generator**
   - Add to automated workflows section
   - Explain `/release-notes` command
   - Show example Confluence output

4. **Fix MCP clarification**
   - Keep "Why We Don't Use MCP" section BUT
   - Add clarification that we DO use Atlassian MCP for API access
   - Explain the distinction (no local servers, but yes API tools)

5. **Fix run_agent.py commands**
   - Remove `sprint-analysis` from all examples OR implement it
   - Verify all documented commands actually work

### Medium Priority

6. **Document all 3 user commands**
   - Add section on `/idea`, `/future`, `/release-notes`
   - Provide usage examples
   - Explain where data is stored

7. **Document utility scripts**
   - Add "Advanced Tools" section
   - List all 5 utility scripts with descriptions
   - Provide usage examples

### Low Priority

8. **Create comprehensive test checklist**
   - Add this document to docs/testing/
   - Reference from main README
   - Include in deployment guides

---

## 📝 Summary

**Total Undocumented Features:**
- 1 monitor (Confluence)
- 2 sub-agents (Product Manager, Release Notes Generator)
- 3 user commands (/idea, /future, /release-notes)
- 5 utility scripts
- 8+ workflows not mentioned

**Critical Issues:**
1. README says "6 sub-agents" but there are 8
2. README says "don't use MCP" but we DO for Atlassian APIs
3. README shows `sprint-analysis` command that doesn't exist in `run_agent.py`
4. Confluence monitoring completely missing from README

**When deploying to production or test environment, ensure ALL features listed in this document are tested, not just those in the README.**
