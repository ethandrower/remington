# PM Agent Implementation Roadmap
**From Zero to Working Agent in Phases**

Based on `orchestration-layer-implementation-plan-v3-final.md` but streamlined for rapid iteration.

---

## Decision: Simplified Local Deployment

### Architecture Decisions

✅ **SQLite instead of PostgreSQL** - Zero setup, perfect for single server
✅ **No Redis** - Process webhooks synchronously (can add later if needed)
✅ **No Docker** - Just Python processes, simpler to debug
✅ **MCP + API hybrid** - Best of both worlds
✅ **Home server** - Full control, no cloud costs

### Why This Works

**For a home server:**
- One agent process, not distributed system
- Modest traffic (<100 webhooks/day)
- SQLite handles this easily (it's what powers your browser!)
- Can always upgrade to PostgreSQL later if needed

**Simplicity wins:**
- Fewer moving parts = less to break
- Easier to understand and debug
- Faster to get started
- Can iterate quickly

---

## Implementation Strategy

### Approach: Incremental Build

**NOT:** Build everything, then test
**YES:** Build minimal version, test, iterate

### Phases Overview

1. **Phase 0: Hello World** (1 hour) - Basic webhook server running
2. **Phase 1: MCP Integration** (2-3 hours) - Can call MCP servers
3. **Phase 2: First Cycle** (3-4 hours) - One complete agent cycle works
4. **Phase 3: Real Webhooks** (2 hours) - Connected to Jira/Bitbucket
5. **Phase 4: Production** (ongoing) - Monitoring, tuning, learning

**Total to MVP: ~1-2 days of focused work**

---

## PHASE 0: Hello World Webhook Server
**Goal:** Server running, accepting webhooks, logging them
**Time:** 1 hour
**Deliverable:** Can curl endpoints and see logs

### 0.1: Create Basic Structure

```bash
# Create directory structure
mkdir -p src/{web,webhook,clients,database,orchestration}
mkdir -p config tests docs/architecture

# Create __init__.py files
touch src/__init__.py
touch src/web/__init__.py
touch src/webhook/__init__.py
touch src/clients/__init__.py
touch src/database/__init__.py
touch src/orchestration/__init__.py
```

### 0.2: Minimal FastAPI Server

Create `src/web/app.py`:

```python
"""Minimal webhook server - Phase 0"""
from fastapi import FastAPI, Request
from datetime import datetime
import json

app = FastAPI(title="PM Agent - Hello World")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "phase": "0 - Hello World"
    }

@app.post("/webhooks/jira")
async def jira_webhook(request: Request):
    payload = await request.json()
    print(f"📥 Jira webhook: {json.dumps(payload, indent=2)}")
    return {"status": "received"}

@app.post("/webhooks/bitbucket")
async def bitbucket_webhook(request: Request):
    payload = await request.json()
    print(f"📥 Bitbucket webhook: {json.dumps(payload, indent=2)}")
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 0.3: Test Locally

```bash
# Install dependencies
pip install fastapi uvicorn[standard]

# Run server
python src/web/app.py

# In another terminal, test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/webhooks/jira -H "Content-Type: application/json" -d '{"test": "hello"}'
```

**Success Criteria:**
- ✅ Server starts without errors
- ✅ Health endpoint returns JSON
- ✅ Webhooks print payload to console
- ✅ You see "📥 Jira webhook: ..." in logs

---

## PHASE 1: MCP Integration
**Goal:** Server can call MCP tools successfully
**Time:** 2-3 hours
**Deliverable:** `/api/test-mcp` endpoint that searches Jira via MCP

### 1.1: Understand Your MCP Setup

```bash
# Check your MCP configuration
cat ~/.config/claude-code/.mcp.json || cat .mcp.json

# Test MCP manually in Claude Code first
# Make sure you can use mcp__atlassian__* tools
```

### 1.2: Create MCP Client Wrapper

Create `src/clients/mcp_client.py`:

```python
"""MCP Client - calls your MCP servers"""
import subprocess
import json
from typing import Optional

class MCPError(Exception):
    pass

class MCPClient:
    """
    Wrapper around MCP functionality

    Note: This requires MCP servers to be running!
    We'll call them via subprocess for now.
    """

    def jira_search_issues(self, jql: str, max_results: int = 10) -> list:
        """
        Search Jira using MCP

        For now, we'll use a simple approach:
        - Start npx @modelcontextprotocol/server-atlassian
        - Send search request
        - Parse response

        TODO: Replace with proper MCP client library when available
        """
        # Placeholder - you'll need to implement based on your MCP setup
        # This depends on how you invoke MCP tools
        raise NotImplementedError("MCP client needs your specific setup")

    def test_connection(self) -> dict:
        """Test MCP is accessible"""
        try:
            # Try to call a simple MCP operation
            # For now, just check if MCP config exists
            import os
            mcp_config = os.path.expanduser("~/.config/claude-code/.mcp.json")
            if os.path.exists(mcp_config):
                with open(mcp_config) as f:
                    config = json.load(f)
                return {
                    "status": "config_found",
                    "servers": list(config.get("mcpServers", {}).keys())
                }
            else:
                return {"status": "no_config"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

### 1.3: Create Direct API Client (Fallback)

Create `src/clients/jira_api_client.py`:

```python
"""Direct Jira API client - fallback when MCP unavailable"""
import requests
import os
from typing import Dict, List

class JiraAPIClient:
    def __init__(self):
        self.domain = os.getenv("ATLASSIAN_DOMAIN", "citemed.atlassian.net")
        self.email = os.getenv("ATLASSIAN_EMAIL")
        self.token = os.getenv("ATLASSIAN_API_TOKEN")
        self.auth = (self.email, self.token)

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict]:
        """Search via JQL - works anywhere"""
        url = f"https://{self.domain}/rest/api/3/search"

        response = requests.get(
            url,
            auth=self.auth,
            headers={"Accept": "application/json"},
            params={"jql": jql, "maxResults": max_results}
        )
        response.raise_for_status()

        data = response.json()
        return data.get("issues", [])

    def get_issue(self, issue_key: str) -> Dict:
        """Get specific issue"""
        url = f"https://{self.domain}/rest/api/3/issue/{issue_key}"

        response = requests.get(
            url,
            auth=self.auth,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()

        return response.json()
```

### 1.4: Add Test Endpoints

Update `src/web/app.py`:

```python
from src.clients.mcp_client import MCPClient, MCPError
from src.clients.jira_api_client import JiraAPIClient

# Add to app.py

@app.get("/api/test-mcp")
async def test_mcp():
    """Test MCP connection"""
    mcp = MCPClient()
    result = mcp.test_connection()
    return result

@app.get("/api/test-api")
async def test_api():
    """Test direct API"""
    api = JiraAPIClient()
    try:
        # Search for recent issues
        issues = api.search_issues("project = ECD ORDER BY created DESC", max_results=5)
        return {
            "status": "success",
            "issue_count": len(issues),
            "sample": issues[0]["key"] if issues else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Test:**
```bash
# Load environment
source .env

# Test API client
curl http://localhost:8000/api/test-api

# Test MCP client
curl http://localhost:8000/api/test-mcp
```

**Success Criteria:**
- ✅ API client can fetch real Jira issues
- ✅ MCP client can detect your MCP configuration
- ✅ Both endpoints return without crashing

---

## PHASE 2: First Complete Cycle
**Goal:** Receive webhook → Think → Act → Log
**Time:** 3-4 hours
**Deliverable:** Jira comment triggers agent to analyze and respond

### 2.1: Database for State (SQLite - Simple!)

**No Docker needed!** SQLite is built into Python.

Create `src/database/models.py`:

```python
"""Database models - using SQLite for simplicity"""
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class AgentCycle(Base):
    """Record of agent reasoning cycle"""
    __tablename__ = "agent_cycles"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    trigger_type = Column(String)  # "webhook", "schedule", "manual"
    trigger_data = Column(JSON)
    context_gathered = Column(JSON)
    plan = Column(JSON)
    actions_taken = Column(JSON)
    status = Column(String)  # "complete", "failed", "partial"

class WebhookEvent(Base):
    """Audit log of webhooks"""
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String)  # "jira", "bitbucket", "slack"
    event_type = Column(String)
    event_type = Column(String)
    payload = Column(JSON)
    processed = Column(String, default="pending")  # "pending", "processed", "skipped"

# SQLite database - just a file!
DB_PATH = os.getenv("DB_PATH", "./data/pm_agent.db")

# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Create tables"""
    Base.metadata.create_all(engine)
    print(f"✅ Database initialized at {DB_PATH}")

def get_session():
    """Get database session"""
    return SessionLocal()
```

**That's it! No Docker, no PostgreSQL, no Redis.**

### 2.2: Simple Orchestrator

Create `src/orchestration/simple_orchestrator.py`:

```python
"""Simple orchestrator - Phase 2"""
from src.database.models import get_session, AgentCycle
from src.clients.jira_api_client import JiraAPIClient
from anthropic import Anthropic
import os
import json
from datetime import datetime

class SimpleOrchestrator:
    """
    Minimal orchestrator for Phase 2

    Flow:
    1. Receive event (Jira comment added)
    2. Gather context (get issue details)
    3. Think (ask Claude what to do)
    4. Act (add comment back)
    5. Log everything
    """

    def __init__(self):
        self.jira = JiraAPIClient()
        self.claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def process_jira_comment(self, issue_key: str, comment_text: str, commenter: str):
        """Process new Jira comment"""

        print(f"\n🔄 Starting agent cycle for {issue_key}")

        # 1. Gather context
        context = self.gather_context(issue_key)

        # 2. Think (ask Claude)
        plan = self.make_plan(issue_key, comment_text, commenter, context)

        # 3. Act
        actions_taken = self.execute_plan(plan)

        # 4. Log
        self.log_cycle("webhook", {
            "issue_key": issue_key,
            "comment": comment_text
        }, context, plan, actions_taken, "complete")

        print(f"✅ Cycle complete\n")

        return {"status": "complete", "actions": len(actions_taken)}

    def gather_context(self, issue_key: str) -> dict:
        """Gather context about the issue"""
        issue = self.jira.get_issue(issue_key)

        context = {
            "issue": {
                "key": issue_key,
                "summary": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "assignee": issue["fields"].get("assignee", {}).get("displayName") if issue["fields"].get("assignee") else "Unassigned"
            }
        }

        print(f"📊 Context: {issue_key} - {context['issue']['summary']}")

        return context

    def make_plan(self, issue_key: str, comment: str, commenter: str, context: dict) -> dict:
        """Ask Claude to make a plan"""

        prompt = f"""
You are a PM agent. A comment was just added to Jira ticket {issue_key}.

CONTEXT:
- Issue: {context['issue']['summary']}
- Status: {context['issue']['status']}
- Assignee: {context['issue']['assignee']}

NEW COMMENT (from {commenter}):
"{comment}"

Should you respond? If yes, what should you say?

Respond in JSON:
{{
  "should_respond": true/false,
  "response": "Your response text here",
  "reasoning": "Why you're responding this way"
}}
"""

        message = self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse Claude's response
        response_text = message.content[0].text

        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            plan = json.loads(json_match.group())
        else:
            plan = {"should_respond": False, "reasoning": "Could not parse response"}

        print(f"🧠 Plan: {plan.get('reasoning')}")

        return plan

    def execute_plan(self, plan: dict) -> list:
        """Execute the plan"""
        actions = []

        if plan.get("should_respond"):
            # For Phase 2, just print - don't actually comment yet
            print(f"💬 Would respond: {plan['response']}")
            actions.append({
                "type": "jira_comment",
                "text": plan["response"],
                "status": "simulated"  # Change to "executed" when ready
            })
        else:
            print(f"⏭️  No action needed: {plan.get('reasoning')}")

        return actions

    def log_cycle(self, trigger_type: str, trigger_data: dict, context: dict,
                  plan: dict, actions: list, status: str):
        """Log cycle to database"""
        session = get_session()

        cycle = AgentCycle(
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            context_gathered=context,
            plan=plan,
            actions_taken=actions,
            status=status
        )

        session.add(cycle)
        session.commit()
        session.close()
```

### 2.3: Connect Webhook to Orchestrator

Update `src/web/app.py`:

```python
from src.orchestration.simple_orchestrator import SimpleOrchestrator
from src.database.models import get_session, WebhookEvent

orchestrator = SimpleOrchestrator()

@app.post("/webhooks/jira")
async def jira_webhook(request: Request):
    payload = await request.json()

    # Log webhook
    session = get_session()
    event = WebhookEvent(
        source="jira",
        event_type=payload.get("webhookEvent"),
        payload=payload
    )
    session.add(event)
    session.commit()
    session.close()

    # Check if it's a comment event
    if payload.get("webhookEvent") == "comment_created":
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        comment = payload.get("comment", {})
        comment_text = comment.get("body")
        commenter = comment.get("author", {}).get("displayName", "Unknown")

        # Process in background (for now, synchronously)
        result = orchestrator.process_jira_comment(issue_key, comment_text, commenter)

        return {"status": "processed", "result": result}

    return {"status": "received"}
```

### 2.4: Test Full Cycle

```bash
# Initialize database (creates ./data/pm_agent.db file)
python -c "from src.database.models import init_db; init_db()"

# Start server
python src/web/app.py

# Simulate webhook (in another terminal)
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "comment_created",
    "issue": {"key": "ECD-123", "fields": {"summary": "Test issue", "status": {"name": "In Progress"}}},
    "comment": {"body": "Can someone review this?", "author": {"displayName": "Sarah"}}
  }'

