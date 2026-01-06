# PM Agent Orchestration Layer - Implementation Plan v3
## Home Server Deployment with MCP + Direct API Hybrid

## Project Context

We're building a goal-based autonomous PM agent that runs on a home server with static IP. The agent will use:
- **MCP** for semantic search and discovery (finding issues, understanding context)
- **Direct APIs** as fallback and for specific operations when MCP gets stuck
- **Webhooks** via static IP for real-time event processing
- **Claude Code** as specialized worker for complex tasks

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Webhook Server (FastAPI)                    │
│         (Exposed via Static IP + SSL)                    │
│   /webhooks/jira  /webhooks/bitbucket  /webhooks/slack   │
└────────────┬────────────────────────────────────────────┘
             │ Events come in real-time
             ▼
┌──────────────────────────────────────────────────────────┐
│              Event Queue (Local Redis)                   │
│  Buffers events, deduplicates, manages processing order  │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│         Orchestration Layer (Core Agent Logic)           │
│   - Goal-based reasoning via Claude API                  │
│   - State management (Local PostgreSQL)                  │
│   - Action planning and execution routing                │
└────────────┬─────────────────────┬───────────────────────┘
             │                     │
     ┌───────▼────────┐    ┌──────▼──────────────────┐
     │  MCP Clients   │    │  Direct API Clients     │
     │  (Primary)     │    │  (Fallback/Specific)    │
     │                │    │                         │
     │  - Semantic    │    │  - add_comment()        │
     │    search      │    │  - get_issue(key)       │
     │  - Discovery   │    │  - move_to_sprint()     │
     │  - Context     │    │  - post_slack_message() │
     └────────┬───────┘    └─────────────────────────┘
              │
              ▼
     ┌────────────────────┐
     │  Claude Code Agent │
     │  (Same Machine)    │
     │  - Complex tasks   │
     │  - Uses MCP skills │
     │  - Document gen    │
     └────────────────────┘
```

## Key Design Decisions

### 1. **MCP as Primary, APIs as Fallback**
```python
class ActionExecutor:
    def execute_action(self, action: dict):
        try:
            # Try MCP first (better for semantic operations)
            if action["type"] in self.mcp_capable_actions:
                return self.execute_via_mcp(action)
        except MCPError as e:
            # Fallback to direct API if MCP fails
            logger.warning(f"MCP failed: {e}, falling back to API")
            return self.execute_via_api(action)
```

**Use MCP for:**
- "Find all tickets related to authentication"
- "Search for the new sprint"
- "What tickets did Sarah work on this week?"
- Discovery and semantic queries

**Use Direct API for:**
- Adding specific comment to known ticket
- Moving ticket PROJ-123 to sprint 42
- Posting message to #engineering
- Recovery when MCP is stuck/unresponsive

### 2. **Home Server Infrastructure**
- Docker Compose for all services
- Postgres for state persistence
- Redis for event queue
- Nginx for SSL termination
- Systemd for auto-restart
- Cloudflare for DDoS protection (optional)

### 3. **Static IP Setup**
- Port forwarding: 443 → 8443 (webhooks)
- Let's Encrypt SSL certificates
- Domain name (optional): agent.yourdomain.com
- Firewall rules: Only allow HTTPS, SSH

## Phase 0: Infrastructure Setup

### Task 0.1: Home Server Preparation
**Objective**: Prepare home server for production-like deployment

**System Requirements:**
- Linux (Ubuntu 22.04+ recommended)
- 4GB+ RAM
- 50GB+ disk space
- Python 3.11+
- Docker + Docker Compose
- Static IP configured on router

**Initial Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Install other dependencies
sudo apt install nginx certbot python3-certbot-nginx git

# Clone project repo
cd ~/
git clone <your-repo-url> pm-agent
cd pm-agent
```

**Deliverable:**
- Server ready with Docker installed
- Repository cloned
- User has Docker permissions

### Task 0.2: Network Configuration
**Objective**: Configure router and firewall for webhook access

**Router Configuration:**
```
1. Reserve static local IP for your server (e.g., 192.168.1.100)
2. Port forwarding rules:
   - External port 443 → Internal 192.168.1.100:8443
   - External port 80 → Internal 192.168.1.100:8080 (for SSL cert)
3. Note your public IP address
```

**Firewall Configuration:**
```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for certbot)
sudo ufw allow 443/tcp   # HTTPS (webhooks)
sudo ufw enable
```

**Optional: Dynamic DNS** (if ISP changes IP occasionally)
```bash
# Use service like DuckDNS, No-IP, or Cloudflare
# Example with DuckDNS:
# 1. Create account at duckdns.org
# 2. Create subdomain: pm-agent.duckdns.org
# 3. Install update client:

echo url="https://www.duckdns.org/update?domains=pm-agent&token=YOUR_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -
chmod 700 ~/duckdns/duck.sh

# Add to crontab (update every 5 minutes)
*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

**Deliverable:**
- Port forwarding configured
- Firewall rules set
- (Optional) Dynamic DNS set up
- Document public IP/hostname in `docs/network-setup.md`

### Task 0.3: SSL Certificate Setup
**Objective**: Set up Let's Encrypt SSL for webhook endpoints

**Option A: With Domain Name (Recommended)**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (domain must point to your IP)
sudo certbot certonly --nginx -d agent.yourdomain.com

# Certificate will be at:
# /etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/agent.yourdomain.com/privkey.pem

# Auto-renewal (certbot installs cron job automatically)
sudo certbot renew --dry-run
```

**Option B: Self-Signed (Development/Testing)**
```bash
# Generate self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./certs/privkey.pem \
  -out ./certs/fullchain.pem \
  -subj "/CN=your-ip-address"
```

**Deliverable:**
- SSL certificates obtained
- Certificates accessible to Docker containers
- Auto-renewal configured
- Document cert paths in `config/ssl-config.yaml`

