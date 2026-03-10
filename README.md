<div align="center">
  <img src="assets/remington_logo_final.svg" alt="Remington Logo" width="200"/>

  # Remington - Autonomous Project Manager Agent

  > An AI-powered project management assistant that monitors Jira, Bitbucket, and Slack to automate workflows, enforce SLAs, and keep your team on track.

  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Claude](https://img.shields.io/badge/powered%20by-Claude%20AI-orange.svg)](https://www.anthropic.com/)
</div>

---

## ⚡ Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/ethandrower/remington.git
cd remington
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install bitbucket-cli (required dependency)
# See: https://github.com/ethandrower/bitbucket-cli-for-claude-code
pip install git+https://github.com/ethandrower/bitbucket-cli-for-claude-code.git

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration

# 5. Start the service
python src/pm_agent_service.py
```

That's it! Remington is now monitoring Jira, Slack, and Bitbucket 24/7.

---

## 🎯 What It Does

Remington is an autonomous agent that acts as your project manager's assistant. It runs 24/7, monitoring your team's activities and taking action when needed.

### Core Capabilities

- **📊 SLA Enforcement** - Tracks 5 types of SLAs and escalates violations automatically
- **💬 Smart Responses** - Tag `@remington` in Jira/Slack/Bitbucket for context-aware answers
- **📈 Daily Standups** - Automated standup reports every weekday at 9 AM
- **🔍 Sprint Health** - Tracks burndown, velocity, and identifies bottlenecks
- **⏰ Deadline Monitoring** - Flags at-risk tickets before they're overdue
- **✅ PR Reviews** - Monitors pull requests and nudges for timely reviews

### How to Interact with Remington

Tag Remington in any comment to get instant, context-aware responses.

#### Example: Jira Comment Interaction

**You comment on PROJ-456:**
```
@remington what's blocking this ticket?
```

**Remington responds (30-60 seconds later):**
```
Hi @john.doe! I've reviewed PROJ-456 and found the following blockers:

🚧 Current Blockers:
• Waiting on API endpoint design from backend team (mentioned in comment from Jan 3)
• Database schema needs approval from @tech-lead (flagged in description)

📋 Recent Activity:
• Last updated 2 days ago by @jane.smith
• Status: Blocked → waiting for dependencies
• No commits in last 5 days

💡 Recommendation:
1. Ping @backend-team in #engineering channel about API design
2. Schedule 15-min sync with @tech-lead for schema approval
3. Consider splitting frontend work into separate ticket to unblock progress

Would you like me to create follow-up tickets for the unblocked work?
```

#### Example: Slack Thread Interaction

**You post in #engineering:**
```
@Remington what's the status of PROJ-123?
```

**Remington responds in thread:**
```
📊 PROJ-123: Implement user authentication

Status: In Progress
Assignee: @developer
Due Date: Tomorrow (Jan 7, 2026) ⚠️

Recent Activity:
✅ Last commit: 2 hours ago (OAuth2 implementation)
✅ PR opened: PR-89 "Add Google OAuth"
⚠️ Still missing: Microsoft OAuth provider (per requirements)

Timeline Risk: MEDIUM
• 1 day remaining
• Core work complete, but additional provider needed
• May need deadline extension or scope reduction

Next Steps:
1. Confirm with @product-manager if Microsoft OAuth is required for v1
2. If yes: Request 2-day extension
3. If no: Mark as complete and create follow-up ticket

Jira Link: https://your-company.atlassian.net/browse/PROJ-123
```

#### Example: Bitbucket PR Interaction

**You comment on PR-45:**
```
@remington review this code
```

**Remington posts review (60-90 seconds later):**
```
Code Review for PR-45: Add payment processing

✅ Overall: Looks good with minor suggestions

🔒 Security:
• Consider using environment variables for API keys instead of config.py
• Add input validation for payment amounts (prevent negative values)

🎯 Best Practices:
• Add error handling for payment gateway timeouts
• Consider adding retry logic with exponential backoff

📝 Code Quality:
• Well-structured and readable
• Good test coverage (85%)
• Documentation is clear

✨ Nice work:
• Proper use of async/await patterns
• Comprehensive error messages
• Good logging for debugging

Recommendation: ✅ Approve with minor fixes

@author please address security items before merge.
```

**Important - Mention Formats:**
- **Jira**: `@remington` (uses Jira account ID internally)
- **Slack**: `@Remington` (your bot's display name)
- **Bitbucket**: `@{bot-account-uuid}` (format varies by platform)

---

## 📋 SLA Monitoring & Enforcement

Remington automatically monitors these Service Level Agreements:

| SLA Type | Target | What It Monitors | Escalation |
|----------|--------|------------------|------------|
| **Jira Comment Response** | 2 business days | Developer responses to stakeholder questions | 4-level escalation (comment → Slack → team → leadership) |
| **PR Review Turnaround** | 24-48 hours | Time from "Ready for Review" to first review | Slack notification to reviewer |
| **PR Code Activity** | 2 business days | PRs "In Progress" must show commits | Slack reminder to PR author |
| **Blocked Ticket Updates** | Daily | Tickets in "Blocked" status need daily updates | Daily Jira comment reminder |
| **Pending Approval Duration** | 48 hours | Tickets waiting for approval/sign-off | Slack notification to approver |

**Business Hours:**
- Default: Monday-Friday, 9 AM - 5 PM (configurable timezone)
- Holidays excluded (configurable in `.env`)
- SLA timers only count business hours

### 4-Level Escalation Matrix

When an SLA is violated, Remington escalates automatically:

| Level | Timing | Action | Where |
|-------|--------|--------|-------|
| **Level 1** | 0-1 days overdue | Friendly reminder | Jira comment only |
| **Level 2** | 1-2 days overdue | Direct request | Jira comment + Slack DM |
| **Level 3** | 2-3 days overdue | Team escalation | Jira + Slack + @tech-lead |
| **Level 4** | 3+ days overdue | Leadership alert | Jira + Slack + @leadership |

#### Example SLA Violation Messages

**Level 1 - Jira Comment (Friendly Reminder):**
```
👋 Hi @developer!

Just a friendly reminder - this comment has been waiting for a response for 1 business day.

Original question from @stakeholder (Jan 5):
"Can we add export to PDF feature by end of sprint?"

Could you provide a quick update when you have a moment? Thanks!

⏱️ SLA: 2 business days (1 day elapsed)
```

**Level 2 - Jira + Slack DM:**

*Jira Comment:*
```
⚠️ Hi @developer,

This comment is now 2 business days overdue for a response.

Original question from @stakeholder (Jan 3):
"What's the ETA on the API integration?"

Could you please prioritize a response today? I've also sent you a Slack DM.

⏱️ SLA: 2 business days (2 days overdue)
📌 Escalation: Level 2
```

*Slack DM to developer:*
```
Hi! 👋

PROJ-456 has a comment that needs your attention - it's now 2 days overdue.

Question from @stakeholder: "What's the ETA on the API integration?"

Link: https://your-company.atlassian.net/browse/PROJ-456

Could you please respond today? Let me know if you need help!
```

**Level 3 - Team Escalation (Jira + Slack Channel):**

*Jira Comment:*
```
🚨 ESCALATION - Level 3

@developer, @tech-lead - This comment requires immediate attention.

Original question from @stakeholder (Jan 1):
"Is this feature ready for release?"

⏱️ Status:
• SLA Target: 2 business days
• Time Overdue: 3 business days
• Escalation Level: 3 of 4

@tech-lead: Please ensure this gets a response today or reassign if needed.
@developer: If you're blocked, please update the ticket status.

📍 Link: PROJ-456
```

*Slack Message in #engineering:*
```
🚨 SLA Escalation - Level 3

PROJ-456 needs immediate attention from @developer

• Comment from @stakeholder has been waiting 3 business days
• Question: "Is this feature ready for release?"
• SLA Target: 2 business days (3 days overdue)

@tech-lead FYI - may need reassignment or prioritization

Link: https://your-company.atlassian.net/browse/PROJ-456
```

**Level 4 - Leadership Alert:**

*Slack Message in #engineering + #leadership:*
```
🚨🚨 CRITICAL SLA VIOLATION - Level 4 🚨🚨

PROJ-456 has exceeded maximum escalation threshold

📋 Details:
• Stakeholder: @stakeholder
• Developer: @developer
• Question: "Is this feature ready for release?"
• SLA Target: 2 business days
• Time Overdue: 4+ business days

⚠️ This may impact sprint commitments and stakeholder trust.

@leadership @tech-lead - Immediate action required
@developer - Please respond ASAP or escalate blockers

Link: https://your-company.atlassian.net/browse/PROJ-456
```

---

## 🤖 Automated Workflows

### Daily Standup (Weekdays at 9 AM)

Every weekday at 9 AM, Remington automatically posts a comprehensive standup report to your configured Slack channel. This report is the **heartbeat** of your sprint - it surfaces issues before they become blockers.

#### What Gets Analyzed

The standup workflow runs 5 sub-analyses:

1. **Code-Ticket Gap Detection** - Finds commits without associated Jira tickets (shadow work)
2. **Productivity Audit** - Reviews code complexity vs timesheet entries over last 7 days
3. **Team Capacity Analysis** - Checks if team is overloaded or underutilized
4. **SLA Compliance Check** - Lists all active violations and pending escalations
5. **Deadline Risk Assessment** - Flags tickets at risk of missing due dates

#### Example Daily Standup Report

**Posted to #standup channel at 9:00 AM:**

```
🌅 Daily Standup Report - Monday, January 6, 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SPRINT HEALTH: Sprint 42 (Jan 1-14, 2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Progress: ████████████░░░░░░░░ 58% (23/40 points)
Velocity: 16 points/week (avg: 18) - slightly below target
Days Remaining: 9 days
Forecast: ✅ On track for 85% completion

🎯 Top Priorities Today:
1. PROJ-456 - Payment gateway integration (8 points, due Wed)
2. PROJ-789 - Fix login bug (5 points, BLOCKED ⚠️)
3. PROJ-234 - User profile page (3 points, due Friday)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 SLA VIOLATIONS (3 active)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL (Level 3):
• PROJ-456: PR review waiting 3 business days
  - PR-89 by @developer-a needs review from @tech-lead
  - Action: Escalated to #engineering + @tech-lead
  - Link: https://bitbucket.org/yourcompany/repo/pull/89

⚠️ MEDIUM (Level 2):
• PROJ-789: Blocked ticket with no update for 2 days
  - Waiting on backend API from @developer-b
  - Action: Jira comment + Slack DM sent
  - Link: https://your-company.atlassian.net/browse/PROJ-789

ℹ️ LOW (Level 1):
• PROJ-123: Comment response overdue by 1 day
  - Stakeholder question about PDF export timeline
  - Action: Friendly Jira reminder posted
  - Link: https://your-company.atlassian.net/browse/PROJ-123

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ DEADLINE RISKS (2 tickets at risk)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 HIGH RISK - PROJ-456 (due in 2 days):
• Status: In Progress (75% complete per last update)
• Last commit: 18 hours ago
• Risk: PR-89 still needs review (see SLA violations above)
• Recommendation: Expedite PR review or request 2-day extension

🟡 MEDIUM RISK - PROJ-234 (due in 5 days):
• Status: In Progress
• Last commit: 5 days ago ⚠️ (stale)
• Assignee: @developer-c
• Risk: No recent activity, may be blocked
• Recommendation: Check in with @developer-c for status update

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 TEAM ACTIVITY (Last 24 Hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Code Activity:
• 18 commits across 3 repositories
• 4 PRs opened, 3 PRs merged
• 127 lines added, 43 lines removed
• Most active: @developer-a (8 commits)

Jira Activity:
• 12 tickets updated
• 3 tickets moved to Done
• 2 new tickets created
• 5 comments posted

Top Contributors:
🥇 @developer-a - 8 commits, 2 PRs merged
🥈 @developer-b - 6 commits, 1 PR opened
🥉 @developer-c - 4 commits, 1 ticket completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 CODE-TICKET GAP ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Found 2 commits without Jira ticket references:

1. Commit abc123f by @developer-b (yesterday 3:45 PM)
   "Fix typo in user service"
   → Consider creating ticket or adding to existing work log

2. Commit def456a by @developer-c (yesterday 11:20 AM)
   "Update dependencies"
   → Consider adding PROJ-MAINTENANCE-456 reference

💡 Reminder: Include ticket number in commit messages (e.g., "PROJ-123: Add feature")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ACTION ITEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. @tech-lead: Review PR-89 today (blocking PROJ-456)
2. @developer-b: Update PROJ-789 status or unblock
3. @developer-c: Check in on PROJ-234 (no commits in 5 days)
4. @all: Link commits to Jira tickets when possible

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 Questions or issues? Tag @Remington in any channel
📊 Full sprint analysis: `python run_agent.py sprint-analysis`
```

#### How It Works

**Automatic Execution:**
1. Cron job triggers at 9:00 AM (weekdays only)
2. Remington runs the standup orchestrator workflow
3. Gathers data from Jira, Bitbucket, and local git repositories
4. Analyzes SLA compliance, deadline risks, and team activity
5. Formats report and posts to configured Slack channel
6. Takes ~30-60 seconds total

**Manual Invocation:**
```bash
# Run standup report manually (useful for testing)
python run_agent.py standup

# Output will be posted to Slack
```

**Configuration:**
```bash
# In .env file
SLACK_CHANNEL_STANDUP=C123ABC456  # Channel ID for standup posts
BUSINESS_HOURS_START=9            # Report posts at this hour
BUSINESS_TIMEZONE=America/New_York
```

### Continuous Monitoring

Remington runs three concurrent monitoring systems:

**1. Webhook Listeners (Instant Response)**
- Jira webhooks: Comment events
- Bitbucket webhooks: PR events, comments
- FastAPI server on port 8000

**2. Polling Monitors (Backup + Slack)**
- **Slack**: Every 15 seconds (primary - Slack has no webhooks)
- **Jira**: Every 30 seconds (backup to webhooks)
- **Bitbucket**: Every 30 seconds (backup to webhooks)

**3. Scheduled Jobs (Daily/Hourly)**
- **Daily Standup**: Weekdays at 9 AM
- **SLA Checks**: Every hour
- **Sprint Analysis**: On-demand via `python run_agent.py sprint-analysis`

**Why the hybrid approach?**
- Webhooks can fail (network issues, misconfigurations)
- Polling ensures nothing is missed (3-day lookback after restart)
- Slack has no webhook support, requires polling

---

## 📦 Installation

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **API Access:**
  - Atlassian account (Jira + Bitbucket)
  - Anthropic API key ([Get one](https://console.anthropic.com/))
  - Slack workspace (optional)

### Step-by-Step Setup

#### 1. Clone Repository

```bash
git clone https://github.com/ethandrower/remington.git
cd remington
```

#### 2. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install bitbucket-cli (required for Bitbucket PR automation)
pip install git+https://github.com/ethandrower/bitbucket-cli-for-claude-code.git
```

**Note on bitbucket-cli:** This is a custom CLI tool that provides a cleaner interface to Bitbucket's API than the official Atlassian Python library. It handles authentication, pagination, and proper @mention formatting automatically.

#### 4. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with your credentials
nano .env  # or your preferred editor
```

**Required Variables:**

```bash
# Anthropic API (for AI reasoning)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Atlassian Configuration
ATLASSIAN_CLOUD_ID=your-cloud-id-here
JIRA_INSTANCE_URL=https://your-company.atlassian.net
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=bot@your-company.atlassian.com
ATLASSIAN_SERVICE_ACCOUNT_TOKEN=your-jira-api-token

# One project or comma-separated for multiple: ATLASSIAN_PROJECT_KEY=ECD,MDP
# Note: SLA checks, standup, and blocked-ticket scripts use project IN (ECD, MDP)
# syntax automatically when multiple keys are provided.
ATLASSIAN_PROJECT_KEY=YOUR_PROJECT

# Bot identity — must match the Jira service account display name.
# Used for self-mention detection and Bitbucket comment attribution.
SERVICE_ACCOUNT_NAME=remington

# Bitbucket
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_REPOS=repo1,repo2
BITBUCKET_REPO_TOKEN=your-bitbucket-app-password

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_BOT_USER_ID=U123ABC456
SLACK_CHANNEL_STANDUP=C123ABC456
SLACK_CHANNEL_QA_ALERTS=C123ABC456   # optional, falls back to SLACK_CHANNEL_STANDUP
SLACK_PM_AGENT_LOG_CHANNEL=C123ABC456  # optional, for internal agent logs

# Scheduling / business hours
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
BUSINESS_TIMEZONE=America/New_York
SLACK_POLL_INTERVAL=15       # seconds between Slack polls
JIRA_POLL_INTERVAL=60        # seconds between Jira polls
BITBUCKET_BACKUP_POLL_INTERVAL=30  # seconds between Bitbucket polls
```

> **⚠️ Critical note on `SERVICE_ACCOUNT_NAME`:** This must be set or the bot will not correctly skip its own comments, causing response loops. Set it to the lowercase display name the bot uses in Jira/Bitbucket comments (e.g. `remington`).

#### 5. Get Your Credentials

**Atlassian Cloud ID:**
1. Go to https://admin.atlassian.com/
2. Look at the URL: `https://admin.atlassian.com/s/{your-cloud-id}/...`
3. Copy the long string

**Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the generated token

**Bitbucket App Password:**
1. Go to https://bitbucket.org/account/settings/app-passwords/
2. Click "Create app password"
3. Grant permissions: `repository:read`, `repository:write`, `pullrequest:write`
4. Copy the generated password

**Slack Bot Token:**
1. Go to https://api.slack.com/apps
2. Create new app (from scratch)
3. Add OAuth scopes: `app_mentions:read`, `channels:history`, `chat:write`, `users:read`
4. Install to workspace
5. Copy "Bot User OAuth Token" (starts with `xoxb-`)

**Slack Bot User ID:**
```bash
# Get it via Slack API
curl https://slack.com/api/auth.test \
  -H "Authorization: Bearer xoxb-your-token" | jq -r .user_id
```

#### 6. Test Configuration

```bash
# Validate environment variables
python -c "from src.config import get_atlassian_config; print(get_atlassian_config())"

# Expected output:
# {'cloud_id': 'your-cloud-id', 'jira_url': 'https://...', 'project_key': 'PROJ'}
```

#### 7. Start Remington

```bash
# Run in foreground (for testing)
python src/pm_agent_service.py

# Run in background (production)
nohup python -u src/pm_agent_service.py > pm_agent.log 2>&1 &

# Check logs
tail -f pm_agent.log
```

**Expected Output:**
```
======================================================================
                  🤖 Autonomous PM Agent Service
======================================================================

Strategy:
  - Webhooks: Primary (instant response)
  - Polling: Backup (catches missed events)
  - Intelligence: Claude API via orchestrator

✅ Jira Monitor initialized (30s backup polling)
✅ Slack Monitor initialized (15s primary polling)
✅ Bitbucket Monitor initialized (30s backup polling)

🚀 Starting webhook server on port 8000...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🔧 Configuration

### Setting Up Webhooks (Recommended)

**Jira Webhooks:**
1. Go to Jira → Settings → System → Webhooks
2. Create webhook:
   - **URL**: `http://your-server:8000/webhooks/jira`
   - **Events**: Issue → commented
   - **JQL Filter**: `project = YOUR_PROJECT`

**Bitbucket Webhooks:**
1. Repository → Settings → Webhooks
2. Create webhook:
   - **URL**: `http://your-server:8000/webhooks/bitbucket`
   - **Events**: Pull request created/updated/commented

**Note:** Polling continues even with webhooks configured (belt-and-suspenders approach).

### Customizing SLAs

Edit `.env`:

```bash
# Business hours (SLA timers only run during these hours)
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
BUSINESS_TIMEZONE=America/New_York

# Holidays (comma-separated YYYY-MM-DD)
COMPANY_HOLIDAYS=2025-01-01,2025-05-26,2025-07-04,2025-12-25

# SLA Targets (in business days/hours)
JIRA_COMMENT_SLA_DAYS=2
PR_REVIEW_SLA_HOURS=48
```

See [`.claude/workflows/sla-monitoring.md`](.claude/workflows/sla-monitoring.md) for full SLA definitions.

---

## 🏗️ Architecture

### Why We Don't Use MCP (Model Context Protocol)

**MCP was considered but rejected because:**

1. **Complexity Overhead** - MCP requires Node.js runtime, multiple server processes, and complex configuration
2. **Authentication Issues** - MCP servers have trouble with service account tokens and OAuth flows
3. **Limited Error Handling** - MCP abstraction makes debugging API issues harder
4. **Unnecessary Abstraction** - Direct REST API calls are simpler and more reliable
5. **Better Control** - Direct API access allows custom retry logic, rate limiting, and error handling

**Instead, we use:**
- ✅ **Direct Atlassian REST APIs** - Simple, well-documented, reliable
- ✅ **Custom bitbucket-cli** - Thin wrapper that handles auth and formatting
- ✅ **Claude API directly** - No intermediary layers, full control
- ✅ **Python requests library** - Standard, battle-tested HTTP client

This keeps the stack simple: `Python → REST APIs → Atlassian/Slack/Claude`

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Remington Agent                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Webhook    │  │   Polling    │  │  Scheduled   │     │
│  │   Listeners  │  │   Monitors   │  │    Jobs      │     │
│  │   (FastAPI)  │  │ (15-30s loops)│  │(Cron-based)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  Orchestrator   │                       │
│                  │  (Routes to     │                       │
│                  │   Sub-Agents)   │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         │                 │                 │             │
│    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐        │
│    │ Standup │       │   SLA   │      │  Jira   │        │
│    │Orchestr.│       │ Monitor │      │ Manager │        │
│    └─────────┘       └─────────┘      └─────────┘        │
│                                                            │
│              (6 specialized sub-agents)                    │
│                                                            │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │  Jira   │         │  Slack  │        │Bitbucket│
   │   API   │         │   API   │        │   API   │
   └─────────┘         └─────────┘        └─────────┘
```

### 6 Specialized Sub-Agents

Located in `.claude/agents/`, each sub-agent has specific responsibilities:

| Agent | Purpose | Invoked By |
|-------|---------|------------|
| **standup-orchestrator** | Daily standup reports | Scheduled (9 AM weekdays) |
| **sprint-analyzer** | Sprint burndown, velocity tracking | On-demand |
| **sla-monitor** | SLA violation detection & escalation | Hourly schedule |
| **developer-auditor** | Timesheet vs code correlation | Daily standup |
| **jira-manager** | Jira comment responses, ticket updates | @mention in Jira |
| **deadline-risk-analyzer** | Due date monitoring | Daily standup |

---

## 🚀 Usage

### Daily Operations

**Check Service Status:**
```bash
# Is it running?
ps aux | grep pm_agent_service

# Check webhook server health
curl http://localhost:8000/health

# View live logs
tail -f pm_agent.log
```

**Manual Workflow Invocation:**
```bash
# Run daily standup manually
python run_agent.py standup

# Run SLA compliance check
python run_agent.py sla-check

# Analyze sprint health
python run_agent.py sprint-analysis
```

### Interacting with Remington

**Ask questions:**
- Jira: `@remington what's blocking this ticket?`
- Slack: `@Remington summarize PROJ-123`
- Bitbucket: `@remington when should this PR merge?`

**Request actions:**
- `@remington update this ticket to In Progress`
- `@remington assign this to @developer`
- `@remington what's our sprint velocity?`

**Get status:**
- `@remington what are our current SLA violations?`
- `@remington which tickets are at risk of missing deadlines?`
- `@remington show me sprint burndown`

---

## 🧪 Testing

### Manual Integration Tests

**Test Jira Response:**
1. Start: `python src/pm_agent_service.py`
2. Post Jira comment: `@remington hello`
3. Watch logs for detection
4. Verify response appears (30-60 seconds)

**Test Slack Monitoring:**
1. Start service
2. Message in Slack: `@Remington what's the status of PROJ-123?`
3. Watch logs
4. Verify threaded response

**Test SLA Detection:**
1. Create PR and leave unreviewed for 48+ hours
2. Wait for hourly SLA check
3. Verify escalation comment appears in PR

### Automated Tests

```bash
# Run full test suite
pytest tests/ -v

# Run specific monitor tests
pytest tests/test_polling_monitors.py -v

# Run with coverage
pytest --cov=src tests/
```

---

## 🐳 Deployment

### Option 1: systemd Service (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/remington.service
```

```ini
[Unit]
Description=Remington PM Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/remington
Environment="PATH=/path/to/remington/.venv/bin"
ExecStart=/path/to/remington/.venv/bin/python src/pm_agent_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable remington
sudo systemctl start remington
sudo systemctl status remington
```

### Option 2: Docker

```bash
# Build
docker build -t remington .

# Run
docker run -d --name remington \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  remington

# Logs
docker logs -f remington
```

### Option 3: Heroku

See [`docs/deployment/HEROKU_DEPLOYMENT.md`](docs/deployment/HEROKU_DEPLOYMENT.md) for complete setup.

```bash
heroku create your-remington
git push heroku main
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku logs --tail
```

---

## 📁 Project Structure

```
remington/
├── .claude/                    # Agent knowledge base
│   ├── CLAUDE.md              # Main agent instructions
│   ├── agents/                # 6 specialized sub-agents (AGENT.md)
│   ├── skills/                # Knowledge domains (SKILL.md)
│   ├── workflows/             # Automation procedures
│   └── data/                  # State tracking (SQLite DBs)
├── src/
│   ├── pm_agent_service.py    # Main entry point
│   ├── config.py              # Environment config management
│   ├── orchestration/         # Routes requests to sub-agents
│   ├── monitors/              # Jira/Slack/Bitbucket polling
│   ├── database/              # SQLAlchemy models
│   └── web/                   # FastAPI webhook server
├── scripts/
│   ├── core/                  # Core automation scripts
│   └── utilities/             # Helper tools
├── tests/                     # Test suite
├── docs/                      # Documentation
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🔒 Security

### What Remington CAN Do:

✅ Read Jira tickets and comments
✅ Post Jira comments and @mention users
✅ Read Bitbucket PRs and commits
✅ Post PR review comments
✅ Post Slack messages
✅ Update Jira ticket status (via transitions)

### What Remington CANNOT Do:

❌ Modify code in repositories
❌ Commit or push changes
❌ Merge or approve PRs
❌ Delete Jira tickets
❌ Execute shell commands on your servers

**Best Practices:**
- Use a dedicated service account for Atlassian (not personal)
- Rotate API tokens every 90 days
- Never commit `.env` (already in `.gitignore`)
- Use read-only filesystem permissions where possible
- Monitor logs for suspicious activity

---

## 🐛 Troubleshooting

**Service won't start:**
```bash
# Check Python version
python --version  # Must be 3.11+

# Verify dependencies installed
pip list | grep anthropic

# Check environment variables
python -c "from src.config import get_atlassian_config; print(get_atlassian_config())"
```

**Mentions not detected:**
- Verify Slack bot has `app_mentions:read` scope
- Check Jira webhooks are configured correctly
- Ensure bot account ID is in `.env`

**Database locked errors:**
```bash
# Kill zombie processes
pkill -f pm_agent_service

# Delete lock files if needed
rm -f .claude/data/bot-state/*.db-wal
rm -f .claude/data/bot-state/*.db-shm
```

**SLA violations not escalating:**
- Check business hours configuration in `.env`
- Verify holiday dates are in correct format (YYYY-MM-DD)
- Run manual SLA check: `python run_agent.py sla-check`

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/ethandrower/remington.git
cd remington
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

### Submitting Changes

1. Fork the repo
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes
4. Run tests: `pytest tests/`
5. Commit: `git commit -m 'feat: Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

---

## 📚 Documentation

- **[Architecture](docs/architecture/)** - System design deep-dive
- **[Deployment](docs/deployment/)** - Production deployment guides
- **[Testing](docs/testing/)** - Test plans and procedures
- **[Configuration](docs/CONFIGURATION.md)** - Complete config reference

---


## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[Anthropic](https://anthropic.com/)** - Claude AI models
- **[Atlassian](https://www.atlassian.com/)** - Jira, Bitbucket, Confluence APIs
- **[Slack](https://slack.com/)** - Team communication platform

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ethandrower/remington/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ethandrower/remington/discussions)
- **Documentation**: [docs/](docs/)

---

**Built with ❤️ for overwhelmed project managers**
