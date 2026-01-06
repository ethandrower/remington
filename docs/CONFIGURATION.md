# Configuration Guide

## Precedence Order

Configuration is loaded in the following order (later takes precedence):

1. **`.env`** - Environment variables (secrets, NOT in git)
2. **`.claude/settings.local.json`** - Claude Code local settings
3. **`.mcp.json`** - MCP server configuration
4. **`claude.json`** - Claude CLI global settings

## Key Files

### .env (NOT in git)

Contains sensitive credentials and configuration:

```bash
# Atlassian Configuration
ATLASSIAN_SERVICE_ACCOUNT_TOKEN=<your-api-token>
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=remington-cd3wmzelbd@serviceaccount.atlassian.com
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
ATLASSIAN_PROJECT_KEY=ECD

# Bitbucket Configuration
BITBUCKET_WORKSPACE=citemed
BITBUCKET_REPOS=citemed_web,word_addon

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-<your-bot-token>
SLACK_CHANNEL_STANDUP=C02NW7QN1RN
SLACK_BOT_USER_ID=U09BVV00XRP

# Polling Intervals (seconds)
JIRA_BACKUP_POLL_INTERVAL=30
BITBUCKET_BACKUP_POLL_INTERVAL=30
SLACK_POLL_INTERVAL=15
```

### .mcp.json

Defines how to start MCP servers (command, args, environment variables):

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-atlassian"],
      "env": {
        "ATLASSIAN_CLOUD_ID": "67bbfd03-b309-414f-9640-908213f80628",
        "ATLASSIAN_API_TOKEN": "${ATLASSIAN_SERVICE_ACCOUNT_TOKEN}",
        "ATLASSIAN_USER_EMAIL": "${ATLASSIAN_SERVICE_ACCOUNT_EMAIL}"
      }
    }
  }
}
```

Note: Environment variables referenced with `${VAR_NAME}` are loaded from `.env`.

### .claude/settings.local.json

Claude Code local settings including MCP server permissions and project-specific configuration.

## Quick Start

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in secrets in `.env`:**
   - Get Atlassian API token from https://id.atlassian.com/manage-profile/security/api-tokens
   - Get Slack bot token from https://api.slack.com/apps

3. **Start the service:**
   ```bash
   python src/pm_agent_service.py
   ```

## Troubleshooting

### MCP Servers Not Loading

Check that `.mcp.json` is valid JSON:
```bash
python3 -c "import json; json.load(open('.mcp.json')); print('✅ Valid JSON')"
```

### Environment Variables Not Loading

Verify `.env` exists and is properly formatted:
```bash
source .env && echo "✅ ATLASSIAN_CLOUD_ID: $ATLASSIAN_CLOUD_ID"
```

### Service Won't Start

1. Check Python dependencies: `pip install -r requirements.txt`
2. Verify Claude Code CLI is installed: `claude --version`
3. Check for port conflicts: `lsof -i :8000`

## Security Notes

- **NEVER** commit `.env` to git (already in `.gitignore`)
- Rotate API tokens every 90 days
- Use service accounts, not personal credentials
- `.mcp.json` is gitignored to prevent accidental secret commits