### Task 0.4: Docker Compose Infrastructure
**Objective**: Define all services in Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL for state management
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: pm_agent
      POSTGRES_USER: pm_agent
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./src/database/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pm_agent"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for event queue and caching
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Webhook API server
  webhook-server:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://pm_agent:${DB_PASSWORD}@postgres:5432/pm_agent
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ATLASSIAN_API_TOKEN=${ATLASSIAN_API_TOKEN}
      - ATLASSIAN_EMAIL=${ATLASSIAN_EMAIL}
      - ATLASSIAN_DOMAIN=${ATLASSIAN_DOMAIN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - BITBUCKET_TOKEN=${BITBUCKET_TOKEN}
      - ENVIRONMENT=production
    volumes:
      - ./src:/app/src
      - ./config:/app/config
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "8443:8443"
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: uvicorn src.web.app:app --host 0.0.0.0 --port 8443 --ssl-keyfile /etc/letsencrypt/live/agent.yourdomain.com/privkey.pem --ssl-certfile /etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem

  # Event processor worker
  event-processor:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://pm_agent:${DB_PASSWORD}@postgres:5432/pm_agent
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ATLASSIAN_API_TOKEN=${ATLASSIAN_API_TOKEN}
      - ATLASSIAN_EMAIL=${ATLASSIAN_EMAIL}
      - ATLASSIAN_DOMAIN=${ATLASSIAN_DOMAIN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - BITBUCKET_TOKEN=${BITBUCKET_TOKEN}
      - ENVIRONMENT=production
    volumes:
      - ./src:/app/src
      - ./config:/app/config
      - ~/.config/claude-code:/root/.config/claude-code:ro  # MCP configs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: python -m src.orchestration.event_processor

  # Optional: Monitoring dashboard
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://pm_agent:${DB_PASSWORD}@postgres:5432/pm_agent
      - REDIS_URL=redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    command: uvicorn src.web.dashboard:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
  redis_data:
```

**Environment File (`.env`):**
```bash
# .env (DO NOT COMMIT)
DB_PASSWORD=your_secure_password_here
ANTHROPIC_API_KEY=sk-ant-xxx
ATLASSIAN_API_TOKEN=xxx
ATLASSIAN_EMAIL=your-email@company.com
ATLASSIAN_DOMAIN=your-company.atlassian.net
SLACK_BOT_TOKEN=xoxb-xxx
BITBUCKET_TOKEN=xxx
BITBUCKET_WORKSPACE=your-workspace
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8443/health || exit 1

# Default command (overridden in docker-compose)
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8443"]
```

**Requirements.txt:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
anthropic==0.7.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
requests==2.31.0
pydantic==2.5.0
python-dotenv==1.0.0
paramiko==3.3.1  # For SSH to Claude Code if needed later
```

**Deliverable:**
- `docker-compose.yml` complete
- `Dockerfile` working
- `.env.example` for reference
- All services start successfully
- Health checks passing

### Task 0.5: Systemd Service for Auto-Start
**Objective**: Ensure agent starts on server boot

Create `/etc/systemd/system/pm-agent.service`:

```ini
[Unit]
Description=PM Agent Orchestrator
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/your-user/pm-agent
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=your-user
Group=docker

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable pm-agent
sudo systemctl start pm-agent

# Check status
sudo systemctl status pm-agent

# View logs
docker-compose logs -f
```

**Deliverable:**
- Systemd service installed
- Agent starts on boot
- Logs accessible via Docker Compose

## Phase 1: Analysis & Discovery

### Task 1.1: Analyze Current Claude Code Setup
**Objective**: Document existing MCP configuration

**Questions to answer:**
1. **MCP Server Configuration**
   - Where is `~/.config/claude-code/` located?
   - Which MCP servers are configured? (Atlassian, Slack, etc.)
   - How are they authenticated? (OAuth tokens, API keys?)
   - Are there any custom MCP servers?

2. **Current MCP Capabilities**
   - What MCP operations work well?
   - Which operations are unreliable or slow?
   - Any known MCP connection issues?

3. **Claude Code Skills**
   - What skills exist in `/mnt/skills/`?
   - Which skills are most used?
   - Any skills specific to your workflow?

**Action Items:**
```bash
# Export MCP configuration
cp -r ~/.config/claude-code ./docs/mcp-backup/

# Document MCP servers
cat ~/.config/claude-code/mcp-servers.json > ./docs/mcp-servers.md

# Test MCP connections
# (manually verify each MCP server works)
```

**Deliverable:**
- `docs/current-mcp-setup.md` documenting MCP configuration
- `docs/mcp-backup/` with config backups
- List of MCP operations to use vs. avoid

### Task 1.2: Define PM Agent Directives
**Objective**: Create agent constitution and objectives

Create `config/pm-directives.yaml`:

```yaml
agent:
  role: "Sprint Project Manager"
  personality: "Proactive but respectful, detail-oriented, clear communicator"

objectives:
  primary:
    - "All sprint tickets must be completed by sprint end date"
    - "No ticket should remain blocked for more than 1 business day"
    - "All PRs must receive review within 8 business hours"
    - "Team members should always have clarity on priorities and status"
  
  secondary:
    - "Proactively identify and escalate risks before they become critical"
    - "Keep stakeholders informed with daily progress updates"
    - "Facilitate unblocking and cross-team coordination"
    - "Learn patterns: who responds quickly, what typically causes delays"

constraints:
  communication:
    - "Maximum 1 reminder per person per day (avoid being annoying)"
    - "Use appropriate channels (#engineering for tech, #leadership for escalations)"
    - "Be respectful of working hours (9am-6pm local time)"
    - "Always provide context: link to ticket, explain urgency"
  
  escalation:
    - "Escalate blockers >2 days to #leadership with summary"
    - "Flag at-risk sprint goals 3 days before sprint end"
    - "Notify tech leads if >3 PRs pending review from same person"
    - "Don't escalate prematurely - try to resolve first"
  
  autonomy_levels:
    can_do_automatically:
      - "Add comments to Jira tickets with status checks"
      - "Post daily sprint summaries to #engineering"
      - "Send DMs asking for updates (max 1/day per person)"
      - "Update ticket status based on PR merges"
    
    needs_confirmation:
      - "Reassign tickets to different people"
      - "Change sprint scope (add/remove tickets)"
      - "Escalate to leadership"
      - "Post to public channels besides #engineering"
    
    never_do:
      - "Delete or close tickets without human approval"
      - "Change ticket priorities without PM approval"
      - "Make code changes or merge PRs"

decision_making:
  when_uncertain:
    - "Default to asking for clarification rather than guessing"
    - "Provide 2-3 options with pros/cons when appropriate"
    - "Always explain reasoning behind suggestions"
  
  learning:
    - "Remember what worked well (in state management)"
    - "Adapt communication style to team member preferences"
    - "Track velocity patterns to improve predictions"

urgency_levels:
  critical:
    description: "Production down, sprint at severe risk, major blocker"
    check_frequency_minutes: 15
    actions:
      - "Immediate Slack notification to relevant people"
      - "Check every 15 minutes until resolved"
      - "Escalate if no response in 30 minutes"
    examples:
      - "P0 bug blocking production"
      - "Sprint ends tomorrow with <40% completion"
      - "Blocker affecting 3+ tickets with no progress for 3+ days"
  
  high:
    description: "At-risk sprint goals, long-pending blockers"
    check_frequency_minutes: 60
    actions:
      - "Proactive outreach to unblock"
      - "Daily status updates"
      - "Prepare escalation if no improvement"
    examples:
      - "Sprint at 50-60% completion with 3 days left"
      - "Blocker with no progress for 2 days"
      - "Critical PR pending review for 24+ hours"
  
  medium:
    description: "Normal sprint progress, some attention needed"
    check_frequency_minutes: 180
    actions:
      - "Monitor for changes"
      - "Gentle reminders for stale items"
      - "Track patterns"
    examples:
      - "Sprint on track but some tickets moving slowly"
      - "PR pending review for 8-16 hours"
      - "Ticket updated but still in same status"
  
  low:
    description: "Everything running smoothly"
    check_frequency_minutes: 360
    actions:
      - "Passive monitoring"
      - "Daily summary only"
      - "Look for improvement opportunities"
    examples:
      - "Sprint ahead of schedule"
      - "All tickets active with recent updates"
      - "No blockers, good velocity"

team_context:
  # Agent learns and updates this over time
  members:
    - name: "Sarah"
      typical_response_time: "1-2 hours"
      works_best_with: "direct Slack DMs"
      timezone: "PT"
      notes: "Very responsive, prefers morning check-ins"
    
    - name: "Mike"
      typical_response_time: "4-8 hours"
      works_best_with: "Jira comments"
      timezone: "ET"
      notes: "Checks Jira regularly, doesn't like Slack pings"
```

**Deliverable:**
- `config/pm-directives.yaml` complete
- `docs/directive-explanation.md` explaining each section
- Example scenarios showing how directives guide decisions

## Phase 2: Webhook Infrastructure

### Task 2.1: Webhook Server (FastAPI)
**Objective**: HTTP server to receive webhooks

Create `src/web/app.py`:

```python
"""
FastAPI application for webhook endpoints
Runs on home server, exposed via static IP + SSL
"""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header
from fastapi.responses import JSONResponse
import hmac
import hashlib
from datetime import datetime
import os

from src.webhook.handlers import (
    JiraWebhookHandler,
    BitbucketWebhookHandler,
    SlackEventHandler
)

app = FastAPI(
    title="PM Agent Webhook Server",
    description="Receives webhooks from Jira, Bitbucket, Slack"
)

# Initialize handlers
jira_handler = JiraWebhookHandler()
bitbucket_handler = BitbucketWebhookHandler()
slack_handler = SlackEventHandler()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "redis": "healthy",  # TODO: actual check
            "postgres": "healthy",  # TODO: actual check
            "mcp": "healthy"  # TODO: actual check
        }
    }

@app.post("/webhooks/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_atlassian_webhook_identifier: str = Header(None)
):
    """
    Jira webhook endpoint
    Docs: https://developer.atlassian.com/server/jira/platform/webhooks/
    """
    
    payload = await request.json()
    
    # Log for debugging
    print(f"Received Jira webhook: {payload.get('webhookEvent')}")
    
    # Process in background to return 200 quickly
    background_tasks.add_task(
        jira_handler.process_webhook,
        payload
    )
    
    return {"status": "accepted", "timestamp": datetime.utcnow().isoformat()}

@app.post("/webhooks/bitbucket")
async def bitbucket_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_event_key: str = Header(None)
):
    """
    Bitbucket webhook endpoint
    Docs: https://support.atlassian.com/bitbucket-cloud/docs/event-payloads/
    """
    
    payload = await request.json()
    
    print(f"Received Bitbucket webhook: {x_event_key}")
    
    background_tasks.add_task(
        bitbucket_handler.process_webhook,
        x_event_key,
        payload
    )
    
    return {"status": "accepted"}

@app.post("/webhooks/slack")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Slack Events API endpoint
    Docs: https://api.slack.com/apis/connections/events-api
    """
    
    payload = await request.json()
    
    # Handle Slack's URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}
    
    # Handle retry headers (Slack retries failed webhooks)
    if request.headers.get("X-Slack-Retry-Num"):
        retry_count = int(request.headers.get("X-Slack-Retry-Num"))
        if retry_count > 3:
            # Too many retries, might be stuck
            print(f"Slack webhook retry #{retry_count}, skipping")
            return {"status": "skipped"}
    
    background_tasks.add_task(
        slack_handler.process_event,
        payload
    )
    
    return {"status": "accepted"}

@app.get("/api/status")
async def get_status():
    """Get current agent status"""
    from src.database.models import Sprint, AgentCycle
    from src.database.connection import get_session
    
    with get_session() as session:
        active_sprints = session.query(Sprint).filter_by(status="active").all()
        recent_cycles = session.query(AgentCycle).order_by(
            AgentCycle.created_at.desc()
        ).limit(10).all()
    
    return {
        "active_sprints": len(active_sprints),
        "recent_cycles": len(recent_cycles),
        "last_cycle": recent_cycles[0].created_at.isoformat() if recent_cycles else None
    }

@app.post("/api/trigger-cycle")
async def trigger_cycle(sprint_id: str, background_tasks: BackgroundTasks):
    """Manually trigger an agent cycle"""
    from src.orchestration.event_processor import EventProcessor
    
    processor = EventProcessor()
    background_tasks.add_task(
        processor.trigger_cycle,
        sprint_id,
        trigger_type="manual"
    )
    
    return {"status": "triggered", "sprint_id": sprint_id}

if __name__ == "__main__":
    import uvicorn
    
    # For local development without SSL
    if os.getenv("ENVIRONMENT") == "development":
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Production with SSL
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8443,
            ssl_keyfile="/etc/letsencrypt/live/agent.yourdomain.com/privkey.pem",
            ssl_certfile="/etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem"
        )
```

**Deliverable:**
- `src/web/app.py` working
- Webhook endpoints accepting POST requests
- Health check endpoint working
- Logging configured

### Task 2.2: Webhook Handlers with MCP
**Objective**: Process webhooks and determine if agent should act

Create `src/webhook/handlers.py`:

```python
"""
Webhook handlers that process events and decide whether to trigger agent
"""

from typing import Dict, Any
import redis
import json
from datetime import datetime
import os

from src.database.models import WebhookEvent
from src.database.connection import get_session

class BaseWebhookHandler:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL"))
    
    def save_webhook_event(self, source: str, event_type: str, payload: dict) -> str:
        """Save webhook to database for audit trail"""
        with get_session() as session:
            event = WebhookEvent(
                source=source,
                event_type=event_type,
                payload=payload
            )
            session.add(event)
            session.commit()
            return str(event.id)
    
    def should_trigger_cycle(self, event_type: str, payload: dict) -> bool:
        """Override in subclasses"""
        return False
    
    def enqueue_cycle(self, sprint_id: str, event_data: dict):
        """Add cycle trigger to Redis queue"""
        cycle_event = {
            "sprint_id": sprint_id,
            "trigger_type": "webhook",
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.redis_client.lpush(
            "agent:cycle_queue",
            json.dumps(cycle_event)
        )
        
        print(f"✓ Enqueued cycle for sprint {sprint_id}")

class JiraWebhookHandler(BaseWebhookHandler):
    def process_webhook(self, payload: dict):
        """Process Jira webhook"""
        
        event_type = payload.get("webhookEvent")
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        print(f"Processing Jira event: {event_type} for {issue_key}")
        
        # Save for audit
        event_id = self.save_webhook_event("jira", event_type, payload)
        
        # Check if this should trigger agent
        if self.should_trigger_cycle(event_type, payload):
            # Extract sprint from issue
            sprint_id = self.extract_sprint_from_issue(payload)
            
            if sprint_id:
                self.enqueue_cycle(sprint_id, {
                    "source": "jira",
                    "event_type": event_type,
                    "issue_key": issue_key,
                    "event_id": event_id
                })
    
    def should_trigger_cycle(self, event_type: str, payload: dict) -> bool:
        """
        Trigger on significant events:
        - Status changes (especially to/from blocked states)
        - Comments (might indicate blocker resolution)
        - Assignee changes
        - Priority changes
        
        Don't trigger on:
        - Minor field updates (description edits)
        - Automated bot updates
        - Spam updates
        """
        
        # Always trigger for new issues and comments
        if event_type in ["jira:issue_created", "comment_created"]:
            return True
        
        # For updates, check what changed
        if event_type == "jira:issue_updated":
            changelog = payload.get("changelog", {}).get("items", [])
            
            # Significant fields that should trigger agent
            significant_fields = [
                "status",
                "assignee",
                "priority",
                "resolution",
                "Sprint",
                "Flagged"  # Blocked flag
            ]
            
            for item in changelog:
                if item.get("field") in significant_fields:
                    return True
            
            # Check if moved to/from blocked state
            for item in changelog:
                if item.get("field") == "status":
                    from_status = item.get("fromString", "").lower()
                    to_status = item.get("toString", "").lower()
                    
                    if "block" in to_status or "block" in from_status:
                        return True
            
            return False
        
        return False
    
    def extract_sprint_from_issue(self, payload: dict) -> str:
        """Extract sprint ID from Jira issue"""
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        
        # Sprint is usually in a custom field (varies by Jira config)
        # Common field names: customfield_10020, customfield_10016
        sprint_field = fields.get("customfield_10020") or fields.get("customfield_10016")
        
        if sprint_field and isinstance(sprint_field, list) and len(sprint_field) > 0:
            # Sprint data format varies, might need parsing
            # Often contains sprint ID in string like "com.atlassian.greenhopper.service.sprint.Sprint@14b4[id=123,...]"
            sprint_data = sprint_field[0]
            
            if isinstance(sprint_data, dict):
                return str(sprint_data.get("id"))
            elif isinstance(sprint_data, str):
                # Parse sprint ID from string
                import re
                match = re.search(r'id=(\d+)', sprint_data)
                if match:
                    return match.group(1)
        
        return None

class BitbucketWebhookHandler(BaseWebhookHandler):
    def process_webhook(self, event_type: str, payload: dict):
        """Process Bitbucket webhook"""
        
        pr = payload.get("pullrequest", {})
        pr_id = pr.get("id")
        
        print(f"Processing Bitbucket event: {event_type} for PR #{pr_id}")
        
        self.save_webhook_event("bitbucket", event_type, payload)
        
        if self.should_trigger_cycle(event_type, payload):
            # Extract Jira keys from PR title/branch
            jira_keys = self.extract_jira_keys(pr)
            
            if jira_keys:
                # Trigger cycle for each related sprint
                for jira_key in jira_keys:
                    sprint_id = self.get_sprint_from_ticket(jira_key)
                    if sprint_id:
                        self.enqueue_cycle(sprint_id, {
                            "source": "bitbucket",
                            "event_type": event_type,
                            "pr_id": pr_id,
                            "jira_keys": jira_keys
                        })
    
    def should_trigger_cycle(self, event_type: str, payload: dict) -> bool:
        """
        Trigger on PR events that affect ticket status:
        - Created (might unblock ticket)
        - Approved (progress indicator)
        - Merged (completes ticket)
        - Declined (might re-block)
        """
        
        trigger_events = [
            "pullrequest:created",
            "pullrequest:approved",
            "pullrequest:fulfilled",  # merged
            "pullrequest:rejected"
        ]
        
        return event_type in trigger_events
    
    def extract_jira_keys(self, pr: dict) -> list:
        """Extract Jira ticket keys from PR"""
        import re
        
        # Look in title, description, branch name
        title = pr.get("title", "")
        description = pr.get("description", "")
        branch = pr.get("source", {}).get("branch", {}).get("name", "")
        
        text = f"{title} {description} {branch}"
        
        # Find patterns like PROJ-123
        pattern = r'[A-Z][A-Z0-9]+-\d+'
        matches = re.findall(pattern, text)
        
        return list(set(matches))  # Deduplicate
    
    def get_sprint_from_ticket(self, jira_key: str) -> str:
        """
        Get sprint ID from Jira ticket
        Uses MCP for semantic search (preferred) with API fallback
        """
        from src.clients.mcp_client import MCPClient
        from src.clients.jira_client import JiraAPIClient
        
        try:
            # Try MCP first
            mcp = MCPClient()
            issue = mcp.jira_get_issue(jira_key)
            return issue.get("sprint_id")
        except Exception as e:
            print(f"MCP failed, using API: {e}")
            # Fallback to direct API
            api = JiraAPIClient()
            issue = api.get_issue(jira_key)
            return issue.get("sprint_id")

class SlackEventHandler(BaseWebhookHandler):
    def process_event(self, payload: dict):
        """Process Slack event"""
        
        event = payload.get("event", {})
        event_type = event.get("type")
        
        self.save_webhook_event("slack", event_type, payload)
        
        # Only process app mentions and DMs
        if event_type in ["app_mention", "message"]:
            # Extract intent from message
            text = event.get("text", "")
            user = event.get("user")
            channel = event.get("channel")
            
            # Check if message contains sprint reference
            sprint_id = self.extract_sprint_reference(text)
            
            if sprint_id:
                self.enqueue_cycle(sprint_id, {
                    "source": "slack",
                    "event_type": "user_request",
                    "user": user,
                    "channel": channel,
                    "message": text
                })
    
    def extract_sprint_reference(self, text: str) -> str:
        """
        Extract sprint reference from Slack message
        Examples:
        - "status on sprint 24"
        - "what's happening with SPRINT-24"
        - "@agent check the current sprint"
        """
        import re
        
        # Look for explicit sprint ID
        match = re.search(r'sprint[- ]?(\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Look for "current sprint" or "active sprint"
        if re.search(r'current|active|this', text, re.IGNORECASE) and 'sprint' in text.lower():
            # Need to determine current sprint
            # This could use MCP to find active sprint
            return "current"  # Placeholder, will be resolved later
        
        return None
```

**Deliverable:**
- `src/webhook/handlers.py` complete
- Each webhook type processed correctly
- Events saved to database
- Cycles enqueued appropriately
- Tests with sample webhook payloads

### Task 2.3: Register Webhooks
**Objective**: Register webhooks with Atlassian services

Create `scripts/register_webhooks.py`:

```python
"""
Register webhooks with Atlassian services
Points them to your static IP/domain
"""

import requests
import os
import click
import json

class WebhookRegistrar:
    def __init__(self):
        self.domain = os.getenv("ATLASSIAN_DOMAIN")
        self.email = os.getenv("ATLASSIAN_EMAIL")
        self.token = os.getenv("ATLASSIAN_API_TOKEN")
        self.auth = (self.email, self.token)
    
    def register_jira_webhook(self, webhook_url: str):
        """Register Jira webhook"""
        
        url = f"https://{self.domain}/rest/api/3/webhook"
        
        payload = {
            "name": "PM Agent Webhook",
            "url": f"{webhook_url}/webhooks/jira",
            "events": [
                "jira:issue_created",
                "jira:issue_updated",
                "comment_created",
                "worklog_updated"
            ],
            "filters": {
                # Optional: filter to specific projects
                # "issue-related-events-section": "project in (PROJ1, PROJ2)"
            }
        }
        
        response = requests.post(url, json=payload, auth=self.auth)
        
        if response.status_code == 201:
            print(f"✓ Jira webhook registered successfully")
            print(f"  Webhook ID: {response.json()['id']}")
        else:
            print(f"✗ Failed to register Jira webhook: {response.text}")
        
        return response.json()
    
    def register_bitbucket_webhook(self, webhook_url: str, workspace: str, repo: str = None):
        """Register Bitbucket webhook"""
        
        # Workspace-level webhook (all repos)
        if not repo:
            url = f"https://api.bitbucket.org/2.0/workspaces/{workspace}/hooks"
        else:
            url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/hooks"
        
        payload = {
            "description": "PM Agent Webhook",
            "url": f"{webhook_url}/webhooks/bitbucket",
            "active": True,
            "events": [
                "pullrequest:created",
                "pullrequest:updated",
                "pullrequest:approved",
                "pullrequest:fulfilled",
                "pullrequest:rejected"
            ]
        }
        
        response = requests.post(url, json=payload, auth=(workspace, self.token))
        
        if response.status_code == 201:
            print(f"✓ Bitbucket webhook registered")
            print(f"  Webhook UUID: {response.json()['uuid']}")
        else:
            print(f"✗ Failed to register Bitbucket webhook: {response.text}")
        
        return response.json()
    
    def list_webhooks(self, service: str):
        """List existing webhooks"""
        
        if service == "jira":
            url = f"https://{self.domain}/rest/api/3/webhook"
            response = requests.get(url, auth=self.auth)
        
        elif service == "bitbucket":
            workspace = os.getenv("BITBUCKET_WORKSPACE")
            url = f"https://api.bitbucket.org/2.0/workspaces/{workspace}/hooks"
            response = requests.get(url, auth=(workspace, self.token))
        
        if response.status_code == 200:
            webhooks = response.json()
            print(json.dumps(webhooks, indent=2))
        else:
            print(f"✗ Failed to list webhooks: {response.text}")

@click.command()
@click.option('--service', type=click.Choice(['jira', 'bitbucket', 'all']), required=True)
@click.option('--url', help='Your webhook base URL (e.g., https://your-ip or https://agent.yourdomain.com)')
@click.option('--list', 'list_only', is_flag=True, help='List existing webhooks')
@click.option('--workspace', help='Bitbucket workspace (if registering Bitbucket)')
def main(service, url, list_only, workspace):
    """Register webhooks with Atlassian services"""
    
    registrar = WebhookRegistrar()
    
    if list_only:
        registrar.list_webhooks(service)
        return
    
    if not url:
        print("Error: --url is required when registering webhooks")
        return
    
    # Ensure URL has https://
    if not url.startswith('http'):
        url = f"https://{url}"
    
    if service == "jira" or service == "all":
        print(f"\nRegistering Jira webhook pointing to {url}...")
        registrar.register_jira_webhook(url)
    
    if service == "bitbucket" or service == "all":
        if not workspace:
            workspace = os.getenv("BITBUCKET_WORKSPACE")
            if not workspace:
                print("Error: --workspace required for Bitbucket")
                return
        
        print(f"\nRegistering Bitbucket webhook pointing to {url}...")
        registrar.register_bitbucket_webhook(url, workspace)
    
    print("\n✓ Webhook registration complete!")
    print(f"\nTest your webhooks:")
    print(f"  curl -X POST {url}/webhooks/jira -H 'Content-Type: application/json' -d '{{}}'")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Load environment
source .env

# Register webhooks (after server is running)
python scripts/register_webhooks.py --service all --url https://your-static-ip

# Or with domain
python scripts/register_webhooks.py --service all --url https://agent.yourdomain.com

# List existing webhooks
python scripts/register_webhooks.py --service jira --list
```

**Deliverable:**
- `scripts/register_webhooks.py` working
- Webhooks registered with Jira/Bitbucket
- Webhooks successfully delivering to your server
- `docs/webhook-testing.md` with test procedures

## Phase 3: MCP + API Hybrid Client Layer

### Task 3.1: MCP Client Wrapper
**Objective**: Wrapper around MCP for consistent usage in orchestrator

Create `src/clients/mcp_client.py`:

```python
"""
MCP Client wrapper for orchestrator
Uses MCP servers configured in Claude Code
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional

class MCPError(Exception):
    """Raised when MCP operation fails"""
    pass

class MCPClient:
    """
    Wrapper around MCP functionality
    Executes MCP operations via Claude Code CLI or direct MCP server calls
    """
    
    def __init__(self):
        # Path to Claude Code config with MCP servers
        self.mcp_config_path = os.path.expanduser("~/.config/claude-code")
    
    # ===== JIRA OPERATIONS =====
    
    def jira_search_issues(self, query: str, limit: int = 50) -> list:
        """
        Search Jira issues using natural language
        This is where MCP shines - semantic search
        
        Examples:
        - "tickets related to authentication"
        - "blocked issues in current sprint"
        - "tickets Sarah worked on this week"
        """
        try:
            # Use MCP Atlassian server
            result = self._call_mcp_server(
                server="atlassian",
                tool="search_issues",
                params={
                    "query": query,
                    "max_results": limit
                }
            )
            return result.get("issues", [])
        
        except Exception as e:
            raise MCPError(f"MCP Jira search failed: {e}")
    
    def jira_get_issue(self, issue_key: str) -> Dict:
        """Get single issue - MCP provides nice structured data"""
        try:
            result = self._call_mcp_server(
                server="atlassian",
                tool="get_issue",
                params={"issue_key": issue_key}
            )
            return result
        except Exception as e:
            raise MCPError(f"MCP get issue failed: {e}")
    
    def jira_find_sprint(self, query: str) -> Optional[str]:
        """
        Find sprint using natural language
        Examples:
        - "current sprint"
        - "new sprint"
        - "sprint 24"
        """
        try:
            result = self._call_mcp_server(
                server="atlassian",
                tool="search_sprints",
                params={"query": query}
            )
            
            sprints = result.get("sprints", [])
            if sprints:
                return sprints[0]["id"]
            
            return None
        
        except Exception as e:
            raise MCPError(f"MCP sprint search failed: {e}")
    
    # ===== SLACK OPERATIONS =====
    
    def slack_search_messages(self, query: str, channel: str = None) -> list:
        """
        Search Slack messages - MCP good for semantic search
        Example: "discussions about the API bug last week"
        """
        try:
            result = self._call_mcp_server(
                server="slack",
                tool="search_messages",
                params={
                    "query": query,
                    "channel": channel
                }
            )
            return result.get("messages", [])
        
        except Exception as e:
            raise MCPError(f"MCP Slack search failed: {e}")
    
    def slack_get_thread(self, channel: str, thread_ts: str) -> list:
        """Get full Slack thread for context"""
        try:
            result = self._call_mcp_server(
                server="slack",
                tool="get_thread",
                params={
                    "channel": channel,
                    "thread_ts": thread_ts
                }
            )
            return result.get("messages", [])
        
        except Exception as e:
            raise MCPError(f"MCP Slack thread fetch failed: {e}")
    
    # ===== HELPER METHODS =====
    
    def _call_mcp_server(self, server: str, tool: str, params: dict) -> dict:
        """
        Call MCP server tool
        
        This could be implemented as:
        1. Direct MCP protocol calls
        2. Via Claude Code CLI
        3. Via custom MCP client library
        
        For now, using subprocess to call Claude Code
        """
        
        # Construct Claude Code command
        # This assumes Claude Code exposes MCP functionality
        
        command = [
            "claude-code",
            "mcp",
            "--server", server,
            "--tool", tool,
            "--params", json.dumps(params)
        ]
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            return json.loads(result.stdout)
        
        except subprocess.TimeoutExpired:
            raise MCPError(f"MCP call timed out: {server}.{tool}")
        
        except subprocess.CalledProcessError as e:
            raise MCPError(f"MCP call failed: {e.stderr}")
        
        except json.JSONDecodeError as e:
            raise MCPError(f"MCP returned invalid JSON: {e}")
    
    def test_connection(self) -> Dict[str, str]:
        """Test MCP connections"""
        results = {}
        
        # Test Jira MCP
        try:
            self.jira_search_issues("test", limit=1)
            results["jira"] = "connected"
        except Exception as e:
            results["jira"] = f"failed: {e}"
        
        # Test Slack MCP
        try:
            self.slack_search_messages("test", limit=1)
            results["slack"] = "connected"
        except Exception as e:
            results["slack"] = f"failed: {e}"
        
        return results
```

**Deliverable:**
- `src/clients/mcp_client.py` working
- Can call MCP servers successfully
- Error handling for MCP failures
- Connection test utility

### Task 3.2: Direct API Clients (Fallback)
**Objective**: Direct API clients for when MCP fails or for specific operations

Create `src/clients/jira_api_client.py`:

```python
"""
Direct Jira API client (fallback when MCP fails)
Also used for operations that don't need semantic search
"""

import requests
from typing import Dict, List
import os

class JiraAPIClient:
    def __init__(self):
        self.domain = os.getenv("ATLASSIAN_DOMAIN")
        self.email = os.getenv("ATLASSIAN_EMAIL")
        self.token = os.getenv("ATLASSIAN_API_TOKEN")
        self.base_url = f"https://{self.domain}"
        self.auth = (self.email, self.token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def get_issue(self, issue_key: str) -> Dict:
        """Get issue by exact key"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        
        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers,
            params={"expand": "changelog,renderedFields"}
        )
        response.raise_for_status()
        
        return self._parse_issue(response.json())
    
    def add_comment(self, issue_key: str, comment: str) -> Dict:
        """Add comment to issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        
        # Jira Cloud uses ADF (Atlassian Document Format)
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        
        return response.json()
    
    def move_to_sprint(self, issue_key: str, sprint_id: str) -> Dict:
        """Move issue to sprint"""
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        
        payload = {
            "issues": [issue_key]
        }
        
        response = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        
        return {"status": "success", "issue": issue_key, "sprint": sprint_id}
    
    def get_sprint_tickets(self, sprint_id: str) -> List[Dict]:
        """Get all tickets in sprint"""
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        
        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers,
            params={"maxResults": 100}
        )
        response.raise_for_status()
        
        issues = response.json()["issues"]
        return [self._parse_issue(issue) for issue in issues]
    
    def _parse_issue(self, raw: Dict) -> Dict:
        """Parse Jira API response into cleaner format"""
        fields = raw["fields"]
        
        return {
            "key": raw["key"],
            "summary": fields["summary"],
            "status": fields["status"]["name"],
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            "priority": fields.get("priority", {}).get("name"),
            "created": fields["created"],
            "updated": fields["updated"],
            "description": fields.get("description"),
            "labels": fields.get("labels", []),
            "sprint_id": self._extract_sprint_id(fields)
        }
    
    def _extract_sprint_id(self, fields: Dict) -> str:
        """Extract sprint ID from custom field"""
        # This varies by Jira configuration
        sprint_field = fields.get("customfield_10020") or fields.get("customfield_10016")
        
        if sprint_field and isinstance(sprint_field, list) and len(sprint_field) > 0:
            sprint_data = sprint_field[0]
            if isinstance(sprint_data, dict):
                return str(sprint_data.get("id"))
        
        return None
```

Create similar clients:
- `src/clients/slack_api_client.py`
- `src/clients/bitbucket_api_client.py`

**Deliverable:**
- API clients for Jira, Slack, Bitbucket
- All clients tested and working
- Error handling and retries
- `docs/api-clients.md` documenting operations

### Task 3.3: Unified Client Interface
**Objective**: Single interface that tries MCP first, falls back to API

Create `src/clients/unified_client.py`:

```python
"""
Unified client that uses MCP when possible, API as fallback
"""

from src.clients.mcp_client import MCPClient, MCPError
from src.clients.jira_api_client import JiraAPIClient
from src.clients.slack_api_client import SlackAPIClient
import logging

logger = logging.getLogger(__name__)

class UnifiedJiraClient:
    """
    Unified Jira client:
    - Uses MCP for discovery and semantic operations
    - Uses API for specific operations and as fallback
    """
    
    def __init__(self):
        self.mcp = MCPClient()
        self.api = JiraAPIClient()
    
    def search_issues(self, query: str, limit: int = 50) -> list:
        """
        Search issues - prefer MCP for semantic understanding
        """
        try:
            logger.info(f"Searching issues via MCP: {query}")
            return self.mcp.jira_search_issues(query, limit)
        
        except MCPError as e:
            logger.warning(f"MCP search failed: {e}, falling back to JQL")
            # Fallback: convert natural language to JQL (best effort)
            jql = self._natural_to_jql(query)
            return self.api.search_issues_jql(jql, limit)
    
    def get_issue(self, issue_key: str) -> dict:
        """
        Get specific issue - try MCP first, API as fallback
        """
        try:
            return self.mcp.jira_get_issue(issue_key)
        except MCPError:
            logger.info(f"MCP failed for {issue_key}, using API")
            return self.api.get_issue(issue_key)
    
    def add_comment(self, issue_key: str, comment: str) -> dict:
        """
        Add comment - use API directly (simple operation)
        """
        logger.info(f"Adding comment to {issue_key} via API")
        return self.api.add_comment(issue_key, comment)
    
    def find_sprint(self, query: str) -> str:
        """
        Find sprint - MCP is better at understanding "current sprint"
        """
        try:
            return self.mcp.jira_find_sprint(query)
        except MCPError:
            # Fallback: get active sprints via API
            sprints = self.api.get_active_sprints()
            if sprints:
                return sprints[0]["id"]  # Return most recent
            return None
    
    def move_to_sprint(self, issue_key: str, sprint_id: str) -> dict:
        """
        Move to sprint - use API directly (specific operation)
        """
        return self.api.move_to_sprint(issue_key, sprint_id)
    
    def _natural_to_jql(self, query: str) -> str:
        """
        Convert natural language to JQL (best effort)
        This is crude - MCP is much better
        """
        # Simple keyword-based conversion
        jql = "project is not EMPTY"
        
        if "blocked" in query.lower():
            jql += " AND status = Blocked"
        
        if "current sprint" in query.lower():
            jql += " AND sprint in openSprints()"
        
        # etc... this is why MCP is better!
        
        return jql

class UnifiedSlackClient:
    """Similar pattern for Slack"""
    
    def __init__(self):
        self.mcp = MCPClient()
        self.api = SlackAPIClient()
    
    def search_messages(self, query: str) -> list:
        """Search messages - MCP preferred"""
        try:
            return self.mcp.slack_search_messages(query)
        except MCPError:
            return self.api.search_messages(query)
    
    def post_message(self, channel: str, message: str) -> dict:
        """Post message - API directly"""
        return self.api.post_message(channel, message)
```

**Deliverable:**
- `src/clients/unified_client.py` complete
- Graceful fallback from MCP to API
- Logging of which client was used
- Tests showing fallback behavior

## Phase 4: Core Orchestration

(Continue with state management, action planner, executor as in v1 plan, but using UnifiedClient)

### Task 4.1: State Manager (PostgreSQL)
Create `src/orchestration/state_manager.py` (same as v2 plan)

### Task 4.2: Context Gatherer  
Create `src/orchestration/context_gatherer.py` using Unified Clients

### Task 4.3: Action Planner
Create `src/orchestration/action_planner.py` with Claude API reasoning

### Task 4.4: Action Executor
Create `src/orchestration/action_executor.py` that routes to MCP or API

### Task 4.5: Main Orchestrator
Create `src/orchestration/orchestrator.py` tying everything together

### Task 4.6: Event Processor Worker
Create `src/orchestration/event_processor.py` (same as v2 plan)

## Phase 5: Claude Code Integration

### Task 5.1: Claude Code Task Runner
**Objective**: Delegate complex tasks to Claude Code (which uses MCP extensively)

Create `src/orchestration/claude_code_runner.py`:

```python
"""
Claude Code Task Runner - for complex tasks requiring deep analysis
"""

import subprocess
import json
import tempfile
import os

class ClaudeCodeTaskRunner:
    """
    Runs Claude Code for complex tasks
    Claude Code uses MCP for deep exploration
    """
    
    def __init__(self):
        self.claude_code_path = "claude-code"  # Assumes in PATH
    
    def execute_task(
        self,
        task_description: str,
        context: dict = None,
        timeout_minutes: int = 30
    ) -> dict:
        """
        Execute complex task via Claude Code
        
        Claude Code will use MCP extensively for exploration
        """
        
        # Create task file
        task_data = {
            "task": task_description,
            "context": context or {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(task_data, f)
            task_file = f.name
        
        try:
            # Execute Claude Code
            command = [
                self.claude_code_path,
                "execute",
                "--task-file", task_file,
                "--output-json"
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_minutes * 60
            )
            
            if result.returncode == 0:
                return {
                    "status": "complete",
                    "result": json.loads(result.stdout),
                    "actions_taken": []  # Parse from Claude Code output
                }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": f"Task exceeded {timeout_minutes} minutes"
            }
        
        finally:
            # Cleanup
            os.unlink(task_file)
    
    def should_delegate_to_claude_code(self, action: dict) -> bool:
        """
        Determine if action should be delegated to Claude Code
        
        Delegate when:
        - Multi-step analysis required
        - Document generation needed
        - Deep investigation needed
        - Cross-system synthesis
        """
        
        complex_action_types = [
            "analyze_blocker_root_cause",
            "create_sprint_report",
            "investigate_pattern",
            "synthesize_from_multiple_sources"
        ]
        
        return action.get("type") in complex_action_types
```

**Deliverable:**
- `src/orchestration/claude_code_runner.py`
- Integration with main orchestrator
- Example complex tasks delegated successfully

## Phase 6: CLI & Management Tools

### Task 6.1: CLI Interface
Create `src/cli/pm_agent.py`:

```bash
# Start agent
python -m src.cli.pm_agent start --sprint SPRINT-24

# Check status
python -m src.cli.pm_agent status

# Manual trigger
python -m src.cli.pm_agent trigger --sprint SPRINT-24

# Test connections (MCP + API)
python -m src.cli.pm_agent test-connections
```

### Task 6.2: Admin Dashboard
Create `src/web/dashboard.py` - web UI to monitor agent

Access at `http://localhost:8000`

## Phase 7: Deployment & Operations

### Task 7.1: Start Everything
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl https://your-ip:8443/health
```

### Task 7.2: Monitoring
- Set up log rotation
- Configure alerts (Slack notifications on errors)
- Monitor disk usage
- Track API costs

### Task 7.3: Backup Strategy
```bash
# Daily database backups
crontab -e
0 2 * * * docker exec pm-agent_postgres_1 pg_dump -U pm_agent pm_agent > /backups/pm-agent-$(date +\%Y\%m\%d).sql
```

## Success Metrics

**Technical:**
- Webhook latency: <2 seconds
- Cycle completion: <20 seconds
- MCP success rate: >80% (with API fallback working)
- Uptime: >99% (your home server)

**Cost:**
- Claude API: ~$5-15/day
- Electricity: negligible
- Total: ~$150-450/month in API costs

**Operational:**
- MCP auth refresh needed: <1x per month
- Manual intervention: <1x per week
- False positives: <10%

## Key Advantages

1. **Best of Both Worlds**: MCP for discovery, API for reliability
2. **Runs Locally**: Full control, no Heroku costs
3. **Webhook-Driven**: Real-time response
4. **Claude Code Integration**: Seamless complex task delegation
5. **Static IP**: Professional webhook delivery
6. **Persistent**: Survives restarts via Docker + systemd

## Maintenance Tasks

**Daily:** Check logs for errors
**Weekly:** Review agent decisions, tune directives
**Monthly:** Rotate logs, check disk space
**Quarterly:** Update dependencies, review API costs

---

This plan gives you a production-ready PM agent running on your home server with the intelligence of MCP and the reliability of direct APIs.

Ready to start implementation?
