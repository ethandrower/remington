# PM Agent - Deployment Checklist

## Current Status: 🟡 Ready for Deployment (Needs API Keys)

**Build Complete**: 11 of 14 steps ✅
**Integration Tested**: Full webhook → orchestrator → database cycle works
**Blocked By**: Missing Anthropic API key (for Claude reasoning)

---

## Pre-Deployment Checklist

### 1. Environment Configuration

- [ ] **Get Anthropic API Key**
  - Go to: https://console.anthropic.com/
  - Create API key
  - Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

- [ ] **Verify Atlassian Credentials** (in `.env`)
  - ✅ `ATLASSIAN_SERVICE_ACCOUNT_EMAIL` - Already set
  - ✅ `ATLASSIAN_SERVICE_ACCOUNT_TOKEN` - Already set (may be expired)
  - If Jira API fails with 401: Regenerate token at https://id.atlassian.com/manage-profile/security/api-tokens

- [ ] **Verify Slack Credentials** (optional, in `.env`)
  - ✅ `SLACK_BOT_TOKEN` - Already set
  - ✅ `SLACK_CHANNEL_STANDUP` - Already set

### 2. Server Setup

- [ ] **Install Dependencies**
  ```bash
  cd /Users/ethand320/code/citemed/project-manager
  pip install -r requirements.txt
  ```

- [ ] **Initialize Database**
  ```bash
  python -m src.database.models
  # Should see: ✅ Database initialized at ./data/pm_agent.db
  ```

- [ ] **Test Server Startup**
  ```bash
  python -m src.web.app
  # Should see: ✅ Orchestrator initialized
  # Visit: http://localhost:8000/health
  ```

### 3. Network Configuration

- [ ] **Ensure Port 8000 is Open**
  ```bash
  # Check firewall
  sudo ufw allow 8000
  # Or
  sudo firewall-cmd --add-port=8000/tcp --permanent
  sudo firewall-cmd --reload
  ```

- [ ] **Verify Dynamic DNS**
  - Confirm your dynamic DNS domain is resolving correctly
  - Test from external network: `curl http://YOUR_DOMAIN:8000/health`

- [ ] **Configure Router Port Forwarding** (if needed)
  - Forward external port 8000 → internal server IP:8000
  - Or use different external port: 80 → internal 8000

### 4. Production Mode Setup

- [ ] **Create Systemd Service** (recommended for auto-start)
  ```bash
  sudo nano /etc/systemd/system/pm-agent.service
  ```

  Paste:
  ```ini
  [Unit]
  Description=CiteMed PM Agent Webhook Server
  After=network.target

  [Service]
  Type=simple
  User=ethand320
  WorkingDirectory=/Users/ethand320/code/citemed/project-manager
  Environment="PATH=/Users/ethand320/code/citemed/project-manager/.venv/bin"
  ExecStart=/Users/ethand320/code/citemed/project-manager/.venv/bin/python -m src.web.app
  Restart=always
  RestartSec=10

  [Install]
  WantedBy=multi-user.target
  ```

  Enable and start:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable pm-agent
  sudo systemctl start pm-agent
  sudo systemctl status pm-agent
  ```

- [ ] **View Logs**
  ```bash
  sudo journalctl -u pm-agent -f
  ```

### 5. Webhook Registration

- [ ] **Register Jira Webhook**
  - Follow guide: `docs/WEBHOOK_SETUP.md`
  - URL: `http://YOUR_DOMAIN:8000/webhooks/jira`
  - Events: `comment_created`, `issue_updated`, `issue_created`
  - JQL Filter: `project = ECD`

- [ ] **Test Webhook Delivery**
  - Add a comment to any ECD ticket
  - Check server logs: `sudo journalctl -u pm-agent -f`
  - Verify in database:
    ```bash
    python -c "from src.database.models import get_session, WebhookEvent; s = get_session(); print(f'{s.query(WebhookEvent).count()} webhooks received'); s.close()"
    ```

### 6. Enable Agent Responses

- [ ] **Verify Orchestrator Works**
  - Check database for agent cycles:
    ```bash
    python -c "from src.database.models import get_session, AgentCycle; s = get_session(); print(f'{s.query(AgentCycle).count()} cycles completed'); s.close()"
    ```

