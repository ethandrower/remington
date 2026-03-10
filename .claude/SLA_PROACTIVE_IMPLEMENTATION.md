# SLA Proactive Monitoring - Implementation Plan

**Status:** IN PROGRESS
**Priority:** CRITICAL
**Owner:** PM Agent Development

## Current State

### What Works ✅
- `scripts/sla_check_working.py` detects SLA violations
- Categorizes violations by severity (warning, critical)
- Checks PRs for staleness
- Outputs violations to console/Slack summary

### What's Missing ❌
- **No Jira comment posting** - Violations detected but developers aren't notified in Jira
- **No Slack thread creation** - No individual threads for tracking violations
- **No developer tagging** - Can't @mention developers in Jira
- **No escalation matrix execution** - 4-level escalation not implemented
- **No historical tracking** - Violations not saved to database

## Required Enhancements

### 1. Jira Comment Posting with Developer Tagging

**Goal:** When SLA violation detected, automatically post comment to Jira ticket tagging the responsible developer.

**Implementation:**

```python
def post_jira_comment_with_tag(issue_key: str, developer_account_id: str, message: str):
    """
    Post comment to Jira ticket with developer mention
    Uses MCP Atlassian tools
    """
    # Format message with ADF (Atlassian Document Format) mention
    comment_body = f"""
{{
  "type": "doc",
  "version": 1,
  "content": [
    {{
      "type": "paragraph",
      "content": [
        {{
          "type": "mention",
          "attrs": {{
            "id": "{developer_account_id}"
          }}
        }},
        {{
          "type": "text",
          "text": " {message}"
        }}
      ]
    }}
  ]
}}
"""

    # Use MCP tool to add comment
    # mcp__atlassian__addCommentToJiraIssue(
    #     cloudId=CLOUD_ID,
    #     issueIdOrKey=issue_key,
    #     commentBody=comment_body
    # )
```

**Developer Lookup:**
Need to map developer names to Jira account IDs. Use `.claude/procedures/developer-lookup-tagging.md`:

```python
DEVELOPER_ACCOUNT_IDS = {
    "Mohamed": "accountid:712020:27a3f2fe-9037-455d-9392-fb80ba1705c0",
    "Ahmed": "accountid:...",  # Need to look up
    "Thanh": "accountid:...",
    "Valentin": "accountid:...",
    "Josh": "accountid:..."
}
```

### 2. Slack Thread Creation

**Goal:** Create dedicated Slack thread for each critical violation for tracking resolution.

**Implementation:**

```python
def create_slack_escalation_thread(violation: Dict) -> str:
    """
    Create Slack thread for SLA violation tracking
    Returns thread_ts for future updates
    """
    import requests

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_STANDUP")

    # Initial message
    message = f"""
🚨 *SLA Violation Detected*

*Item:* {violation['item_id']}
*Type:* {violation['type']}
*Owner:* {violation['owner']}
*Overdue by:* {violation['hours_overdue']:.0f} hours

*Action Required:* {violation['message']}

*Links:*
• {violation['link']}

_This thread will track resolution progress. Reply here with updates._
"""

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {slack_token}"},
        json={
            "channel": channel,
            "text": f"SLA Violation: {violation['item_id']}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message}
                }
            ]
        }
    )

    if response.ok:
        data = response.json()
        return data.get("ts")  # Thread timestamp for replies

    return None
```

### 3. Escalation Matrix Implementation

**Goal:** Execute 4-level escalation based on violation age and severity.

**Escalation Levels:**

#### Level 1: Soft Reminder (0-1 days overdue)
- **Action:** Jira comment only
- **Template:** "Hi @developer, just a gentle reminder..."
- **Tracking:** Log in `active-violations.json`

#### Level 2: Jira + Slack Thread (1-2 days overdue)
- **Action:** Jira comment + Slack thread creation
- **Template:** "Hi @developer, [item] is now X days overdue..."
- **Tracking:** Update violation with thread_ts

#### Level 3: Team Escalation (2-3 days overdue)
- **Action:** Jira + Slack + Tech Lead notification
- **Template:** "Hi team, requires immediate attention..."
- **Tracking:** Flag for management review

#### Level 4: Leadership (3+ days overdue)
- **Action:** All above + Leadership notification
- **Template:** "Hi @leadership, exceeded escalation threshold..."
- **Tracking:** Create incident report

**Implementation:**

