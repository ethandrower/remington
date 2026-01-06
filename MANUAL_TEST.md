# PM Agent - Manual Testing Procedure

Run these tests locally to verify the system is working before deployment.

---

## Test 1: Verify All Components Initialize

```bash
python -m pytest tests/test_polling_monitors.py -v
```

**Expected:** All tests pass (should take ~60 seconds)

**What This Tests:**
- ✅ All 3 monitors (Slack, Jira, Bitbucket) connect to APIs
- ✅ Claude Code CLI is available
- ✅ Database tracking works
- ✅ No duplicate processing

---

## Test 2: Start the Full Service

```bash
python -m src.pm_agent_service
```

**Expected Output:**
```
======================================================================
                      🤖 CiteMed PM Agent Service
======================================================================

Strategy:
  - Webhooks: Primary (instant response)
  - Polling: Backup (catches missed events)
  - Intelligence: Claude Code with MCP tools

✅ Claude Code Orchestrator ready
✅ Slack Monitor initialized (15s polling)
✅ Jira Monitor initialized (30s polling)
✅ Bitbucket Monitor initialized (30s polling)

======================================================================
                     🟢 PM Agent Service Starting
======================================================================

🔄 Starting Slack polling thread (primary)...
✅ Slack polling started (interval: 15s)

🔄 Starting Jira backup polling thread...
✅ Jira backup polling started (interval: 30s)

🔄 Starting Bitbucket backup polling thread...
✅ Bitbucket backup polling started (interval: 30s)

🚀 Starting webhook server on port 8000...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**What This Tests:**
- ✅ Service starts without errors
- ✅ All 3 polling threads running
- ✅ Webhook server listening on port 8000

**Leave this running in Terminal 1**

---

## Test 3: Check Health Endpoint

In a **new terminal** (Terminal 2):

```bash
curl http://localhost:8000/health | python -m json.tool
```

**Expected:**
```json
{
    "status": "healthy",
    "timestamp": "2025-11-08T18:26:11.563451",
    "phase": "0 - Hello World"
}
```

**What This Tests:**
- ✅ Webhook server is responding
- ✅ HTTP endpoint working

---

## Test 4: Send Test Webhook (Simulated Jira Comment)

```bash
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "comment_created",
    "comment": {
      "body": {
        "type": "doc",
        "content": [{
          "type": "paragraph",
          "content": [{
            "type": "text",
            "text": "Can someone review this PR? Its been waiting 3 days."
          }]
        }]
      },
      "author": {
        "displayName": "Test User"
      }
    },
    "issue": {
      "key": "ECD-TEST",
      "fields": {
        "summary": "Test webhook processing"
      }
    }
  }'
```

**Expected Response:**
```json
{
  "status":"processing",
  "webhook_id":2,
  "issue_key":"ECD-TEST",
  "timestamp":"2025-11-08T18:26:11.564088"
}
```

**In Terminal 1 (service logs), you should see:**
```
============================================================
📥 JIRA WEBHOOK RECEIVED
============================================================
Event: comment_created
Issue: ECD-TEST

🤖 Triggering orchestrator for ECD-TEST...

============================================================
🔄 CLAUDE CODE REASONING CYCLE
============================================================
Agent: jira-manager
Trigger: Jira comment on ECD-TEST
Commenter: Test User
Comment: Can someone review this PR? Its been waiting 3 days....

🤖 Invoking Claude Code (attempt 1/2, timeout: 10 min)...
   ✅ Claude Code response received (4567 chars)
💾 Logging cycle to database...
   ✓ Cycle #8 logged