# View database (optional)
sqlite3 ./data/pm_agent.db "SELECT * FROM agent_cycles;"
sqlite3 ./data/pm_agent.db "SELECT * FROM webhook_events;"
```

**Success Criteria:**
- ✅ Webhook received and logged to database
- ✅ Orchestrator gathers context from Jira
- ✅ Claude generates a response plan
- ✅ Cycle logged to database
- ✅ See "🔄 Starting agent cycle..." in logs

---

## PHASE 3: Real Webhooks
**Goal:** Jira/Bitbucket actually calling your server
**Time:** 2 hours
**Deliverable:** Real events triggering agent

### 3.1: Expose Server Publicly

**Option A: ngrok (for testing)**
```bash
# Install ngrok
brew install ngrok

# Start tunnel
ngrok http 8000

# You'll get: https://abc123.ngrok.io -> localhost:8000
```

**Option B: Your Static IP (production)**
```bash
# Configure router port forwarding
# External 443 -> Internal YOUR_SERVER_IP:8000

# Test externally
curl https://YOUR_PUBLIC_IP:8000/health
```

### 3.2: Register Webhooks

```bash
# Use the script from orchestration plan
python scripts/register_webhooks.py --service jira --url https://YOUR_PUBLIC_URL
```

### 3.3: Test with Real Jira

1. Go to Jira
2. Add comment to any ECD ticket
3. Watch your server logs
4. See agent respond!

**Success Criteria:**
- ✅ Jira actually sends webhook to your server
- ✅ Agent processes real events
- ✅ Can see cycles in database

---

## PHASE 4: Production
**Goal:** Running reliably, monitoring, iterating
**Time:** Ongoing

### 4.1: Enable Real Actions

In `simple_orchestrator.py`, change:
```python
"status": "simulated"  # Change to "executed"
```

And actually call:
```python
self.jira.add_comment(issue_key, plan["response"])
```

### 4.2: Add More Triggers

- Blocked tickets
- PR created/merged
- Sprint started
- Daily health check

### 4.3: Monitoring

```python
# Add to app.py
@app.get("/api/stats")
async def stats():
    session = get_session()

    from sqlalchemy import func
    from src.database.models import AgentCycle

    total_cycles = session.query(func.count(AgentCycle.id)).scalar()
    today_cycles = session.query(func.count(AgentCycle.id)).filter(
        AgentCycle.created_at >= datetime.utcnow().date()
    ).scalar()

    return {
        "total_cycles": total_cycles,
        "today_cycles": today_cycles
    }
```

---

## Quick Start Checklist

- [ ] Phase 0: Basic webhook server running (1 hour)
- [ ] Phase 1: MCP + API clients working (2 hours)
- [ ] Phase 2: First complete cycle working (3 hours)
- [ ] Phase 3: Real webhooks connected (2 hours)
- [ ] Phase 4: Production ready (ongoing)

**Total: 1-2 days to working agent!**

---

## Next Steps After This

1. **Add More Intelligence:** Better prompts, more context
2. **Add More Actions:** Slack notifications, ticket transitions
3. **Add Scheduling:** Periodic checks, not just webhooks
4. **Add Directives:** Load from `config/pm-directives.yaml`
5. **Add Dashboard:** Web UI to see agent activity

---

Ready to start with Phase 0?