```python
def execute_escalation(violation: Dict, current_level: int) -> int:
    """
    Execute appropriate escalation level
    Returns new escalation level
    """
    days_overdue = violation['hours_overdue'] / 24

    # Determine escalation level
    if days_overdue >= 3:
        target_level = 4
    elif days_overdue >= 2:
        target_level = 3
    elif days_overdue >= 1:
        target_level = 2
    else:
        target_level = 1

    # Only escalate, never de-escalate
    new_level = max(current_level, target_level)

    # Execute escalation actions
    if new_level >= 1 and current_level < 1:
        post_jira_soft_reminder(violation)

    if new_level >= 2 and current_level < 2:
        post_jira_escalation(violation)
        thread_ts = create_slack_escalation_thread(violation)
        violation['slack_thread_ts'] = thread_ts

    if new_level >= 3 and current_level < 3:
        update_slack_thread_with_techlead(violation)
        post_jira_team_escalation(violation)

    if new_level >= 4 and current_level < 4:
        notify_leadership(violation)
        create_incident_report(violation)

    return new_level
```

### 4. Historical Violation Tracking

**Goal:** Persist violation data across runs to track escalation history and resolution.

**Data Structure:**

```json
{
  "violations": [
    {
      "id": "ECD-123_comment_response",
      "issue_key": "ECD-123",
      "type": "jira_comment_response",
      "detected_at": "2025-10-29T10:00:00Z",
      "first_detected": "2025-10-27T10:00:00Z",
      "due_at": "2025-10-27T10:00:00Z",
      "hours_overdue": 48,
      "owner": "Mohamed",
      "owner_account_id": "accountid:...",
      "escalation_level": 2,
      "actions_taken": [
        {
          "level": 1,
          "timestamp": "2025-10-28T09:00:00Z",
          "action": "jira_comment",
          "jira_comment_id": "12345"
        },
        {
          "level": 2,
          "timestamp": "2025-10-29T09:00:00Z",
          "action": "slack_thread",
          "slack_thread_ts": "1698573600.123456"
        }
      ],
      "resolved": false,
      "resolved_at": null
    }
  ],
  "last_updated": "2025-10-29T10:00:00Z"
}
```

**Storage Location:**
`.claude/data/sla-tracking/active-violations.json`

**Persistence Functions:**

```python
def load_active_violations() -> Dict:
    """Load existing violations from disk"""
    violations_file = Path(".claude/data/sla-tracking/active-violations.json")
    if violations_file.exists():
        return json.loads(violations_file.read_text())
    return {"violations": [], "last_updated": None}

def save_active_violations(data: Dict):
    """Save violations to disk"""
    violations_file = Path(".claude/data/sla-tracking/active-violations.json")
    violations_file.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    violations_file.write_text(json.dumps(data, indent=2))

def update_violation_status(violation_id: str, new_level: int, action: Dict):
    """Update specific violation with new escalation"""
    data = load_active_violations()

    for v in data["violations"]:
        if v["id"] == violation_id:
            v["escalation_level"] = new_level
            v["actions_taken"].append(action)
            v["hours_overdue"] = calculate_hours_overdue(v)
            break
    else:
        # New violation
        data["violations"].append({
            "id": violation_id,
            "escalation_level": new_level,
            "actions_taken": [action],
            # ... other fields
        })

    save_active_violations(data)

def mark_violation_resolved(violation_id: str):
    """Mark violation as resolved and archive"""
    data = load_active_violations()

    for i, v in enumerate(data["violations"]):
        if v["id"] == violation_id:
            v["resolved"] = True
            v["resolved_at"] = datetime.now().isoformat()

            # Archive to daily snapshot
            archive_resolved_violation(v)

            # Remove from active list
            data["violations"].pop(i)
            break

    save_active_violations(data)
```

### 5. Daily Snapshots for Trend Analysis

**Goal:** Save daily snapshot of all violations for historical trend analysis.

**File:** `.claude/data/sla-tracking/daily-snapshots/YYYY-MM-DD.json`

```python
def save_daily_snapshot(violations: List[Dict]):
    """Save daily snapshot for trend analysis"""
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot_file = Path(f".claude/data/sla-tracking/daily-snapshots/{today}.json")
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "total_violations": len(violations),
        "by_severity": categorize_by_severity(violations),
        "by_type": categorize_by_type(violations),
        "by_developer": categorize_by_developer(violations),
        "violations": violations
    }

    snapshot_file.write_text(json.dumps(snapshot, indent=2))
```

## Integration with sla_check_working.py

### Enhanced Workflow

