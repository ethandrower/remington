# Simplified Architecture - Local Deployment

## Stack Overview

```
┌─────────────────────────────────────────────────────┐
│              Jira / Bitbucket / Slack               │
│                  (send webhooks)                    │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         FastAPI Webhook Server (port 8000)          │
│         - Receives webhooks                         │
│         - Logs to SQLite                            │
│         - Triggers orchestrator                     │
└────────────┬────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│              Simple Orchestrator                     │
│         1. Gather context (fetch from Jira)         │
│         2. Think (ask Claude API)                   │
│         3. Act (comment, update, notify)            │
│         4. Log cycle to SQLite                      │
└────────────┬────────────────┬───────────────────────┘
             │                │
      ┌──────▼─────┐   ┌─────▼──────┐
      │ MCP Client │   │ API Client │
      │ (primary)  │   │ (fallback) │
      └────────────┘   └────────────┘
             │                │
             └────────┬───────┘
                      ▼
      ┌──────────────────────────────┐
      │    Jira / Bitbucket / Slack  │
      │         (via APIs)            │
      └──────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              SQLite Database (local file)            │
│         - agent_cycles (reasoning history)          │
│         - webhook_events (audit log)                │
│         File: ./data/pm_agent.db                    │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. FastAPI Webhook Server
**File:** `src/web/app.py`
**Purpose:** HTTP server to receive webhooks
**Endpoints:**
- `GET /health` - Health check
- `POST /webhooks/jira` - Jira events
- `POST /webhooks/bitbucket` - Bitbucket events
- `POST /webhooks/slack` - Slack events
- `GET /api/stats` - Agent statistics

**Why FastAPI:**
- Fast, modern Python web framework
- Automatic API docs (visit /docs)
- Async support for future scaling
- Built-in request validation

### 2. MCP Client
**File:** `src/clients/mcp_client.py`
**Purpose:** Call MCP servers for semantic operations
**Use cases:**
- "Find all tickets related to authentication"
- "What tickets did Sarah work on this week?"
- "Search for the current sprint"

**How it works:**
- Uses your existing `.mcp.json` configuration
- Spawns MCP processes as needed
- Wraps MCP calls in Python API

### 3. Direct API Clients
**Files:**
- `src/clients/jira_api_client.py`
- `src/clients/slack_api_client.py`
- `src/clients/bitbucket_api_client.py`

**Purpose:** Fallback when MCP unavailable or for specific operations
**Use cases:**
- Add comment to specific ticket
- Move ticket to sprint
- Post Slack message
- Get PR details

### 4. Simple Orchestrator
**File:** `src/orchestration/simple_orchestrator.py`
**Purpose:** Core agent logic
**Flow:**
```python
1. receive_event(webhook_payload)
2. context = gather_context(issue_key)
3. plan = ask_claude_what_to_do(context)
4. actions = execute_plan(plan)
5. log_cycle(context, plan, actions)
```

### 5. SQLite Database
**File:** `./data/pm_agent.db` (automatically created)
**Tables:**
- `agent_cycles` - Every time agent thinks and acts
- `webhook_events` - Audit log of all webhooks received

**Schema:**
```sql
-- Agent reasoning cycles
CREATE TABLE agent_cycles (
    id INTEGER PRIMARY KEY,
    created_at DATETIME,
    trigger_type TEXT,
    trigger_data JSON,
    context_gathered JSON,
    plan JSON,
    actions_taken JSON,
    status TEXT
);

-- Webhook audit log
CREATE TABLE webhook_events (
    id INTEGER PRIMARY KEY,
    received_at DATETIME,
    source TEXT,
    event_type TEXT,
    payload JSON,
    processed TEXT
);
```

## Data Flow Example

### Scenario: Developer adds Jira comment

```
1. Developer adds comment "Can someone review this?" to ECD-123

2. Jira sends webhook:
   POST https://your-server:8000/webhooks/jira
   {
     "webhookEvent": "comment_created",
     "issue": {"key": "ECD-123", ...},
     "comment": {"body": "Can someone review this?", ...}
   }

3. FastAPI receives webhook:
   - Logs to webhook_events table
   - Extracts issue_key = "ECD-123"
   - Calls orchestrator.process_jira_comment(...)

4. Orchestrator gathers context:
   - Calls jira_api.get_issue("ECD-123")
   - Gets: status, assignee, summary, description
   - Context = {issue: {...}, recent_comments: [...]}

5. Orchestrator asks Claude:
   - Prompt: "New comment on ECD-123. Should I respond?"
   - Claude: {should_respond: true, response: "I'll notify the reviewer..."}

6. Orchestrator executes plan:
   - Calls jira_api.add_comment(issue_key, response)
   - Logs action to actions_taken

