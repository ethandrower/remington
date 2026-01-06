# Heroku Deployment: MCP Authentication Challenge

## The Problem

**Model Context Protocol (MCP) servers cannot run on Heroku.**

MCPs are local server processes that run on your machine and provide tools like `mcp__atlassian__*` and `mcp__filesystem__*`. When you deploy to Heroku:

1. ❌ Local `.mcp.json` won't work (no local filesystem)
2. ❌ MCP servers won't be running (no way to start them)
3. ❌ OAuth flows require browser interaction (Heroku is headless)
4. ❌ Filesystem MCP can't access the citemed_web repository

## The Solution: Direct API Integration

For Heroku deployment, you need to **bypass MCPs** and use **direct API calls** to Atlassian and other services.

### Architecture Comparison

**Local Development (with MCPs):**
```
Claude Code → MCP Atlassian Server → Atlassian Cloud
```

**Heroku Production (without MCPs):**
```
Python Bot → Direct HTTP API calls → Atlassian Cloud
```

---

## Implementation Strategy

### 1. Atlassian API Access

**Option A: API Token Authentication (Recommended)**

Use Atlassian API tokens for server-to-server auth (no OAuth, no browser).

**Setup Steps:**
1. Create an API token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token (save it securely)

2. Add to Heroku config vars:
   ```bash
   heroku config:set ATLASSIAN_SERVICE_ACCOUNT_EMAIL="your-email@example.com"
   heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="your-api-token"
   heroku config:set ATLASSIAN_CLOUD_ID="67bbfd03-b309-414f-9640-908213f80628"
   ```

3. Use Basic Auth in API calls:
   ```python
   import requests
   import base64
   import os

   def jira_api_call(endpoint, method="GET", json_data=None):
       """Make direct Jira API call without MCP."""
       email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL')
       token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN')
       cloud_id = os.getenv('ATLASSIAN_CLOUD_ID')

       # Basic Auth
       credentials = f"{email}:{token}"
       encoded = base64.b64encode(credentials.encode()).decode()

       headers = {
           'Authorization': f'Basic {encoded}',
           'Content-Type': 'application/json'
       }

       url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/{endpoint}"

       response = requests.request(method, url, headers=headers, json=json_data)
       response.raise_for_status()
       return response.json()
   ```

**Option B: OAuth 2.0 (Complex, requires additional setup)**

Not recommended for autonomous agents because:
- Requires periodic token refresh
- Initial auth needs browser interaction
- More complex error handling

---

### 2. Bitbucket API Access

**Same API token works for Bitbucket:**

```python
def bitbucket_api_call(endpoint, method="GET", json_data=None):
    """Make direct Bitbucket API call."""
    email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL')
    token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN')

    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/json'
    }

    url = f"https://api.bitbucket.org/2.0/{endpoint}"

    response = requests.request(method, url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()
```

---

### 3. Slack API Access

**Slack Bot Token (straightforward):**

1. Create Slack app: https://api.slack.com/apps
2. Enable Bot Token Scopes:
   - `chat:write`
   - `chat:write.public`
   - `channels:read`
   - `users:read`
3. Install app to workspace
4. Copy Bot User OAuth Token (starts with `xoxb-`)

5. Add to Heroku:
   ```bash
   heroku config:set SLACK_BOT_TOKEN="xoxb-your-token"
   heroku config:set SLACK_CHANNEL_STANDUP="C123ABC456"
   ```

6. Use in code:
   ```python
   import requests

   def slack_post_message(channel, text):
       """Post message to Slack."""
       token = os.getenv('SLACK_BOT_TOKEN')

       response = requests.post(
           'https://slack.com/api/chat.postMessage',
           headers={'Authorization': f'Bearer {token}'},
           json={'channel': channel, 'text': text}
       )

       return response.json()
   ```

---

### 4. Git Repository Access (citemed_web)

**Problem:** Filesystem MCP can't access `/Users/ethand320/code/citemed/citemed_web/` on Heroku.

**Solution:** Use Git API or clone repo temporarily.

