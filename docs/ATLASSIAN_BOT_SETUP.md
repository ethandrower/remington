# Atlassian Bot User Setup

## Overview

Instead of using personal Atlassian credentials, create a dedicated bot user account for the PM Agent. This provides:

✅ Clear identification of automated comments
✅ Ability to `@mention` the bot to trigger workflows
✅ Separation of personal vs automated activity
✅ Better audit trail for compliance

## Setup Options

### Option 1: Service Account (Recommended for Enterprise)

1. **Create Service Account**
   - Go to Atlassian Admin → User management
   - Add new user with email like `pm-bot@citemed.com`
   - Set display name: "CiteMed PM Bot" or "Automation Bot"

2. **Assign Appropriate Permissions**
   ```
   Jira Permissions:
   - Browse projects
   - Add comments
   - Edit issues
   - View development tools (for PR links)
   - Transition issues (for workflow automation)

   Confluence Permissions:
   - View pages
   - Add comments
   ```

3. **Create OAuth 2.0 App**
   - Go to https://developer.atlassian.com/console/myapps/
   - Click "Create" → "OAuth 2.0 integration"
   - App name: "CiteMed PM Agent"
   - Callback URL: `http://localhost:3000/callback` (for local auth flow)

4. **Configure Permissions (Scopes)**
   ```
   Jira:
   - read:jira-work
   - write:jira-work
   - read:jira-user

   Confluence:
   - read:confluence-content.summary
   - read:confluence-content.all
   - write:confluence-content
   ```

5. **Get Credentials**
   - Copy Client ID
   - Copy Client Secret
   - Generate OAuth tokens using the authorization flow

### Option 2: Dedicated User Account (Simpler)

1. **Create New Atlassian User**
   - Email: `pm-bot@citemed.com`
   - Name: "PM Bot"
   - Send invite

2. **Accept Invitation & Configure**
   - Accept email invite
   - Set password
   - Add profile picture (robot icon recommended)

