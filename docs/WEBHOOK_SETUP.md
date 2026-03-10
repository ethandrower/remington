# Jira Webhook Setup Guide

## Overview
This guide shows how to register webhooks with Jira to enable real-time event processing by the PM Agent.

## Prerequisites

1. **Server Running**: PM Agent webhook server must be running and publicly accessible
2. **Jira Admin Access**: You need Jira admin permissions to create webhooks
3. **Public URL**: Your dynamic DNS domain pointing to the server

## Webhook Endpoint

The PM Agent exposes these webhook endpoints:

- **Jira**: `http://your-domain.com:8000/webhooks/jira`
- **Bitbucket**: `http://your-domain.com:8000/webhooks/bitbucket`
- **Slack**: `http://your-domain.com:8000/webhooks/slack`

## Step 1: Register Jira Webhook

### Via Jira Web UI

1. Go to **Jira Settings** → **System** → **Webhooks**
   - Direct URL: `https://citemed.atlassian.net/plugins/servlet/webhooks`

2. Click **Create a WebHook**

3. Fill in the details:
   - **Name**: `PM Agent - Comment Monitoring`
   - **Status**: Enabled
   - **URL**: `http://YOUR_DOMAIN:8000/webhooks/jira`
   - **Events**:
     - ✅ `comment_created` (primary event for SLA monitoring)
     - ✅ `comment_updated` (optional)
     - ✅ `issue_updated` (optional - for status changes)
     - ✅ `issue_created` (optional)

4. **JQL Filter** (optional - limit to specific projects):
   ```
   project = ECD
   ```

5. Click **Create**

### Via API (Alternative)

```bash
curl -X POST \
  https://citemed.atlassian.net/rest/webhooks/1.0/webhook \
  -u "your-email@example.com:your-api-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PM Agent - Comment Monitoring",
    "url": "http://YOUR_DOMAIN:8000/webhooks/jira",
    "events": [
      "comment_created",
      "comment_updated",
      "issue_updated",
      "issue_created"
    ],
    "filters": {
      "issue-related-events-section": "project = ECD"
    },
    "enabled": true
  }'
```

## Step 2: Test the Webhook

### Option 1: Add a Test Comment in Jira

1. Go to any ECD ticket (e.g., `ECD-123`)
2. Add a comment: "Test webhook - please ignore"
3. Check your server logs for the webhook event

### Option 2: Use Jira's Test Feature

1. In Jira Webhook settings, find your webhook
2. Click the **"..." menu** → **View Details**
3. Scroll to **Recent Deliveries** to see test results

## Step 3: Verify Server Received Webhook

Check the server logs:

```bash
# If running in foreground
# You'll see: 📥 JIRA WEBHOOK RECEIVED

# If running as systemd service
sudo journalctl -u pm-agent -f

# Check database
python -c "
from src.database.models import get_session, WebhookEvent
session = get_session()
webhooks = session.query(WebhookEvent).all()
print(f'Total webhooks received: {len(webhooks)}')
for w in webhooks[-5:]:
    print(f'  {w.source}:{w.event_type} - {w.processed}')
session.close()
"
```

## Step 4: Enable Production Mode

Once testing is complete, update the orchestrator to actually post comments:

1. **Get Anthropic API Key**: https://console.anthropic.com/
2. **Add to .env**:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

3. **Enable Real Jira Comments** (in `src/orchestration/simple_orchestrator.py:282`):
   ```python
   # Uncomment these lines:
   if self.jira:
       try:
           self.jira.add_comment(issue_key, response_text)
           actions[-1]["status"] = "executed"
       except Exception as e:
           actions[-1]["status"] = "failed"
           actions[-1]["error"] = str(e)
   ```

4. **Restart Server**:
   ```bash
   # If using systemd
   sudo systemctl restart pm-agent

   # If running manually
   # Ctrl+C to stop, then:
   python -m src.web.app
   ```

## Troubleshooting

### Webhook Not Received

1. **Check server is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check firewall allows port 8000**:
   ```bash
   sudo ufw allow 8000
   # or
   sudo firewall-cmd --add-port=8000/tcp --permanent
   sudo firewall-cmd --reload
   ```

3. **Test from external network**:
   ```bash
   curl http://YOUR_DOMAIN:8000/health
   ```

4. **Check Jira webhook logs**:
   - Go to Jira → Settings → Webhooks
   - Click your webhook → View Details
   - Check "Recent Deliveries" for errors

### Webhook Received but Not Processed

1. **Check orchestrator initialization**:
   - Look for "✅ Orchestrator initialized" in logs
   - If you see "⚠️ Orchestrator not fully initialized", check `.env` file

2. **Check ANTHROPIC_API_KEY**:
   ```bash
   grep ANTHROPIC_API_KEY .env
   ```

3. **Check database**:
   ```bash
   python -m src.database.models
   ```

### Agent Not Responding to Comments

1. **Check webhook event type**:
   - Only `comment_created` events trigger the agent
   - Other events are logged but not processed

2. **Check orchestrator decision**:
   ```bash
   python -c "
   from src.database.models import get_session, AgentCycle
   import json
   session = get_session()
   cycle = session.query(AgentCycle).order_by(AgentCycle.id.desc()).first()
   if cycle:
       plan = json.loads(cycle.plan)
       print(f'Should respond: {plan.get(\"should_respond\")}')
       print(f'Reasoning: {plan.get(\"reasoning\")}')
   session.close()
   "
   ```

## Security Considerations

### Production Recommendations

1. **Use HTTPS**: Set up SSL/TLS certificate (Let's Encrypt)
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

2. **Webhook Secret**: Add authentication to webhook endpoint
   - Configure secret in Jira webhook settings
   - Validate signature in FastAPI endpoint

3. **Rate Limiting**: Add rate limiting to prevent abuse
   ```bash
   pip install slowapi
   ```

4. **IP Whitelist**: Restrict to Atlassian IPs
   - See: https://support.atlassian.com/organization-administration/docs/ip-addresses-and-domains-for-atlassian-cloud-products/

## Next Steps

Once webhooks are working:

1. **Monitor SLAs**: Agent will automatically track comment response times
2. **Enable Auto-Responses**: Uncomment the Jira posting code
3. **Add More Events**: Subscribe to `issue_updated`, `sprint_started`, etc.
4. **Integrate Bitbucket**: Add PR review monitoring
5. **Integrate Slack**: Add slash commands for manual agent invocation

## Reference

- **Jira Webhook Documentation**: https://developer.atlassian.com/server/jira/platform/webhooks/
- **Webhook Events Reference**: https://developer.atlassian.com/cloud/jira/platform/webhooks/
- **Testing Webhooks**: Use https://webhook.site/ for debugging payloads