**Option A: Read-only GitHub/Bitbucket API**

Access files via API without cloning:

```python
def get_file_from_git(repo_slug, file_path, branch="main"):
    """Fetch file content from Bitbucket."""
    workspace = "citemed"  # your workspace slug

    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/src/{branch}/{file_path}"

    # Use same Atlassian credentials
    email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL')
    token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN')
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.get(url, headers={'Authorization': f'Basic {encoded}'})
    response.raise_for_status()

    return response.text  # file contents
```

**Option B: Shallow Git Clone (if needed)**

Clone only the latest commit on demand:

```python
import subprocess
import tempfile
import os

def analyze_code_with_git(repo_url, file_pattern):
    """Clone repo, analyze files, clean up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Shallow clone (only latest commit)
        subprocess.run([
            'git', 'clone', '--depth=1',
            repo_url, tmpdir
        ], check=True)

        # Analyze files
        # ... your analysis code ...

        # tmpdir automatically deleted when context exits
```

**Trade-offs:**
- API access: Faster, lighter, limited to file reads
- Git clone: Slower, heavier, enables complex git operations

---

## Implementation Checklist

### Phase 1: Replace MCP Calls (High Priority)

- [ ] Create `utils/atlassian_api.py` with direct API helpers:
  - [ ] `jira_get_issue(issue_key)`
  - [ ] `jira_search_issues(jql)`
  - [ ] `jira_add_comment(issue_key, comment)`
  - [ ] `jira_create_issue(fields)`
  - [ ] `jira_transition_issue(issue_key, transition_id)`

- [ ] Create `utils/bitbucket_api.py` with PR helpers:
  - [ ] `get_pull_requests(repo_slug, state="OPEN")`
  - [ ] `get_pr_commits(repo_slug, pr_id)`
  - [ ] `add_pr_comment(repo_slug, pr_id, comment)`

- [ ] Create `utils/slack_api.py` with messaging helpers:
  - [ ] `post_message(channel, text, blocks=None)`
  - [ ] `post_thread_reply(channel, thread_ts, text)`
  - [ ] `lookup_user(email)`

- [ ] Update `run_agent.py` to use API helpers instead of MCP tools

### Phase 2: Test Authentication (Critical)

- [ ] Test Atlassian API token locally:
  ```bash
  python scripts/test_atlassian_auth.py
  ```

- [ ] Test Slack bot token locally:
  ```bash
  python scripts/test_slack_auth.py
  ```

- [ ] Test all API helpers with real credentials:
  ```bash
  python scripts/test_api_integration.py
  ```

### Phase 3: Environment Configuration

- [ ] Update `.env.example` with API token placeholders
- [ ] Update `app.json` with required API tokens
- [ ] Create `scripts/heroku_config.sh` for easy config setup
- [ ] Document token generation in `docs/API_SETUP.md`

### Phase 4: Heroku Deployment

- [ ] Deploy to Heroku (with API tokens configured)
- [ ] Test standup workflow remotely:
  ```bash
  heroku run python run_agent.py standup
  ```
- [ ] Monitor logs for auth issues:
  ```bash
  heroku logs --tail --dyno worker
  ```
- [ ] Enable worker dyno:
  ```bash
  heroku ps:scale worker=1
  ```

---

## Alternative: Hybrid Approach

**Use MCPs locally, API calls on Heroku:**

```python
def get_jira_issue(issue_key):
    """Get Jira issue using available method."""
    if os.getenv('HEROKU'):
        # Use direct API
        return jira_api_call(f"issue/{issue_key}")
    else:
        # Use MCP (Claude Code environment)
        return mcp__atlassian__getJiraIssue(issueIdOrKey=issue_key)
```

**Benefits:**
- Keep MCP convenience for local development
- Use reliable API calls for production
- Single codebase for both environments

**Implementation:**
```python
# utils/platform_detect.py
def is_heroku():
    return os.getenv('DYNO') is not None

def is_mcp_available():
    return not is_heroku()  # MCPs only work locally
```

---

## Security Best Practices

