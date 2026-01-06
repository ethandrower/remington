# Autonomous Project Manager Agent

> An AI-powered project management assistant that monitors Jira, Bitbucket, and Slack to automate team workflows, enforce SLAs, and provide intelligent responses.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Claude](https://img.shields.io/badge/powered%20by-Claude%20Code-orange.svg)](https://claude.com/claude-code)

---

## ⚡ Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/project-manager.git
cd project-manager
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Run the service
python src/pm_agent_service.py
```

That's it! The agent is now monitoring your Jira, Slack, and Bitbucket for mentions and events.

---

## 🎯 What It Does

This autonomous agent operates 24/7 to handle routine project management tasks:

### Core Features
- **🤖 Automated PR Code Reviews** - Analyzes code quality, security, and best practices
- **💬 Intelligent Jira Responses** - Context-aware answers to ticket questions
- **📊 Real-Time Monitoring** - Hybrid webhook + polling architecture
- **✅ SLA Compliance Tracking** - Automatic violation detection and escalation
- **📈 Sprint Health Analysis** - Burndown tracking and epic progress monitoring
- **👥 Team Productivity Audits** - Timesheet validation and code-ticket correlation
- **🔔 Smart @Mentions** - Proper user notifications in Jira and Bitbucket

### Automation Examples

**Automated PR Review:**
```
Developer pushes commit → Agent detects change → Analyzes code quality
→ Posts detailed review with inline comments → @mentions author
```

**Jira Comment Response:**
```
User asks "@bot what's the status?" → Agent reads ticket history
→ Analyzes context and business rules → Posts intelligent response
→ @mentions relevant team members
```

**SLA Monitoring:**
```
PR sits for 48 hours → Agent detects violation → Posts escalation
→ Notifies tech lead → Updates tracking database
```

---

## 🏗️ Architecture

The agent runs as a **24/7 service** with three concurrent systems:

### 1. Webhook Server (Primary - Instant Response)
- FastAPI server listening for Jira/Bitbucket events
- < 100ms webhook acknowledgment
- Background processing with Claude Code

### 2. Polling Monitors (Backup - Catches Missed Events)
- **Slack**: 15 seconds (primary - no webhook support)
- **Jira**: 30 seconds (backup to webhooks)
- **Bitbucket**: 30 seconds (backup to webhooks)
- 3-day lookback period prevents missing events after restarts

### 3. Claude Code Orchestrator (Intelligence Layer)
- Uses Claude Code CLI with MCP (Model Context Protocol)
- Reads agent instructions from `.claude/` directory
- Executes context-aware decision-making
- Posts responses via REST APIs with proper @mentions

---

## 📦 Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for MCP servers)
- **Claude Code CLI** - [Install here](https://claude.com/claude-code)
- **Access to:**
  - Atlassian account (Jira/Bitbucket)
  - Slack workspace (optional)

### Setup Steps

#### 1. Install Claude Code CLI

```bash
# Download from https://claude.com/claude-code
# Verify installation
claude --version
```

#### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/project-manager.git
cd project-manager

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Environment Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```bash
# Anthropic API (for AI reasoning)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Atlassian Configuration
ATLASSIAN_CLOUD_ID=your-cloud-id-here
JIRA_INSTANCE_URL=https://your-company.atlassian.net
ATLASSIAN_PROJECT_KEY=YOUR_PROJECT

# Slack Configuration (optional)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_BOT_USER_ID=U123ABC456
SLACK_CHANNEL_STANDUP=C123ABC456

# Company Configuration
COMPANY_NAME=YourCompany
```

See [`.env.example`](.env.example) for complete configuration options.

#### 4. Test Configuration

```bash
# Validate all required environment variables are set
python src/config.py

# Expected output:
# ✅ Anthropic API Key: sk-ant-...
# ✅ Atlassian Cloud ID: your-cloud-id
# ✅ Jira URL: https://your-company.atlassian.net
# ✅ Project Key: YOUR_PROJECT
```

#### 5. Run the Service

```bash
# Start the PM Agent (this runs everything)
python src/pm_agent_service.py

# Or with module syntax
python -m src.pm_agent_service

# Run in background with logging
python -u src/pm_agent_service.py 2>&1 | tee -a pm_agent.log &
```

**Expected Output:**
```
======================================================================
                  🤖 Autonomous PM Agent Service
======================================================================

Strategy:
  - Webhooks: Primary (instant response)
  - Polling: Backup (catches missed events)
  - Intelligence: Claude Code with MCP tools

✅ Claude Code Orchestrator ready
✅ Slack Monitor initialized (15s polling)
✅ Jira Monitor initialized (30s backup polling)
✅ Bitbucket Monitor initialized (30s backup polling)

🚀 Starting webhook server on port 8000...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🔧 Configuration Guide

### Getting Your Credentials

#### Atlassian Cloud ID
1. Go to https://admin.atlassian.com/
2. Look at the URL - your Cloud ID is the long string
3. Example: `https://admin.atlassian.com/s/{cloud-id}/...`

#### Jira Project Key
1. Open any ticket in your project
2. Look at the issue key (e.g., `PROJ-123`)
3. The project key is the prefix before the dash (`PROJ`)

#### Slack Bot Token
1. Go to https://api.slack.com/apps
2. Create a new app or select existing
3. Navigate to "OAuth & Permissions"
4. Install app to workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

#### Slack Bot User ID
1. Go to https://api.slack.com/apps
2. Select your app → "OAuth & Permissions"
3. Scroll to "Scopes" → Add bot token scopes:
   - `app_mentions:read`
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `users:read`
4. Install/reinstall app to workspace
5. Get Bot User ID from app settings or by calling `client.auth_test()`

### MCP Server Configuration

The agent uses Model Context Protocol (MCP) servers for accessing Jira/Confluence:

1. Copy MCP example: `cp .mcp.json.example .mcp.json`
2. Edit `.mcp.json` with your Atlassian credentials
3. See [MCP documentation](https://modelcontextprotocol.io/) for details

---

## 🚀 Usage

### Daily Operations

**Monitor Service Status:**
```bash
# Check if service is running
ps aux | grep pm_agent_service

# Check webhook server health
curl http://localhost:8000/health | python -m json.tool

# View live logs
tail -f pm_agent.log
```

**Manual Workflows:**
```bash
# Run daily standup report once
python run_agent.py standup

# Run SLA compliance check
python run_agent.py sla-check

# Run sprint analysis
python run_agent.py sprint-analysis
```

### Webhook Setup

**Jira Webhooks:**
1. Go to your Jira instance → Settings → System → Webhooks
2. Create webhook:
   - **URL**: `http://your-server:8000/webhooks/jira`
   - **Events**: Issue → commented
   - **JQL Filter**: `project = YOUR_PROJECT`

**Bitbucket Webhooks:**
1. Go to Repository → Settings → Webhooks
2. Create webhook:
   - **URL**: `http://your-server:8000/webhooks/bitbucket`
   - **Events**: Pull request created/updated/commented

**Note**: Polling continues as backup even with webhooks configured.

---

## 🧠 How It Works

### Agent Architecture

The agent consists of **6 specialized sub-agents** (`.claude/agents/`):

| Sub-Agent | Responsibilities |
|-----------|-----------------|
| **Standup Orchestrator** | Daily standup reports, sprint progress tracking |
| **Sprint Analyzer** | Burndown analysis, epic progress, bottleneck detection |
| **SLA Monitor** | Compliance tracking, escalation execution |
| **Developer Auditor** | Timesheet validation, productivity analysis |
| **Jira Manager** | Comment responses, ticket updates, JQL queries |
| **Deadline Risk Analyzer** | Due date monitoring, risk assessment |

### Knowledge Base

**Skills** (`.claude/skills/`):
- `agile-workflows/` - Sprint planning, standups, retrospectives
- `jira-best-practices/` - Ticket formatting, workflow guidance
- `team-communication/` - Slack messaging, escalation templates
- `sla-enforcement/` - SLA logic, escalation decision trees

### Workflow Example: PR Review

```
1. Developer pushes new commit to PR
   ↓
2. Bitbucket webhook → PM Agent (instant)
   OR Polling detects commit (30s backup)
   ↓
3. Check database: Already reviewed? → Skip if yes
   ↓
4. Claude Code Orchestrator:
   - Fetches PR diff
   - Reads code review guidelines
   - Analyzes code quality, security, best practices
   - Generates review comments
   ↓
5. Posts review to Bitbucket:
   - Summary comment with @author mention
   - Inline comments on specific issues
   - Overall recommendation
   ↓
6. Database updated: Mark commit as reviewed
   ↓
7. Developer receives notification
```

**Typical Response Time**: 60-90 seconds

---

## 📊 SLA Definitions

The agent enforces these Service Level Agreements (customize in `.env`):

| SLA | Default Target | Applies To | Escalation |
|-----|---------------|------------|------------|
| **Jira Comment Response** | 2 business days | Stakeholder comments | 4-level matrix |
| **PR Review** | 24-48 hours | Initial review of PRs | Slack notification |
| **PR Staleness** | 2 business days | PRs without commits | Author notification |
| **Blocked Ticket Updates** | Daily | Blocked status tickets | Daily reminder |
| **Pending Approval** | 48 hours | Awaiting sign-off | Approver reminder |

**Business Hours**: Configurable via `BUSINESS_HOURS_START`, `BUSINESS_HOURS_END`, and `BUSINESS_TIMEZONE` in `.env`

See [`.claude/workflows/sla-monitoring.md`](.claude/workflows/sla-monitoring.md) for complete definitions.

---

## 🚨 Escalation Matrix

Automated escalations follow a 4-level system:

| Level | Timing | Action | Channels |
|-------|--------|--------|----------|
| **Level 1** | 0-1 days overdue | Soft reminder | Jira comment |
| **Level 2** | 1-2 days overdue | Explicit request | Jira + Slack |
| **Level 3** | 2-3 days overdue | Team escalation | Jira + Slack + @tech-lead |
| **Level 4** | 3+ days overdue | Leadership alert | Jira + Slack + @leadership |

Escalation templates are customizable in `.claude/skills/sla-enforcement/`.

---

## 🧪 Testing

### Manual Testing

**Test Jira Comment Response:**
1. Start service: `python src/pm_agent_service.py`
2. Post comment in Jira: "@bot please review this ticket"
3. Watch logs for detection and processing
4. Check Jira for bot's response (30-60 seconds)
5. Verify @mention is clickable

**Test PR Review:**
1. Start service
2. Push commit to an open PR
3. Watch logs for PR detection
4. Check PR for automated review (60-90 seconds)
5. Verify @author mention works

### Automated Tests

```bash
# Run full test suite
pytest tests/ -v

# Run specific test
pytest tests/test_polling_monitors.py -v

# Run with coverage
pytest --cov=src tests/
```

---

## 🐳 Deployment

### Production Deployment Options

#### Option 1: systemd Service (Linux)

1. Create service file: `/etc/systemd/system/pm-agent.service`
```ini
[Unit]
Description=Autonomous PM Agent Service
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/project-manager
Environment="PATH=/path/to/project-manager/.venv/bin"
ExecStart=/path/to/project-manager/.venv/bin/python -m src.pm_agent_service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable pm-agent
sudo systemctl start pm-agent
sudo systemctl status pm-agent
```

#### Option 2: Docker Container

```bash
# Build image
docker build -t pm-agent .

# Run container
docker run -d --name pm-agent \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  pm-agent

# View logs
docker logs -f pm-agent
```

#### Option 3: Heroku

```bash
# Deploy to Heroku
heroku create your-pm-agent
git push heroku main

# Set environment variables
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku config:set ATLASSIAN_CLOUD_ID=...

# View logs
heroku logs --tail
```

See [`docs/deployment/HEROKU_DEPLOYMENT.md`](docs/deployment/HEROKU_DEPLOYMENT.md) for complete Heroku setup.

---

## 🔒 Security

### Best Practices

- **Never commit `.env`** - Already in `.gitignore`
- **Use service accounts** - Not personal credentials
- **Rotate tokens regularly** - Every 90 days recommended
- **Least-privilege access** - Only required permissions
- **Read-only code access** - Agent cannot modify your codebase

### Enforced Restrictions

The agent **CANNOT**:
- ❌ Modify code in monitored repositories
- ❌ Commit or push git changes
- ❌ Merge or approve PRs automatically
- ❌ Delete or archive Jira tickets
- ❌ Run destructive commands

Enforced via:
1. `.claude/settings.local.json` - File access permissions
2. MCP filesystem server - Read-only paths
3. Explicit allowlists in orchestrator

---

## 📁 Project Structure

```
project-manager/
├── .claude/                    # Agent knowledge base
│   ├── CLAUDE.md              # Main agent instructions
│   ├── agents/                # 6 specialized sub-agents
│   ├── skills/                # Knowledge base (workflows, best practices)
│   ├── workflows/             # Automation procedures
│   └── data/                  # Historical tracking data
├── src/
│   ├── pm_agent_service.py    # Main service entry point
│   ├── config.py              # Configuration management
│   ├── orchestration/         # Claude Code integration
│   ├── monitors/              # Polling monitors (Jira, Slack, Bitbucket)
│   ├── database/              # SQLAlchemy models
│   └── web/                   # FastAPI webhook server
├── scripts/                   # Helper scripts
├── tests/                     # Test suite
├── docs/                      # Documentation
├── .env.example               # Environment template
├── .mcp.json.example          # MCP server template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🛠️ Customization

### Adding Custom Workflows

1. Create workflow definition: `.claude/workflows/my-workflow.md`
2. Update relevant sub-agent: `.claude/agents/[subagent]/AGENT.md`
3. Add skill if needed: `.claude/skills/my-skill/SKILL.md`
4. Test with manual invocation: `python run_agent.py my-workflow`

### Configuring SLAs

Edit `.env`:
```bash
# Business hours
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
BUSINESS_TIMEZONE=America/New_York

# Company holidays (comma-separated YYYY-MM-DD)
COMPANY_HOLIDAYS=2025-01-01,2025-07-04,2025-12-25
```

### Team Configuration

**Option 1: Sync from Confluence**
```bash
CONFLUENCE_TEAM_PAGE_ID=your-page-id-here
```

**Option 2: Manual Configuration**
```bash
TEAM_MEMBER_NAMES=John Doe,Jane Smith,Bob Johnson
TEAM_MEMBER_IDS=accountId:123abc,accountId:456def,accountId:789ghi
```

---

## 🐛 Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check Claude Code CLI is installed
claude --version

# Verify environment variables
python src/config.py

# Check for port conflicts
lsof -i :8000
```

**Mentions not working:**
- Verify using Jira ADF format for Jira comments
- Verify using `@{accountId}` format for Bitbucket
- Check account IDs are correct (use lookup tools)

**Database locked:**
```bash
# Kill zombie processes
pkill -f pm_agent_service

# Restart service
python src/pm_agent_service.py
```

**Polling missing events:**
- Increase polling frequency in `.env`
- Check database for duplicates
- Verify 3-day lookback is working

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for more help.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/project-manager.git
cd project-manager
python3 -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📚 Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Detailed setup instructions
- **[Architecture Overview](docs/architecture/)** - System design and components
- **[API Reference](docs/API.md)** - Webhook endpoints and data formats
- **[Deployment Guide](docs/deployment/)** - Production deployment options
- **[Testing Guide](docs/testing/)** - Manual and automated testing
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

---

## 📊 Metrics & Monitoring

### Performance Metrics

**Response Times:**
- Webhook acknowledgment: < 100ms
- Jira comment response: 30-60 seconds (avg)
- PR code review: 60-90 seconds (avg)

**Accuracy:**
- SLA compliance detection: 100%
- Code-ticket alignment: 100%
- Duplicate prevention: 100% (via database)

### Health Monitoring

```bash
# Check service status
curl http://localhost:8000/health

# View database stats
sqlite3 .claude/data/bot-state/jira_state.db \
  "SELECT COUNT(*) FROM processed_mentions;"

# Monitor logs
tail -f pm_agent.log
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[Claude Code](https://claude.com/claude-code)** - AI orchestration platform
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - Integration framework
- **[Anthropic](https://anthropic.com/)** - Claude AI models

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/project-manager/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/project-manager/discussions)

---

## 🗺️ Roadmap

- [ ] Web-based dashboard for metrics and control
- [ ] Support for GitHub (in addition to Bitbucket)
- [ ] Multi-language support for messages
- [ ] Machine learning for SLA prediction
- [ ] Integration with additional project management tools
- [ ] Mobile app for on-the-go monitoring

See [ROADMAP.md](docs/ROADMAP.md) for detailed future plans.

---