```python
def main():
    # 1. Load previous violations
    historical_data = load_active_violations()

    # 2. Detect current violations
    pr_violations = check_pr_slas()
    jira_violations = check_jira_slas_via_claude()
    all_violations = pr_violations + jira_violations

    # 3. For each violation, check if it's new or existing
    for violation in all_violations:
        violation_id = f"{violation['item_id']}_{violation['type']}"

        # Find in historical data
        existing = find_violation(historical_data, violation_id)

        if existing:
            current_level = existing['escalation_level']
        else:
            current_level = 0

        # Execute escalation
        new_level = execute_escalation(violation, current_level)

        # Update tracking
        update_violation_status(violation_id, new_level, {
            "level": new_level,
            "timestamp": datetime.now().isoformat(),
            "action": get_action_type(new_level)
        })

    # 4. Check for resolved violations (no longer in current violations)
    check_for_resolved_violations(historical_data, all_violations)

    # 5. Save daily snapshot
    save_daily_snapshot(all_violations)

    # 6. Generate report
    generate_sla_report(all_violations)
```

## Developer Account ID Lookup

**Need to obtain Jira account IDs for all developers:**

```bash
# Via MCP tool
mcp__atlassian__lookupJiraAccountId(
    cloudId="67bbfd03-b309-414f-9640-908213f80628",
    searchString="Mohamed"
)
```

**Store in `.env`:**
```bash
DEVELOPER_MOHAMED_JIRA=accountid:712020:27a3f2fe-9037-455d-9392-fb80ba1705c0
DEVELOPER_AHMED_JIRA=accountid:...
DEVELOPER_THANH_JIRA=accountid:...
DEVELOPER_VALENTIN_JIRA=accountid:...
DEVELOPER_JOSH_JIRA=accountid:...
```

## Testing Plan

### Phase 1: Jira Comment Posting
1. Manually trigger SLA check with known violation
2. Verify Jira comment is posted
3. Verify developer is properly tagged
4. Check comment formatting

### Phase 2: Slack Thread Creation
1. Trigger Level 2 escalation
2. Verify Slack thread is created
3. Verify thread contains correct info and links
4. Test thread updates

### Phase 3: Escalation Matrix
1. Create test violations at different ages
2. Verify correct escalation level is determined
3. Verify only new actions are taken (no duplicates)
4. Test all 4 escalation levels

### Phase 4: Historical Tracking
1. Run SLA check multiple times
2. Verify violations persist across runs
3. Verify escalation levels increase correctly
4. Test violation resolution detection

### Phase 5: End-to-End
1. Run daily standup workflow
2. Verify SLA section includes violations
3. Verify all escalations are executed
4. Verify daily snapshot is saved

## Deployment

### Manual Testing
```bash
# Dry run (no posting)
python scripts/sla_check_working.py --no-slack

# Live run
python scripts/sla_check_working.py
```

### Automated (Cron)
```bash
# Run every hour during business hours
0 9-17 * * 1-5 cd /path/to/project-manager && python scripts/sla_check_working.py

# Run daily standup at 9am
0 9 * * 1-5 cd /path/to/project-manager && python run_agent.py standup
```

### Heroku Scheduler
```yaml
# clock.py for APScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

# SLA check every hour
scheduler.add_job(run_sla_check, 'cron', hour='9-17', day_of_week='mon-fri')

# Daily standup at 9am
scheduler.add_job(run_standup, 'cron', hour=9, day_of_week='mon-fri')

scheduler.start()
```

## Success Metrics

### Immediate (Week 1)
- [x] SLA violations detected
- [ ] Jira comments posted automatically
- [ ] Developer tagging works
- [ ] Slack threads created for critical items
- [ ] Violations persist across runs

### Short-term (Month 1)
- [ ] ≥ 90% SLA compliance rate
- [ ] Average response time < 48 hours
- [ ] < 5% escalations reach Level 3/4
- [ ] Zero missed violations

### Long-term (Quarter 1)
- [ ] Decreasing violation trends
- [ ] Improved team response times
- [ ] Automated resolution for routine issues
- [ ] Predictive SLA risk detection

## Files to Modify

1. **scripts/sla_check_working.py** - Add escalation execution
2. **scripts/sla_escalation.py** - NEW: Escalation logic module
3. **scripts/sla_persistence.py** - NEW: Historical tracking module
4. **.env** - Add developer account IDs
5. **.claude/data/sla-tracking/** - Create directory structure

## Next Steps

1. **Obtain developer Jira account IDs** via MCP lookup
2. **Implement Jira comment posting** with developer tagging
3. **Implement Slack thread creation** for Level 2+ escalations
4. **Add historical tracking** with JSON persistence
5. **Test escalation matrix** with real violations
6. **Deploy to cron/Heroku** for autonomous operation

---

**Owner:** PM Agent Development
**Last Updated:** 2025-10-29
**Status:** Ready for implementation