### Secrets Management

1. **NEVER commit secrets to git:**
   - `.env` must be in `.gitignore`
   - Use Heroku config vars for production
   - Use environment variables for all credentials

2. **Use service accounts:**
   - Create dedicated "PM Bot" Atlassian account
   - Use least-privilege permissions
   - Separate tokens for dev/staging/prod

3. **Rotate credentials regularly:**
   - Set calendar reminder to rotate API tokens quarterly
   - Have backup tokens ready for zero-downtime rotation

4. **Monitor access logs:**
   - Check Atlassian audit logs for unexpected API usage
   - Set up Slack alerts for failed auth attempts

### Token Permissions

**Atlassian API Token Permissions:**
- Read access: Jira issues, Bitbucket repositories
- Write access: Jira comments, issue transitions, Bitbucket PR comments
- No access: User management, admin settings

**Slack Bot Token Scopes:**
- `chat:write` - Post messages as bot
- `chat:write.public` - Post in public channels without joining
- `channels:read` - List channels
- `users:read` - Lookup user IDs by email

---

## Testing Strategy

### Local Testing (with API tokens)

```bash
# Copy .env.example to .env
cp .env.example .env

# Add your API tokens to .env
# vim .env

# Test API integration
python scripts/test_api_integration.py

# Expected output:
# ✅ Jira API: Successfully fetched ECD-123
# ✅ Bitbucket API: Successfully listed PRs
# ✅ Slack API: Successfully posted test message
# ✅ All integrations working!
```

### Heroku Testing (staging)

```bash
# Create Heroku app
heroku create citemed-pm-agent-staging

# Set config vars
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_EMAIL="..."
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="..."
heroku config:set SLACK_BOT_TOKEN="..."
heroku config:set SLACK_CHANNEL_STANDUP="..."
heroku config:set DRY_RUN=true  # Safe testing

# Deploy
git push heroku main

# Test one-off standup
heroku run python run_agent.py standup

# Check logs
heroku logs --tail

# If successful, enable worker
heroku ps:scale worker=1

# Disable dry run for real operations
heroku config:set DRY_RUN=false
```

---

## Common Issues & Solutions

### Issue: "Authentication failed - 401 Unauthorized"

**Cause:** Invalid or expired API token

**Solution:**
1. Regenerate API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Update Heroku config: `heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="new-token"`
3. Restart worker: `heroku restart`

### Issue: "Slack error: not_in_channel"

**Cause:** Bot not invited to channel

**Solution:**
1. Invite bot to channel: `/invite @PM Agent Bot`
2. Or use `chat:write.public` scope to post without joining

### Issue: "Rate limited - 429 Too Many Requests"

**Cause:** Exceeded Atlassian API rate limits

**Solution:**
1. Reduce polling frequency in `clock.py`
2. Implement exponential backoff in API helpers
3. Cache frequently accessed data (e.g., epic metadata)

### Issue: "Git repository not accessible"

**Cause:** Trying to use filesystem paths that don't exist on Heroku

**Solution:**
1. Use Bitbucket API to access files: `get_file_from_git()`
2. Or use shallow git clone: `git clone --depth=1`
3. Store analysis results in Heroku Postgres (if needed)

---

## Next Steps

1. **Create API utility modules** (`utils/atlassian_api.py`, `utils/slack_api.py`)
2. **Write integration tests** (`scripts/test_api_integration.py`)
3. **Document token generation** (`docs/API_SETUP.md`)
4. **Test locally with API tokens** (no MCPs)
5. **Deploy to Heroku staging**
6. **Monitor and iterate**
7. **Deploy to production**

---

## Related Documentation

- [API Setup Guide](./API_SETUP.md) - How to generate all required tokens
- [Heroku Deployment Guide](./HEROKU_DEPLOYMENT.md) - Step-by-step deployment instructions
- [Architecture Overview](../README.md) - System architecture and design decisions
- [Atlassian OAuth Apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/) - Official docs
- [Slack API Documentation](https://api.slack.com/docs) - Official Slack API reference