============================================================
✅ CYCLE COMPLETE
============================================================
```

**What This Tests:**
- ✅ Webhook received and logged
- ✅ Background task triggered
- ✅ Claude Code invoked with full context
- ✅ Agent reads `.claude/agents/jira-manager.md`
- ✅ Uses MCP tools to query Jira
- ✅ Generates intelligent response
- ✅ Logs to database

**This should complete in ~30-60 seconds**

---

## Test 5: Verify Database Logging

```bash
sqlite3 ./data/pm_agent.db "SELECT id, trigger_type, status, created_at FROM agent_cycles ORDER BY id DESC LIMIT 5;"
```

**Expected:**
```
8|jira_comment|complete|2025-11-08 18:26:45
7|jira_comment|complete|2025-11-08 18:05:12
...
```

**What This Tests:**
- ✅ Database logging works
- ✅ Audit trail created
- ✅ All cycles tracked

---

## Test 6: Watch Polling in Action

Leave the service running and watch the logs. Every 15-30 seconds you'll see:

**Slack Polling (every 15s):**
```
(Usually silent unless new mentions found)
```

**Jira Polling (every 30s):**
```
(Usually silent unless new comments found)
```

**If Slack or Jira detect new items, you'll see:**
```
============================================================
📥 JIRA MENTION DETECTED (via backup polling)
============================================================
Issue: ECD-456
Comment: Please help review this...

🤖 Triggering orchestrator...
```

**What This Tests:**
- ✅ Polling threads running continuously
- ✅ No errors or crashes
- ✅ Database prevents reprocessing (won't process same item twice)

---

## Test 7: Verify No Reprocessing

Send the **same webhook again** (Test 4):

```bash
curl -X POST http://localhost:8000/webhooks/jira \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "comment_created",
    "comment": { ... same payload ... },
    "issue": { "key": "ECD-TEST" }
  }'
```

**Expected:**
- ✅ Webhook received
- ✅ But Claude Code SHOULD still process (webhooks don't track duplicates, only polling does)

**What This Tests:**
- Webhook pipeline processes every webhook (by design)
- Polling pipeline tracks and deduplicates (by design)

---

## Test 8: Stop the Service Gracefully

In Terminal 1, press `Ctrl+C`

**Expected:**
```
============================================================
         🛑 Shutting down PM Agent Service
============================================================

✅ Shutdown complete
```

**What This Tests:**
- ✅ Graceful shutdown
- ✅ Threads terminate cleanly
- ✅ Database closes properly

---

## Test 9: Restart and Verify Persistence

Start the service again:

```bash
python -m src.pm_agent_service
```

Then check the database:

```bash
sqlite3 .claude/data/bot-state/jira_state.db "SELECT COUNT(*) FROM processed_mentions;"
```

**Expected:**
```
(Same count as before - database persisted)
```

**What This Tests:**
- ✅ Database survives restarts
- ✅ No data loss
- ✅ Tracking persists

---

## ✅ All Tests Passed?

If all 9 manual tests pass:

1. **Polling works** ✅ - Detects new items every 15-30s
2. **Claude Code works** ✅ - Intelligent responses with business context
3. **Webhooks work** ✅ - Instant processing < 100ms response
4. **Database works** ✅ - No reprocessing, full audit trail
5. **Hybrid architecture works** ✅ - Polling + webhooks running together

**You're ready to deploy!** 🚀

---

## Troubleshooting

### Issue: "Claude Code CLI not found"
**Fix:** Install Claude Code from https://claude.com/claude-code

### Issue: "Slack monitor not initialized"
**Fix:** Check `.env` has `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_STANDUP`, `SLACK_BOT_USER_ID`

### Issue: "Jira monitor not initialized"
**Fix:** Check `.env` has `ATLASSIAN_SERVICE_ACCOUNT_TOKEN`, `ATLASSIAN_CLOUD_ID`

### Issue: Polling is slow
**Fix:** Check network connection to Slack/Jira/Bitbucket APIs

### Issue: Claude Code times out
**Fix:** Increase timeout in orchestrator (default 10 minutes)

---

## Next Steps After Manual Testing

1. ✅ All manual tests pass
2. Deploy to home server
3. Register webhooks in Jira/Bitbucket
4. Monitor logs: `journalctl -u pm-agent -f`
5. Validate with real events

**Questions?** Check `TEST_PLAN.md` for detailed test scenarios.
