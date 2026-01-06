# SLA Alert Deduplication - Skill

## Purpose

This skill prevents duplicate SLA violation alerts from being posted to Slack every hour. It ensures that once an SLA violation is alerted, it won't be re-alerted for 24 hours unless the escalation level increases.

## Problem Solved

**Before**: The SLA monitor would post the same violation to Slack every hour, even if:
- The user already replied and addressed it
- The deadline was extended
- The issue was partially resolved

**After**: Violations are only alerted when:
- This is the first time we're alerting about it, OR
- 24 hours have passed since the last alert, OR
- The escalation level has increased (e.g., Level 1 → Level 2)

## How It Works

### Database Tracking

The system uses a new `sla_alerts` table in the SQLite database (`.claude/data/bot-state/slack_state.db`):

```sql
CREATE TABLE sla_alerts (
    violation_id TEXT PRIMARY KEY,           -- e.g., "PR-114_pr_stale"
    item_id TEXT NOT NULL,                   -- e.g., "PR-114"
    violation_type TEXT NOT NULL,            -- e.g., "pr_stale"
    last_alerted_at TIMESTAMP NOT NULL,      -- When we last posted to Slack
    alert_count INTEGER DEFAULT 1,           -- How many times we've alerted
    current_escalation_level INTEGER DEFAULT 1,  -- Escalation level (1-4)
    slack_thread_ts TEXT,                    -- Slack thread timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Decision Flow

When the SLA monitor finds violations, it checks each one:

1. **New Violation?**
   - If `violation_id` doesn't exist in database → **ALERT**

2. **Escalation Increased?**
   - If `current_escalation` > `stored_escalation` → **ALERT**

3. **24 Hours Passed?**
   - If `(now - last_alerted_at) >= 24 hours` → **ALERT**

4. **Otherwise**
   - Skip this violation (already alerted recently)

### Example Scenarios

**Scenario 1: First Alert**
```
Hour 1: PR-114 detected as stale
→ No record in database
→ ✅ POST TO SLACK
→ Record: PR-114_pr_stale, last_alerted_at = 2025-11-17 10:00
```

**Scenario 2: Re-run Within 24 Hours**
```
Hour 2: PR-114 still stale
→ Record found: last_alerted_at = 2025-11-17 10:00 (1 hour ago)
→ ⏭️ SKIP (< 24 hours)
```

**Scenario 3: Escalation Increase**
```
Hour 3: PR-114 escalated from Level 1 → Level 2
→ Record found: escalation_level = 1, new level = 2
→ ✅ POST TO SLACK (escalation increased)
→ Update: current_escalation_level = 2, last_alerted_at = now
```

**Scenario 4: 24 Hours Later**
```
Hour 25: PR-114 still stale at Level 2
→ Record found: last_alerted_at = 2025-11-17 10:00 (25 hours ago)
→ ✅ POST TO SLACK (24+ hours passed)
→ Update: last_alerted_at = now, alert_count = 2
```

**Scenario 5: User Fixed the Issue**
```
Hour 26: User replied and extended deadline
→ PR-114 no longer in SLA violations list
→ No alert needed (not in violations)
→ (Future: can call `clear_resolved_violations()` to clean database)
```

## Implementation Files

### Core Module
**File**: `scripts/sla_alert_tracker.py`

Provides helper functions:
- `should_alert_violation(violation)` - Returns True if we should alert
- `record_alert(violation, slack_thread_ts)` - Records that we alerted
- `get_alert_history(item_id, violation_type)` - Gets alert history
- `clear_resolved_violations(item_ids)` - Cleans up resolved items

### Integration Point
**File**: `scripts/sla_check_working.py`

Modified `post_violations_to_slack()` function:
```python
from sla_alert_tracker import should_alert_violation, record_alert

for violation in sorted_violations:
    # Check deduplication BEFORE posting
    if not should_alert_violation(violation):
        skipped_count += 1
        continue

    # Post to Slack
    response = requests.post(...)

    if result.get("ok"):
        # Record this alert AFTER posting
        record_alert(violation, slack_thread_ts=thread_ts)
```

### Database Initialization
**File**: `bots/slack_monitor.py`

The `init_db()` method now creates the `sla_alerts` table automatically on bot startup.

## Usage

### For Developers

No special actions needed. The deduplication happens automatically when SLA checks run.

### Manual Testing

To test the deduplication manually:

```bash
# Run SLA check (will alert on new violations)
python scripts/sla_check_working.py

# Run again immediately (should skip recent alerts)
python scripts/sla_check_working.py

