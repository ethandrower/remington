# Remington - Autonomous Project Manager Agent

> An AI-powered project management assistant that monitors Jira, Bitbucket, and Slack to automate workflows, enforce SLAs, and keep your team on track.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Claude](https://img.shields.io/badge/powered%20by-Claude%20AI-orange.svg)](https://www.anthropic.com/)

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

**In Jira:**
```
Comment on any ticket: "@remington what's the status of this?"
→ Remington reads the full ticket context and posts a detailed response
```

**In Slack:**
```
In any channel: "@remington when is PROJ-123 due?"
→ Remington fetches ticket details from Jira and responds in thread
```

**In Bitbucket:**
```
Comment on PR: "@remington review this code"
→ Remington analyzes the diff and posts review comments
```

**Important:** Use the exact bot mention format for your platform:
- **Jira**: `@remington` (uses Jira account ID internally)
- **Slack**: `@Remington` or `<@U09BVV00XRP>` (your bot's user ID)
- **Bitbucket**: `@{bot-account-id}` (Bitbucket UUID format)

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

---

## 🤖 Automated Workflows

### Daily Standup (Weekdays at 9 AM)

Remington automatically posts a comprehensive standup report to Slack:

1. **Code-Ticket Gap Detection** - Finds commits without associated Jira tickets
2. **Productivity Audit** - Analyzes work quality over the last 7 days
3. **Team Timesheet Review** - Validates logged time vs actual work
4. **SLA Violations** - Lists all current violations and pending escalations
5. **Deadline Risk Dashboard** - Highlights tickets at risk of missing deadlines

**Example Output:**
```
🌅 Daily Standup Report - January 6, 2026

📊 Sprint Health:
  • Sprint: Sprint 42 (Jan 1-14)
  • Completed: 23/40 points (58%)
  • On track for 85% completion

⚠️ SLA Violations:
  • PROJ-456: PR review waiting 3 days (Level 3 escalation sent)
  • PROJ-789: Blocked ticket needs update (Level 1 reminder)

🎯 Deadline Risks:
  • PROJ-123: Due tomorrow, still "In Progress"
  • PROJ-234: Due in 3 days, no commits in 5 days

👥 Team Activity:
  • 15 commits yesterday
  • 3 PRs merged
  • 12 Jira updates
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
ATLASSIAN_PROJECT_KEY=YOUR_PROJECT

# Atlassian Authentication
ATLASSIAN_API_TOKEN=your-jira-api-token
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=bot@your-company.atlassian.com
BITBUCKET_REPO_TOKEN=your-bitbucket-app-password

# Slack Configuration (optional but recommended)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_BOT_USER_ID=U123ABC456
SLACK_CHANNEL_STANDUP=C123ABC456

# Company Settings
COMPANY_NAME=YourCompany
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
BUSINESS_TIMEZONE=America/New_York
```

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