7. Orchestrator logs cycle:
   - Saves to agent_cycles table
   - Status: "complete"

8. Response to Jira:
   - Returns 200 OK (webhook acknowledged)
```

## File Structure

```
project-manager/
├── src/
│   ├── web/
│   │   └── app.py                    # FastAPI server
│   ├── webhook/
│   │   └── handlers.py               # Webhook processing logic
│   ├── clients/
│   │   ├── mcp_client.py            # MCP wrapper
│   │   ├── jira_api_client.py       # Direct Jira API
│   │   ├── slack_api_client.py      # Direct Slack API
│   │   └── bitbucket_api_client.py  # Direct Bitbucket API
│   ├── orchestration/
│   │   └── simple_orchestrator.py   # Core agent logic
│   └── database/
│       └── models.py                 # SQLAlchemy models
├── data/
│   └── pm_agent.db                   # SQLite database (created automatically)
├── config/
│   └── pm-directives.yaml           # Agent goals and constraints
├── .env                              # Environment variables (secrets)
├── requirements.txt                  # Python dependencies
└── run_agent.py                      # CLI entrypoint
```

## Dependencies

**Core:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - Database ORM
- `anthropic` - Claude API
- `requests` - HTTP client

**No need for:**
- ❌ PostgreSQL (using SQLite)
- ❌ Redis (processing synchronously)
- ❌ Docker (running natively)
- ❌ Complex queue systems

## Deployment

### Development (your laptop)
```bash
python src/web/app.py
# Access: http://localhost:8000
```

### Production (home server)
```bash
# Option 1: Direct
python src/web/app.py

# Option 2: With systemd (auto-restart)
sudo systemctl enable pm-agent
sudo systemctl start pm-agent

# Option 3: With ngrok (for testing webhooks)
ngrok http 8000
# Webhooks → https://abc123.ngrok.io → localhost:8000
```

### Exposing to Internet

**For webhook delivery, you need public access:**

**Option A: ngrok (testing)**
```bash
ngrok http 8000
# Gives you: https://abc123.ngrok.io
# Use this URL when registering Jira webhooks
```

**Option B: Static IP (production)**
```bash
# Configure router:
# Port forward: External 443 → Internal YOUR_SERVER_IP:8000
# Register webhooks: https://YOUR_PUBLIC_IP/webhooks/jira
```

**Option C: Dynamic DNS (if IP changes)**
```bash
# Use service like DuckDNS, No-IP
# Get domain: agent.duckdns.org → your IP (auto-updates)
```

## Monitoring

### Check agent activity
```bash
# View all cycles
sqlite3 ./data/pm_agent.db "SELECT * FROM agent_cycles ORDER BY created_at DESC LIMIT 10;"

# Count by status
sqlite3 ./data/pm_agent.db "SELECT status, COUNT(*) FROM agent_cycles GROUP BY status;"

# View recent webhooks
sqlite3 ./data/pm_agent.db "SELECT * FROM webhook_events ORDER BY received_at DESC LIMIT 10;"
```

### Check server health
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/stats
```

### View logs
```bash
# Server logs (printed to console)
python src/web/app.py

# Or with systemd
sudo journalctl -u pm-agent -f
```

## Scaling Considerations

### When SQLite is enough
- ✅ <100 webhooks/day
- ✅ Single server deployment
- ✅ Agent responds in <10 seconds
- ✅ You're okay with occasional lock delays

### When to upgrade to PostgreSQL
- ⚠️ >1000 webhooks/day
- ⚠️ Multiple agent processes
- ⚠️ Need distributed deployment
- ⚠️ Want advanced querying/analytics

**Good news:** Switching is easy! Just change DATABASE_URL:
```python
# From:
DATABASE_URL = "sqlite:///./data/pm_agent.db"

# To:
DATABASE_URL = "postgresql://user:pass@localhost:5432/pm_agent"
```

Same code, different database. SQLAlchemy handles it.

## Advantages of This Architecture

1. **Simple** - No Docker, no containers, just Python
2. **Fast to iterate** - Change code, restart, done
3. **Easy to debug** - One process, straightforward logs
4. **Reliable** - SQLite is rock-solid
5. **Cheap** - No cloud costs, just API usage
6. **Flexible** - Can upgrade to PostgreSQL/Redis later if needed

## Cost Estimate

**Infrastructure:** $0/month (runs on your server)
**Claude API:** ~$5-15/day (depends on usage)
**Total:** ~$150-450/month

Compare to Heroku:
- Basic dyno: $7/month
- PostgreSQL: $9/month
- Total: ~$16/month + API costs

**But:** Home server gives you MCP access and full control!

---

**This architecture prioritizes simplicity and iteration speed over premature optimization.**