- [ ] **Enable Real Jira Comments** (when ready)
  - Edit `src/orchestration/simple_orchestrator.py`
  - Uncomment lines 282-288 (the `if self.jira:` block)
  - Restart server: `sudo systemctl restart pm-agent`

---

## Post-Deployment Verification

### Smoke Tests

1. **Health Check**
   ```bash
   curl http://YOUR_DOMAIN:8000/health
   # Expected: {"status": "healthy", ...}
   ```

2. **Webhook Reception**
   - Add test comment in Jira
   - Check logs: `sudo journalctl -u pm-agent -n 50`
   - Should see: "📥 JIRA WEBHOOK RECEIVED"

3. **Orchestrator Processing**
   - Check agent cycles in database
   - Verify `status = "complete"`
   - Check `plan` field for Claude's reasoning

4. **Agent Response** (if enabled)
   - Agent should post comment back to Jira ticket
   - Comment should be professional and relevant

### Monitoring

- **System Health**:
  ```bash
  # Check if service is running
  sudo systemctl status pm-agent

  # Check resource usage
  htop
  # Look for python process
  ```

- **Database Stats**:
  ```bash
  python -c "
  from src.database.models import get_stats
  import json
  print(json.dumps(get_stats(), indent=2))
  "
  ```

- **Recent Activity**:
  ```bash
  python -c "
  from src.database.models import get_session, WebhookEvent, AgentCycle
  s = get_session()
  print(f'Last 5 webhooks:')
  for w in s.query(WebhookEvent).order_by(WebhookEvent.id.desc()).limit(5):
      print(f'  {w.source}:{w.event_type} - {w.processed} - {w.received_at}')
  print(f'\nLast 5 cycles:')
  for c in s.query(AgentCycle).order_by(AgentCycle.id.desc()).limit(5):
      print(f'  {c.trigger_type} - {c.status} - {c.created_at}')
  s.close()
  "
  ```

---

## Troubleshooting

### Agent Not Responding

**Symptom**: Webhooks received but no agent response

**Check**:
1. ANTHROPIC_API_KEY is set and valid
2. Check recent cycle in database for errors
3. Check Jira API token hasn't expired

**Fix**:
```bash
# Regenerate Atlassian API token
# Update .env
# Restart: sudo systemctl restart pm-agent
```

### High Memory/CPU Usage

**Symptom**: Server becomes slow or unresponsive

**Check**:
```bash
htop
# Look for python process using excessive resources
```

**Fix**:
- Add rate limiting to webhook endpoints
- Increase server resources
- Add queue system (Redis/Celery) for background processing

### Database Growing Too Large

**Symptom**: `pm_agent.db` file becomes very large

**Solution**: Add cleanup job to archive old data
```bash
# Create backup
cp data/pm_agent.db data/pm_agent_backup_$(date +%Y%m%d).db

# Clean old webhooks (older than 30 days)
python -c "
from src.database.models import get_session, WebhookEvent
from datetime import datetime, timedelta
s = get_session()
cutoff = datetime.utcnow() - timedelta(days=30)
deleted = s.query(WebhookEvent).filter(WebhookEvent.received_at < cutoff).delete()
s.commit()
print(f'Deleted {deleted} old webhooks')
s.close()
"
```

---

## Next Steps After Deployment

### Phase 1: Monitor & Tune (Week 1)
- Monitor agent responses for quality
- Adjust Claude prompts if needed
- Tune SLA thresholds
- Add more webhook events

### Phase 2: Expand Capabilities (Week 2-3)
- Add Bitbucket PR monitoring
- Add Slack slash commands
- Add scheduled tasks (daily standup reports)
- Add developer productivity analysis

### Phase 3: Advanced Features (Month 2)
- Add multi-repository support
- Add sprint health analysis
- Add automated escalations
- Add team performance dashboards

---

## Quick Commands Reference

```bash
# Start server
python -m src.web.app

# Start as service
sudo systemctl start pm-agent

# View logs
sudo journalctl -u pm-agent -f

# Check health
curl http://localhost:8000/health

# Database stats
python -m src.database.models

# Run integration test
python test_integration.py

# Stop service
sudo systemctl stop pm-agent
```

---

**Status**: Ready to deploy once ANTHROPIC_API_KEY is added! 🚀