# Check what was skipped in the output:
# "⏭️  Skipped 3 violations (alerted within last 24h)"
```

### View Alert History

```python
from scripts.sla_alert_tracker import get_alert_history

# Get all alerts for an item
history = get_alert_history("PR-114")

# Get specific violation type
history = get_alert_history("PR-114", "pr_stale")

# Example output:
# [
#   {
#     "violation_id": "PR-114_pr_stale",
#     "item_id": "PR-114",
#     "violation_type": "pr_stale",
#     "last_alerted_at": "2025-11-17T10:00:00",
#     "alert_count": 2,
#     "current_escalation_level": 1,
#     "slack_thread_ts": "1731847200.123456"
#   }
# ]
```

### Clear Resolved Violations

When violations are confirmed resolved, clean up the database:

```python
from scripts.sla_alert_tracker import clear_resolved_violations

# Clear specific items
clear_resolved_violations(["PR-114", "ECD-123"])
```

## Violation ID Format

Each violation is uniquely identified by: `{item_id}_{violation_type}`

**Examples:**
- `PR-114_pr_stale` - PR-114 is stale
- `ECD-123_comment_response` - ECD-123 has unanswered comment
- `ECD-456_blocked_update` - ECD-456 is blocked without updates
- `ECD-789_pending_approval` - ECD-789 stuck in pending approval

## Configuration

### 24-Hour Window

The 24-hour cooldown is hardcoded in `sla_alert_tracker.py`:

```python
if hours_since_alert >= 24:
    return True  # Alert again
```

To change this, modify the comparison in `should_alert_violation()`.

### Escalation Levels

Escalation levels (1-4) correspond to SLA escalation matrix:
- **Level 1**: Soft reminder (Jira comment only)
- **Level 2**: Jira + Slack notification
- **Level 3**: Team escalation
- **Level 4**: Leadership escalation

If a violation moves from Level 1 → Level 2, it will re-alert immediately even if within 24 hours.

## Monitoring

### Database Query Examples

```sql
-- View all active alerts
SELECT * FROM sla_alerts ORDER BY last_alerted_at DESC;

-- Find violations alerted multiple times
SELECT * FROM sla_alerts WHERE alert_count > 1;

-- Find violations at high escalation levels
SELECT * FROM sla_alerts WHERE current_escalation_level >= 3;

-- Count alerts by violation type
SELECT violation_type, COUNT(*) as count
FROM sla_alerts
GROUP BY violation_type;

-- Find violations alerted in last 24 hours
SELECT * FROM sla_alerts
WHERE datetime(last_alerted_at) > datetime('now', '-24 hours');
```

### Log Output

When SLA check runs, you'll see:
```
🔍 Checking 5 violations for deduplication...
   🆕 New violation: PR-114_pr_stale - WILL ALERT
   ⏭️  Skipping ECD-123_comment_response: alerted 2.5h ago (< 24h)
   ⬆️  Escalation increased for ECD-456_blocked_update: L1 → L2 - WILL ALERT
   🕐 24+ hours since last alert for ECD-789_pending_approval (26.3h) - WILL ALERT

   ✅ Posted 3/5 violations to Slack
   ⏭️  Skipped 2 violations (alerted within last 24h)
```

## Benefits

1. **Reduced Slack Noise**: Team isn't bombarded with duplicate alerts every hour
2. **User-Friendly**: Respects when users have responded/addressed issues
3. **Smart Escalation**: Re-alerts when severity increases
4. **Audit Trail**: Complete history of all alerts in database
5. **Persistent**: Survives bot restarts (stored in SQLite)

## Future Enhancements

Potential improvements:
1. **Reply Detection**: Auto-clear alerts when user replies in Slack thread
2. **Jira Status Sync**: Auto-clear when Jira ticket is resolved
3. **Configurable Cooldown**: Make 24-hour window adjustable per violation type
4. **Alert Fatigue Prevention**: Exponential backoff (24h, 48h, 72h...)
5. **Dashboard**: Web UI to view alert history and trends

## Related Files

- **Implementation**: `scripts/sla_alert_tracker.py`
- **Integration**: `scripts/sla_check_working.py` (lines 262-361)
- **Database Init**: `bots/slack_monitor.py` (lines 47-94)
- **SLA Monitor**: `.claude/agents/sla-monitor.md`
- **Escalation Logic**: `scripts/sla_escalation.py`

---

**This feature prevents the PR-114 duplicate alert issue and ensures SLA alerts are timely, relevant, and not repetitive.**