3. **Create API Token (for Cloud)**
   - Log in as bot user
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create API token: "PM Agent"
   - Copy token (you won't see it again!)

4. **Configure OAuth App** (same as Option 1, Step 3-5)

## Environment Configuration

Update `.env` with bot credentials:

```bash
# Atlassian Bot User Configuration
ATLASSIAN_OAUTH_CLIENT_ID=your_app_client_id
ATLASSIAN_OAUTH_CLIENT_SECRET=your_app_client_secret
ATLASSIAN_OAUTH_REDIRECT_URI=http://localhost:3000/callback
ATLASSIAN_OAUTH_ACCESS_TOKEN=<generated_token>
ATLASSIAN_OAUTH_REFRESH_TOKEN=<generated_refresh_token>

# Atlassian Instance
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
ATLASSIAN_PROJECT_KEY=ECD

# Bot User Account ID (for self-identification)
PM_BOT_ACCOUNT_ID=<lookup_bot_account_id>
```

## Getting OAuth Tokens

### Method 1: OAuth Authorization Flow

```python
# tools/atlassian_oauth_flow.py
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser

CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
CALLBACK_URL = "http://localhost:3000/callback"

# Step 1: Get authorization URL
auth_url = (
    f"https://auth.atlassian.com/authorize?"
    f"audience=api.atlassian.com&"
    f"client_id={CLIENT_ID}&"
    f"scope=read%3Ajira-work%20write%3Ajira-work%20offline_access&"
    f"redirect_uri={CALLBACK_URL}&"
    f"response_type=code&"
    f"prompt=consent"
)

print(f"Opening browser for authentication...")
webbrowser.open(auth_url)

# Step 2: Receive callback and exchange code for tokens
# (Implement HTTP server to catch callback)
# See: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
```

### Method 2: Use Atlassian MCP Built-in Flow

The MCP server handles OAuth automatically:

```bash
# Run the PM agent once to trigger OAuth flow
python run_agent.py standup --dry-run

# Follow browser prompts to authorize
# Tokens will be automatically saved
```

## Verifying Bot Setup

Test that the bot can access Jira:

```python
# tools/test_atlassian_bot.py
from dotenv import load_dotenv
import os
import requests

load_dotenv()

CLOUD_ID = os.getenv("ATLASSIAN_CLOUD_ID")
ACCESS_TOKEN = os.getenv("ATLASSIAN_OAUTH_ACCESS_TOKEN")

# Test API call
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json"
}

# Get current user (should be bot)
response = requests.get(
    f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/myself",
    headers=headers
)

user = response.json()
print(f"Authenticated as: {user['displayName']}")
print(f"Account ID: {user['accountId']}")
print(f"Email: {user.get('emailAddress', 'N/A')}")

# Expected output:
# Authenticated as: PM Bot
# Account ID: 5f8a... (save this to PM_BOT_ACCOUNT_ID)
```

## Bot Behavior

### How Comments Will Appear

**Before (Personal Account):**
```
Ethan Davidson commented 5 minutes ago:
⚠️ SLA Violation - This ticket is 2 days overdue...
```

**After (Bot Account):**
```
PM Bot commented 5 minutes ago:
⚠️ SLA Violation - This ticket is 2 days overdue...
```

### Triggering Bot via @mentions

Team members can trigger the bot by mentioning it:

```
@PM-Bot run standup
@PM-Bot check SLA for ECD-123
@PM-Bot audit productivity for last week
```

(Requires implementing Slack webhook listener or Jira automation trigger)

## Security Best Practices

### Token Storage
- ✅ Store tokens in `.env` (never commit to git)
- ✅ Use environment variables in production
- ✅ Rotate tokens every 90 days
- ❌ Never hardcode credentials in code

### Permission Scoping
- ✅ Grant minimal required permissions
- ✅ Review bot permissions quarterly
- ✅ Log all bot actions for audit trail
- ❌ Don't grant admin permissions

### Access Control
- ✅ Limit who can modify bot credentials
- ✅ Use separate credentials for dev/staging/prod
- ✅ Implement rate limiting for bot API calls
- ❌ Don't share bot credentials with multiple people

## Troubleshooting

### Token Expired Error
```
Error: 401 Unauthorized - Access token expired
```

**Solution:** Refresh the access token using refresh token:

```python
import requests

refresh_response = requests.post(
    "https://auth.atlassian.com/oauth/token",
    headers={"Content-Type": "application/json"},
    json={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    }
)

new_tokens = refresh_response.json()
# Update .env with new access_token
```

### Permission Denied Error
```
Error: 403 Forbidden - Insufficient permissions
```

**Solution:**
1. Check OAuth app scopes include required permissions
2. Verify bot user has Jira project permissions
3. Re-authorize the OAuth app with updated scopes

### Bot User Not Found
```
Error: User 'PM Bot' not found
```

**Solution:**
1. Verify bot user account is created
2. Check bot has accepted Jira/Confluence invitations
3. Ensure bot has logged in at least once

## Migration from Personal to Bot Account

### Step-by-Step Migration

1. **Create bot user** (follow setup above)
2. **Generate new OAuth credentials** for bot
3. **Test bot access** in dev/staging first
4. **Update production .env** with bot credentials
5. **Restart PM agent** to use new credentials
6. **Verify** comments now show as bot user

### No Data Loss

Switching to bot user does NOT affect:
- ✅ Historical PM agent data
- ✅ Existing Jira comments (they keep original author)
- ✅ SLA tracking and compliance data
- ✅ Workflow configurations

Only **new** comments/updates will show as bot user.

## Additional Resources

- [Atlassian OAuth 2.0 Guide](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [Managing API Tokens](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [Atlassian MCP Server Docs](https://github.com/modelcontextprotocol/servers/tree/main/src/atlassian)

---

**Created:** 2025-10-19
**For:** CiteMed PM Agent Autonomous Operation
