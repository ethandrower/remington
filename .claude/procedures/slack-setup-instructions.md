# Slack Integration Setup for Project Manager Automation

## Overview
This guide sets up a simple Slack bot that Claude can use to read timesheet data and send PM alerts without hosting any servers.

## Prerequisites
- Admin access to your Slack workspace
- Python 3.6+ available for Claude to execute scripts

## Step 1: Create Slack App

1. **Go to** https://api.slack.com/apps
2. **Click** "Create New App" → "From scratch"
3. **Name**: "CiteMed PM Bot"
4. **Workspace**: Select your CiteMed workspace
5. **Click** "Create App"

## Step 2: Configure Bot Permissions

1. **Go to** "OAuth & Permissions" in left sidebar
2. **Scroll to** "Scopes" → "Bot Token Scopes"
3. **Add these scopes**:
   - `channels:history` - Read public channel messages
   - `groups:history` - Read private channel messages
   - `chat:write` - Send messages
   - `users:read` - Get user information
   - `channels:read` - List channels

## Step 3: Install App to Workspace

1. **Scroll up** to "OAuth Tokens for Your Workspace"
2. **Click** "Install to Workspace"
3. **Review permissions** and click "Allow"
4. **Copy** the "Bot User OAuth Token" (starts with `xoxb-`)

## Step 4: Add Bot to Channels

1. **Go to** your timesheet/developer channel in Slack
2. **Type** `/invite @CiteMed PM Bot`
3. **Or** go to channel settings → Integrations → Add apps → CiteMed PM Bot

## Step 5: Set Environment Variable

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
export SLACK_BOT_TOKEN="xoxb-your-token-here"
```

Or create a secure config file:
```bash
# Create secure token file
echo 'export SLACK_BOT_TOKEN="xoxb-your-token-here"' > ~/.claude/slack-token
chmod 600 ~/.claude/slack-token

# Source in scripts
source ~/.claude/slack-token
```

## Step 6: Test the Integration

```bash
# Make script executable
chmod +x .claude/subagents/project-manager/scripts/slack_pm_integration.py

# Test reading messages
python .claude/subagents/project-manager/scripts/slack_pm_integration.py read developer-chat 7

# Test sending message
python .claude/subagents/project-manager/scripts/slack_pm_integration.py send general "PM Bot test message"

# Test timesheet analysis
python .claude/subagents/project-manager/scripts/slack_pm_integration.py timesheets developer-timesheets 7
```

## Usage Examples for Claude

### Read Developer Channel History
```bash
python slack_pm_integration.py read developer-chat 7 > recent_messages.json
```

### Extract Timesheet Data
```bash
python slack_pm_integration.py timesheets developer-timesheets 7 > timesheet_analysis.json
```

### Send PM Gap Alert
```bash
python slack_pm_integration.py alert dev-team ECD-409 "Mohamed Belkahla"
```

### Send Custom Message
```bash
python slack_pm_integration.py send dev-team "🎯 Sprint burndown: 65% complete, 3 days remaining"
```

## Timesheet Message Patterns

The script automatically recognizes these timesheet formats:

```
✅ Recognized formats:
- "3.5h on ECD-409"
- "ECD-409: 2.5 hours"
- "4h - working on authentication system"
- "Today: worked on ECD-409 for 3h, fixed login bug"

❌ Not recognized:
- "worked all day" (no hours specified)
- "debugging issues" (no ticket reference)
```

## Security Notes

- **Bot token** has limited read/write permissions to specific channels
- **No webhooks** or external hosting required
- **Token** stored locally, not in cloud services
- **Revokable** anytime from Slack app settings

## Troubleshooting

### "Channel not found" error
- Check bot is invited to the channel
- Use channel name without # prefix
- Check for typos in channel name

### "Invalid token" error
- Verify SLACK_BOT_TOKEN environment variable
- Re-copy token from Slack app OAuth page
- Check token starts with `xoxb-`

### "Missing scope" error
- Go to OAuth & Permissions in Slack app
- Add required scopes listed above
- Reinstall app to workspace

## Integration with PM Workflows

### Daily Gap Detection
```bash
# Get timesheet data
python slack_pm_integration.py timesheets dev-timesheets 1 > daily_timesheets.json

# Cross-reference with git activity (existing workflow)
# Send alerts for gaps detected
python slack_pm_integration.py alert dev-team ECD-409 "Developer Name"
```

### Weekly Productivity Report
```bash
# Get week's timesheet data
python slack_pm_integration.py timesheets dev-timesheets 7 > weekly_timesheets.json

# Analyze against git commits and Jira updates
# Post summary to team channel
python slack_pm_integration.py send dev-team "📊 Weekly productivity report: ..."
```

This completes the no-server Slack integration for automated PM analysis!
