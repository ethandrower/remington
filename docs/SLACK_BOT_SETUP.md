# Slack Bot Setup

## Overview

Create a dedicated Slack bot for the PM Agent to post automated reports, respond to @mentions, and create discussion threads. This provides:

✅ Clear identification of automated messages (shows as "PM Bot" instead of personal account)
✅ Ability for team to `@PM-Bot` to trigger workflows
✅ Automated posting of standup reports, SLA alerts, and sprint analysis
✅ Thread-based discussions for better organization
✅ Separation of personal vs automated activity

## Setup Process

### Step 1: Create Slack App

1. **Go to Slack API Dashboard**
   - Visit https://api.slack.com/apps
   - Click "Create New App"
   - Choose "From scratch"

2. **Configure Basic Information**
   - **App Name:** CiteMed PM Bot
   - **Workspace:** Select your CiteMed workspace
   - Click "Create App"

3. **Add Bot User**
   - In the left sidebar, click "App Home"
   - Under "Your App's Presence in Slack", click "Edit" next to Display Name
   - **Display Name:** PM Bot
   - **Default Username:** pm-bot
   - Click "Save"

4. **Add App Icon (Recommended)**
   - Download a robot/bot icon (512x512 or 1024x1024 PNG)
   - Go to "Basic Information" → "Display Information"
   - Upload icon under "App Icon & Preview"

### Step 2: Configure Bot Permissions (Scopes)

1. **Navigate to OAuth & Permissions**
   - Left sidebar → "OAuth & Permissions"

2. **Add Bot Token Scopes**

   Under "Scopes" → "Bot Token Scopes", add these permissions:

   ```
   Required Scopes:
   - chat:write          (Post messages to channels)
   - chat:write.public   (Post to channels without joining)
   - channels:read       (View channel info)
   - channels:history    (Read channel messages for context)
   - users:read          (Look up user info for @mentions)
   - app_mentions:read   (Detect when bot is @mentioned)
   - commands            (For slash commands like /standup)

   Optional but Recommended:
   - files:write         (Upload files like reports)
   - reactions:write     (Add emoji reactions to messages)
   - im:write            (Send DMs for private notifications)
   - groups:read         (Access private channels if needed)
   ```

3. **Install App to Workspace**
   - Scroll to top of "OAuth & Permissions" page
   - Click "Install to Workspace"
   - Review permissions
   - Click "Allow"

