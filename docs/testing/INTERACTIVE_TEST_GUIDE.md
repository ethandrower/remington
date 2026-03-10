# Interactive Manual Testing Guide - Conversational Context

**Purpose:** Test that the PM Agent maintains conversation context across multiple interactions
**Duration:** ~15-20 minutes
**Prerequisites:** PM Agent service running (`python src/pm_agent_service.py`)

---

## Test 1: Slack Thread Context Preservation

**Goal:** Verify bot maintains context across multiple Slack thread replies

### Steps:

**1. Start a new thread in #citemed-development**
```
Post message: "What's the status of ECD-862?"
```

**Expected Bot Response:**
- ✅ Bot should fetch ECD-862 details from Jira
- ✅ Bot should reply with current status, assignee, priority
- ✅ Bot should reply IN THREAD

**Check:**
- [ ] Bot replied in thread
- [ ] Response includes specific ECD-862 details
- [ ] Response timestamp shows it's threaded

---

**2. Reply in the SAME thread (don't mention ticket number)**
```
Reply in thread: "@Remington when will this be done?"
```

**Expected Bot Response:**
- ✅ Bot should understand "this" refers to ECD-862 (from thread context)
- ✅ Bot should NOT ask "which ticket?"
- ✅ Bot should provide due date or estimate for ECD-862

**Check:**
- [ ] Bot understood "this" = ECD-862
- [ ] Bot didn't ask for clarification
- [ ] Response is contextually appropriate

---

**3. Another reply in SAME thread (pronoun reference)**
```
Reply in thread: "@Remington can you update its priority to Highest?"
```

**Expected Bot Response:**
- ✅ Bot should understand "its" refers to ECD-862
- ✅ Bot should update ECD-862 priority to Highest
- ✅ Bot should confirm the update in response

**Check:**
- [ ] Bot updated ECD-862 (check Jira)
- [ ] Priority changed to "Highest"
- [ ] Bot confirmed the action in Slack

**Verify in logs:**
```bash
# Look for this in pm_agent.log or console:
grep "Using full issue context" <log-file>
# Should show: "Using full issue context (N previous comments)"
```

---

## Test 2: Jira Comment Thread Context

**Goal:** Verify bot maintains context across multiple Jira comments

### Steps:

**1. Post first comment on a Jira ticket (e.g., ECD-862)**
```
Go to: https://citemed.atlassian.net/browse/ECD-862
Add comment: "@remington what's the current status of this ticket?"
```

**Expected Bot Response:**
- ✅ Bot should reply as Jira comment
- ✅ Response includes issue description context
- ✅ Response includes status, assignee, progress

**Check:**
- [ ] Bot posted comment to Jira
- [ ] Response references issue description
- [ ] Response is factually correct

---

**2. Post follow-up comment (no ticket number mentioned)**
```
Add comment on SAME ticket: "@remington can you increase the priority?"
```

**Expected Bot Response:**
- ✅ Bot should see previous comments in issue context
- ✅ Bot should understand "the priority" refers to THIS issue
- ✅ Bot should update priority and confirm

**Check:**
- [ ] Bot updated priority
- [ ] Bot didn't ask "which ticket?"
- [ ] Response shows awareness of previous conversation

**Verify in logs:**
```bash
# Look for:
grep "Fetching issue context" <log-file>
# Should show: "Fetching issue context for ECD-862..."
# Should show: "Context fetched: N comments"
```

---

**3. Test issue description awareness**
```
Add comment: "@remington based on the requirements, do we need Microsoft OAuth?"
```

**Expected Bot Response:**
- ✅ Bot should reference issue DESCRIPTION (not just comments)
- ✅ If description mentions Google OAuth, bot should know context
- ✅ Response should show understanding of feature requirements

**Check:**
- [ ] Bot referenced issue description in response
- [ ] Bot showed understanding of OAuth requirements
- [ ] Response is contextually relevant to feature scope

---

## Test 3: Cross-Platform Context

**Goal:** Verify context flows between Slack and Jira

### Steps:

**1. Start in Slack**
```
Post to #citemed-development: "@Remington create a bug ticket for login timeout issue"
```

**Expected Bot Response:**
- ✅ Bot creates Jira ticket
- ✅ Bot replies with ticket key (e.g., "Created ECD-XXX")

**Note the ticket key:** ECD-_____

---

**2. Go to that Jira ticket and comment**
```
Navigate to the created ticket: ECD-XXX
Add comment: "@remington can you add steps to reproduce?"
```

**Expected Bot Response:**
- ✅ Bot should see issue context (title: "login timeout issue")
- ✅ Bot should understand this is a bug ticket created from Slack
- ✅ Bot should add reproduction steps or ask for them

**Check:**
- [ ] Bot understood this ticket's original context
- [ ] Response is appropriate for a bug ticket
- [ ] Bot referenced "login timeout" from title

---

## Test 4: Multi-Turn Conversation

**Goal:** Test extended conversation with context accumulation

### Steps:

**1. Start thread in Slack**
```
Post: "@Remington what tickets are assigned to Mohamed?"
```

**Expected:** Bot lists tickets assigned to Mohamed

---

**2. Follow-up in thread**
```
Reply in thread: "@Remington which of those are high priority?"
```

**Expected Bot Response:**
- ✅ Bot remembers "those" = tickets assigned to Mohamed
- ✅ Bot filters previous list for high priority
- ✅ Bot doesn't re-query all tickets

---

**3. Another follow-up**
```
Reply in thread: "@Remington can you create a summary report of them?"
```

**Expected Bot Response:**
- ✅ Bot remembers "them" = Mohamed's high-priority tickets
- ✅ Bot creates summary of specific tickets
- ✅ Context spans 3 messages

**Check:**
- [ ] Each reply understood previous context
- [ ] No repeated questions
- [ ] Final summary covers correct tickets

---

## Test 5: Context Error Handling

**Goal:** Verify graceful degradation when context fetch fails

### Steps:

**1. Test with invalid ticket (Slack)**
```
Post: "@Remington what's the status of ECD-99999?"
```

**Expected Bot Response:**
- ✅ Bot should handle gracefully
- ✅ Error message should be user-friendly
- ✅ Bot shouldn't crash

---

**2. Test thread with no history**
```
Post new standalone message: "@Remington tell me about testing"
```

**Expected Bot Response:**
- ✅ Bot handles message with no thread context
- ✅ Response is coherent even without thread history

---

## Verification Checklist

After running all tests, verify:

### Slack Context
- [ ] ✅ Thread context fetched for all threaded mentions
- [ ] ✅ Pronoun resolution works (this, it, that, them)
- [ ] ✅ Bot doesn't ask redundant questions
- [ ] ✅ All replies stay in correct threads

### Jira Context
- [ ] ✅ Issue description included in context
- [ ] ✅ All previous comments included
- [ ] ✅ Bot references issue details correctly
- [ ] ✅ Context logged in service logs

### Performance
- [ ] ✅ Bot responds within 10-30 seconds
- [ ] ✅ No timeout errors
- [ ] ✅ Context fetch doesn't cause delays

### Error Handling
- [ ] ✅ Invalid tickets handled gracefully
- [ ] ✅ Missing context doesn't break responses
- [ ] ✅ Bot continues working after errors

---

## Expected Log Output

When tests are working correctly, you should see:

### For Slack Thread Context:
```
📜 Fetched thread context: 2 replies
🤖 Processing Slack mention with Claude...
   📜 Using full thread context
✅ Sent response to Slack thread 1704470400.123456
```

### For Jira Comment Context:
```
   📜 Fetching issue context for ECD-862...
   ✅ Context fetched: 3 comments
   📜 Using full issue context (3 previous comments)
🤖 Processing Jira mention with Claude Code...
✅ Posted response to Jira ECD-862
```

---

## Troubleshooting

### Bot doesn't understand context

**Check:**
```bash
# Verify context is being fetched
grep "Context fetched" pm_agent.log

# Verify context is being used
grep "Using full" pm_agent.log
```

**If missing:**
- Check that `issue_context` or `thread_context` exists in event
- Verify API calls succeeded (no 500/404 errors in logs)

### Bot asks redundant questions

**Likely cause:** Context not reaching Claude prompt

**Check:**
```python
# In pm_agent_service.py, verify context formatting logic runs
# Look for these log lines:
"   📜 Using full issue context (N previous comments)"
"   📜 Using full thread context"
```

### Performance issues

**Check:**
```bash
# Test context fetch timing
pytest tests/integration/test_jira_context_flow.py::TestJiraContextPerformance -v
```

**Expected:** Context fetch < 2 seconds

---

## Success Criteria

All tests pass if:
1. ✅ Bot maintains context across 3+ message turns
2. ✅ Pronoun references resolved correctly
3. ✅ No redundant "which ticket?" questions
4. ✅ Jira comments include issue description awareness
5. ✅ Slack threads keep conversation coherent
6. ✅ Logs show context being fetched and used
7. ✅ Performance acceptable (< 30s responses)

---

## Next Steps After Manual Testing

If all tests pass:
- ✅ Mark conversational context as FULLY IMPLEMENTED
- ✅ Move to next test phase (detect→respond→mark flow)
- ✅ Update integration test plan status

If any tests fail:
- ❌ Review logs for error messages
- ❌ Check context data structure in events
- ❌ Verify Claude prompt includes full context
- ❌ File bug report with specific test that failed