4. **Copy Bot Token**
   - After installation, you'll see "Bot User OAuth Token"
   - Starts with `xoxb-`
   - **Copy this token** (you'll add it to `.env`)
   - Example format: `xoxb-YOUR-BOT-TOKEN-HERE`

### Step 3: Configure Event Subscriptions (for @mentions)

1. **Enable Event Subscriptions**
   - Left sidebar → "Event Subscriptions"
   - Toggle "Enable Events" to **On**

2. **Set Request URL**

   You have two options:

   **Option A: Use Slack Socket Mode (Recommended for Development)**
   - Go to "Socket Mode" in left sidebar
   - Enable Socket Mode
   - Create an app-level token with `connections:write` scope
   - No public URL needed

   **Option B: Use HTTP Endpoint (Production)**
   - You need a public HTTPS URL (e.g., `https://your-domain.com/slack/events`)
   - Set up a Flask/FastAPI server to receive events
   - See "Slack Event Listener Setup" section below

3. **Subscribe to Bot Events**

   Under "Subscribe to bot events", add:
   ```
   - app_mention        (When someone @mentions the bot)
   - message.channels   (Messages in channels bot is in)
   - message.im         (Direct messages to bot)
   ```

4. **Save Changes**
   - Click "Save Changes" at bottom

### Step 4: Create Slash Commands (Optional)

If you want `/standup`, `/sla-check`, etc. commands:

1. **Navigate to Slash Commands**
   - Left sidebar → "Slash Commands"
   - Click "Create New Command"

2. **Configure Command**
   ```
   Command: /standup
   Request URL: https://your-domain.com/slack/commands (or use Socket Mode)
   Short Description: Run daily PM standup workflow
   Usage Hint: [--dry-run]
   ```

3. **Repeat for other commands:**
   - `/sla-check` - Check SLA compliance
   - `/sprint-analysis` - Analyze current sprint
   - `/audit` - Run productivity audit

### Step 5: Invite Bot to Channels

1. **Add bot to relevant channels:**
   ```
   /invite @PM-Bot
   ```

2. **Recommended channels:**
   - `#sprint-updates` - For standup reports
   - `#engineering` - For SLA alerts and escalations
   - `#leadership` - For high-priority escalations (Level 4)

## Environment Configuration

Update `.env` with Slack credentials:

```bash
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-level-token-here  # Only if using Socket Mode
SLACK_SIGNING_SECRET=your_signing_secret_here    # From "Basic Information"

# Channel Configuration
SLACK_CHANNEL_STANDUP=#sprint-updates
SLACK_CHANNEL_ALERTS=#engineering
SLACK_CHANNEL_LEADERSHIP=#leadership

# Bot Settings
SLACK_BOT_USER_ID=U123ABC456  # Bot's member ID (lookup via Slack API)
```

## Getting Bot User ID

To find the bot's user ID (needed for self-identification):

```python
# tools/get_slack_bot_id.py
import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
response = client.auth_test()

print(f"Bot User ID: {response['user_id']}")
print(f"Bot User: {response['user']}")
print(f"Team: {response['team']}")

# Example output:
# Bot User ID: U123ABC456
# Bot User: pm-bot
# Team: CiteMed
```

## Slack Event Listener Setup

### Option 1: Socket Mode (Recommended for Development)

Socket Mode doesn't require a public URL. Best for local development and testing.

```python
# .claude/scripts/slack_socket_listener.py
import os
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

load_dotenv()

# Initialize Bolt app
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

# Handle @mentions
@app.event("app_mention")
def handle_mention(event, say):
    """Respond when bot is @mentioned."""
    user = event["user"]
    text = event["text"]

    # Parse command from mention
    # Example: "@PM-Bot run standup"
    if "run standup" in text.lower():
        say(f"<@{user}> Starting daily standup workflow...")
        # TODO: Trigger run_agent.py standup
        # subprocess.run(["python", "run_agent.py", "standup"])

    elif "check sla" in text.lower():
        say(f"<@{user}> Checking SLA compliance...")
        # TODO: Trigger run_agent.py sla-check

    else:
        say(
            f"Hi <@{user}>! I can help with:\n"
            f"• `@PM-Bot run standup` - Daily standup workflow\n"
            f"• `@PM-Bot check sla` - SLA compliance check\n"
            f"• `@PM-Bot analyze sprint` - Sprint analysis"
        )

# Handle slash commands
@app.command("/standup")
def handle_standup_command(ack, command, say):
    """Handle /standup slash command."""
    ack()  # Acknowledge command immediately
    say("🏃 Running daily standup workflow...")
    # TODO: Trigger run_agent.py standup

if __name__ == "__main__":
    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    print("⚡️ PM Bot is running in Socket Mode!")
    handler.start()
```

**Run the listener:**
```bash
python .claude/scripts/slack_socket_listener.py
```

### Option 2: HTTP Endpoint (Production)

For production, use a web server to receive Slack events.

```python
# .claude/scripts/slack_http_listener.py
from flask import Flask, request, jsonify
from slack_sdk import WebClient
import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def verify_slack_request(request):
    """Verify request is from Slack."""
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET").encode()
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not signature:
        return False

    # Create signing base string
    sig_basestring = f"v0:{timestamp}:{request.get_data().decode()}"

    # Compute expected signature
    expected_signature = "v0=" + hmac.new(
        slack_signing_secret,
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack event subscriptions."""
    if not verify_slack_request(request):
        return jsonify({"error": "Invalid signature"}), 403

    data = request.json

    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # Handle app_mention event
    if data.get("event", {}).get("type") == "app_mention":
        event = data["event"]
        channel = event["channel"]
        user = event["user"]
        text = event["text"]

        # Parse and respond to mention
        if "run standup" in text.lower():
            client.chat_postMessage(
                channel=channel,
                text=f"<@{user}> Starting daily standup workflow..."
            )
            # TODO: Trigger run_agent.py standup

        # ... other commands

    return jsonify({"ok": True})

@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handle Slack slash commands."""
    if not verify_slack_request(request):
        return jsonify({"error": "Invalid signature"}), 403

    command = request.form.get("command")
    user_id = request.form.get("user_id")

    if command == "/standup":
        # TODO: Trigger run_agent.py standup
        return jsonify({
            "response_type": "in_channel",
            "text": "🏃 Running daily standup workflow..."
        })

    return jsonify({"text": "Unknown command"})

if __name__ == "__main__":
    app.run(port=3000)
```

**Deploy with ngrok (for testing):**
```bash
ngrok http 3000
# Use the HTTPS URL (e.g., https://abc123.ngrok.io) as your Request URL in Slack
```

## Integration with PM Agent

Update `run_agent.py` to post to Slack:

```python
# In run_agent.py
import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

def post_to_slack(channel: str, message: str, thread_ts: str = None):
    """Post message to Slack channel."""
    if not os.getenv("SLACK_BOT_TOKEN"):
        print("⚠️  SLACK_BOT_TOKEN not set, skipping Slack post")
        return

    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    response = client.chat_postMessage(
        channel=channel,
        text=message,
        thread_ts=thread_ts  # Reply in thread if provided
    )

    return response["ts"]  # Return timestamp for threading

def run_standup_workflow(args):
    """Execute the complete 5-part standup workflow."""
    print("🏃‍♂️ Running Daily Standup Workflow")

    # Generate standup report
    report = generate_standup_report()  # Your existing logic

    # Post to Slack
    if not args.dry_run:
        channel = os.getenv("SLACK_CHANNEL_STANDUP", "#sprint-updates")
        post_to_slack(channel, report)
        print(f"✅ Posted standup to {channel}")
    else:
        print(f"[DRY RUN] Would post to Slack:\n{report}")
```

## Testing the Bot

### Manual Testing

1. **Test message posting:**
   ```python
   # tools/test_slack_bot.py
   import os
   from slack_sdk import WebClient
   from dotenv import load_dotenv

   load_dotenv()

   client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

   # Test posting to channel
   response = client.chat_postMessage(
       channel="#sprint-updates",
       text="🤖 PM Bot test message - if you see this, the bot is working!"
   )

   print(f"✅ Message posted: {response['ts']}")
   ```

2. **Test @mention in Slack:**
   - Go to `#sprint-updates`
   - Type: `@PM-Bot help`
   - Bot should respond with available commands

3. **Test slash command:**
   - Type: `/standup --dry-run`
   - Bot should acknowledge and run workflow

### Automated Testing

```bash
# Test Slack connectivity
python tools/test_slack_bot.py

# Test standup posting (dry run)
python run_agent.py standup --dry-run

# Test actual posting
python run_agent.py standup
```

## Message Formatting

Use Slack's Block Kit for rich messages:

```python
def create_standup_message(report_data):
    """Create rich formatted standup message."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🏃 Daily Standup Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Date:* {report_data['date']}\n*Sprint:* {report_data['sprint']}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Sprint Progress*\n{report_data['sprint_summary']}"
                }
            },
            # ... more sections
        ]
    }

# Post with blocks
client.chat_postMessage(
    channel="#sprint-updates",
    text="Daily Standup Report",  # Fallback text
    blocks=create_standup_message(report_data)["blocks"]
)
```

## Thread Management

Create threads for SLA escalations:

```python
def post_sla_violation(ticket_key: str, violation_details: str):
    """Post SLA violation and create thread."""
    channel = os.getenv("SLACK_CHANNEL_ALERTS", "#engineering")

    # Post main message
    main_message_ts = post_to_slack(
        channel=channel,
        message=f"⚠️ SLA Violation: {ticket_key}\n{violation_details}"
    )

    # Reply in thread with more context
    post_to_slack(
        channel=channel,
        message="Ticket details:\n• Status: In Progress\n• Assignee: @developer\n• Days overdue: 3",
        thread_ts=main_message_ts
    )
```

## Security Best Practices

### Token Storage
- ✅ Store tokens in `.env` (never commit to git)
- ✅ Use environment variables in production
- ✅ Rotate tokens if exposed
- ❌ Never hardcode tokens in code

### Request Verification
- ✅ Always verify Slack signature for HTTP endpoints
- ✅ Use HTTPS for production endpoints
- ✅ Validate request timestamps (prevent replay attacks)
- ❌ Never disable signature verification

### Permission Scoping
- ✅ Only request scopes you actually need
- ✅ Review bot permissions quarterly
- ✅ Use Socket Mode for development (no public URL exposure)
- ❌ Don't request admin scopes unnecessarily

### Rate Limiting
- ✅ Respect Slack API rate limits (1 message/second for chat.postMessage)
- ✅ Implement retry logic with exponential backoff
- ✅ Batch messages where possible
- ❌ Don't spam channels with rapid-fire messages

## Troubleshooting

### Bot Not Responding to @mentions

**Symptom:**
```
You @mention the bot, but it doesn't respond
```

**Solution:**
1. Check event listener is running (`slack_socket_listener.py` or HTTP server)
2. Verify `app_mentions:read` scope is enabled
3. Check bot is invited to the channel (`/invite @PM-Bot`)
4. Review event subscription settings

### "Not in Channel" Error

**Symptom:**
```
slack_sdk.errors.SlackApiError: not_in_channel
```

**Solution:**
Use `chat:write.public` scope to post without joining, OR:
```python
# Join channel first
client.conversations_join(channel="C123ABC456")
# Then post
client.chat_postMessage(channel="C123ABC456", text="Hello!")
```

### Rate Limit Exceeded

**Symptom:**
```
slack_sdk.errors.SlackApiError: rate_limited
```

**Solution:**
```python
import time
from slack_sdk.errors import SlackApiError

def post_with_retry(channel, text, retries=3):
    for attempt in range(retries):
        try:
            return client.chat_postMessage(channel=channel, text=text)
        except SlackApiError as e:
            if e.response["error"] == "rate_limited":
                retry_after = int(e.response.headers.get("Retry-After", 1))
                time.sleep(retry_after)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### Invalid Token

**Symptom:**
```
slack_sdk.errors.SlackApiError: invalid_auth
```

**Solution:**
1. Verify `SLACK_BOT_TOKEN` starts with `xoxb-`
2. Check token hasn't been revoked
3. Reinstall app to workspace if needed
4. Generate new token from "OAuth & Permissions" page

## Example: Complete Standup Posting

```python
# .claude/scripts/slack_pm_integration.py (enhanced)
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class SlackPMBot:
    def __init__(self):
        self.client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.standup_channel = os.getenv("SLACK_CHANNEL_STANDUP", "#sprint-updates")
        self.alerts_channel = os.getenv("SLACK_CHANNEL_ALERTS", "#engineering")

    def post_standup_report(self, report_sections: dict):
        """Post comprehensive standup report."""
        message = self._format_standup_message(report_sections)

        try:
            response = self.client.chat_postMessage(
                channel=self.standup_channel,
                text=f"Daily Standup Report - {datetime.now().strftime('%Y-%m-%d')}",
                blocks=message["blocks"]
            )
            print(f"✅ Posted standup to {self.standup_channel}")
            return response["ts"]
        except SlackApiError as e:
            print(f"❌ Error posting to Slack: {e.response['error']}")
            return None

    def _format_standup_message(self, sections: dict):
        """Format standup as Slack blocks."""
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🏃 Daily Standup Report"}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*1️⃣ Sprint Progress*\n{sections['sprint_progress']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*2️⃣ Code-Ticket Gaps*\n{sections['gaps']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*3️⃣ Productivity Audit*\n{sections['productivity']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*4️⃣ Team Summary*\n{sections['team_summary']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*5️⃣ SLA Violations*\n{sections['sla_violations']}"
                    }
                }
            ]
        }

# Usage
if __name__ == "__main__":
    bot = SlackPMBot()

    # Example report sections
    report = {
        "sprint_progress": "• 10/15 tickets completed\n• 3 tickets at risk",
        "gaps": "• ECD-123 has code but no updates in 2 days",
        "productivity": "• Mohamed: 8.5/10 correlation\n• Ahmed: 9.2/10 correlation",
        "team_summary": "• Average velocity: 85%\n• On track for sprint goal",
        "sla_violations": "• 2 tickets require attention\n• 1 PR needs review"
    }

    bot.post_standup_report(report)
```

## Additional Resources

- [Slack API Documentation](https://api.slack.com/)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder/) - Visual message designer
- [Slack Python SDK](https://slack.dev/python-slack-sdk/)
- [Slack Bolt Framework](https://slack.dev/bolt-python/tutorial/getting-started) - For event-driven apps
- [Socket Mode Guide](https://api.slack.com/apis/connections/socket)

---

**Created:** 2025-10-19
**For:** CiteMed PM Agent Autonomous Operation
