# SLA Monitoring Testing Guide

**Last Updated:** January 19, 2026

---

## Overview

This guide explains how to test the SLA monitoring system without triggering real alerts or posting to Slack/Jira.

---

## Dry-Run Testing Options

### Option 1: Unit Tests (Recommended)

**Purpose:** Test violation detection logic with mocked data

**File:** `tests/integration/test_sla_monitoring.py`

**Run:**
```bash
python tests/integration/test_sla_monitoring.py
```

**What it tests:**
- ✅ QA violation detection (24h threshold)
- ✅ Pending Approval violations (48h threshold)
- ✅ Blocked ticket violations (24h threshold)
- ✅ Severity levels (warning vs critical)
- ✅ No false positives
- ✅ Error handling

**Output:**
```
🧪 SLA MONITORING TEST SUITE (DRY-RUN)
Testing check_jira_slas_direct() function
No actual Slack/Jira API calls will be made

============================================================
TEST 1: QA Violations (24h Threshold)
============================================================
📋 Checking Jira SLAs (via Python CLI tools)...
   Found 5 open tickets
   Found 3 Jira violations

📊 Found 3 QA violations:
  - ECD-101: warning (8.0h overdue)
  - ECD-102: critical (32.0h overdue)
  - ECD-103: warning (12.0h overdue)

✅ QA violation detection working correctly!

...

🎉 ALL TESTS PASSED!
```

**Benefits:**
- 100% isolated - no external API calls
- Fast execution (< 5 seconds)
- Repeatable results
- Comprehensive coverage

---

### Option 2: Live Check with --no-slack Flag

**Purpose:** Check real Jira/Bitbucket data without posting alerts

**File:** `scripts/core/sla_check_working.py`

**Run:**
```bash
python scripts/core/sla_check_working.py --no-slack
```

**What it does:**
- ✅ Queries real Jira tickets via Python CLI
- ✅ Queries real Bitbucket PRs
- ✅ Detects actual violations
- ❌ Does NOT post to Slack
- ❌ Does NOT comment on Jira
- ✅ Prints violations to console

**Output:**
```
🔀 Checking PR SLAs (Bitbucket)...
   Found 10 open PRs in citemed_web
   Found 0 PR violations ✅

📋 Checking Jira SLAs (via Python CLI tools)...
   Found 100 open tickets
   Found 2 Jira violations

   ⚠️  ECD-585: In QA for 36.0h without update (SLA: 24h)
       Severity: warning
       Hours overdue: 12.0

   🚨 ECD-601: Pending Approval for 75.0h (SLA: 48h)
       Severity: critical
       Hours overdue: 27.0

📊 Total Violations: 2

⏭️  Skipping Slack post (--no-slack flag)
```

**Benefits:**
- Real data validation
- See actual violations in your sprint
- No alert spam
- Safe for production testing

---

### Option 3: Jira-Only Check

**Purpose:** Check only Jira violations (skip PRs)

**Run:**
```bash
python scripts/core/sla_check_working.py --no-slack --skip-pr
```

**Use case:** When you only want to verify Jira SLA checks

---

### Option 4: Deduplication Testing

**Purpose:** Test alert deduplication logic (24h cooldown)

**File:** `tests/integration/test_sla_deduplication.py`

**Run:**
```bash
python tests/integration/test_sla_deduplication.py
```

**What it tests:**
- First alert posts (no deduplication)
- Immediate re-run skips (within 24h)
- Escalation increase posts (even within 24h)
- Same escalation skips (within 24h)
- Different violation types post (separate tracking)

**Output:**
```
🧪 Testing SLA Alert Deduplication

============================================================
TEST 1: First Alert (Should Post)
============================================================
Result: ✅ WILL ALERT
📝 Recorded alert

============================================================
TEST 2: Immediate Re-run (Should Skip)
============================================================
Result: ❌ WILL NOT ALERT

...

✅ ALL TESTS PASSED!
Deduplication logic is working correctly!
```

**Note:** Test records remain in `.claude/data/bot-state/slack_state.db` and can be cleaned up:
```sql
DELETE FROM sla_alerts WHERE item_id LIKE 'TEST-%';
```

---

## Testing Workflow

### Before Deployment

1. **Run unit tests** to verify violation detection:
   ```bash
   python tests/integration/test_sla_monitoring.py
   ```

2. **Run live check** with `--no-slack` to see real violations:
   ```bash
   python scripts/core/sla_check_working.py --no-slack
   ```

3. **Verify deduplication** logic works:
   ```bash
   python tests/integration/test_sla_deduplication.py
   ```

4. **Review violations** - check if they're legitimate

5. **Deploy** when confident

### After Code Changes

1. **Run unit tests** first (fast feedback):
   ```bash
   python tests/integration/test_sla_monitoring.py
   ```

2. **If tests pass**, run live check:
   ```bash
   python scripts/core/sla_check_working.py --no-slack
   ```

3. **Compare results** with expected behavior

4. **Deploy if satisfied**

---

## Test Coverage

### What's Tested

✅ **QA SLA Monitoring**
- Detects tickets in "In QA", "QA", "Ready for QA" statuses
- 24-hour threshold enforcement
- Warning severity (24-48h)
- Critical severity (> 48h)

✅ **Pending Approval SLA**
- Detects tickets in "Pending Approval" status
- 48-hour threshold enforcement
- Warning severity (48-72h)
- Critical severity (> 72h)

✅ **Blocked Ticket SLA**
- Detects tickets with "Blocked" status
- Detects tickets with "blocked" label
- 24-hour threshold enforcement
- Warning/critical severity levels

✅ **PR Review SLA**
- Detects open PRs without recent reviews
- 24-48 hour threshold enforcement
- Stale PR detection

✅ **Alert Deduplication**
- 24-hour cooldown between same alerts
- Escalation increase triggers new alert
- Different violation types tracked separately
- Thread tracking for follow-up

✅ **Error Handling**
- Jira search failures (timeout, connection)
- Invalid ticket data
- Missing fields

### What's NOT Tested

❌ **Slack API Integration**
- Actual message posting (requires Slack API)
- Thread creation/updates
- User mentions

❌ **Jira API Write Operations**
- Comment posting
- Status transitions
- Field updates

**Rationale:** These are tested manually in staging or via integration tests with test Slack/Jira instances

---

## Interpreting Results

### Successful Test Run

```
🎉 ALL TESTS PASSED!

The SLA monitoring system is working correctly:
  ✅ QA violations detected (24h threshold)
  ✅ Pending Approval violations detected (48h threshold)
  ✅ Blocked ticket violations detected (24h threshold)
  ✅ Severity levels correct (warning vs critical)
  ✅ No false positives
  ✅ Error handling works
```

**Next step:** Run live check with `--no-slack` to verify real data

### Failed Test Run

```
❌ FAILED: QA Violations (24h)
   Error: Expected 3 violations, got 4
```

**What to do:**
1. Check if test expectations are wrong (timestamps, thresholds)
2. Check if code logic changed (SLA thresholds, status names)
3. Review recent commits to `scripts/core/sla_check_working.py`
4. Fix either test or code, re-run

### Live Check with Violations

```
📋 Checking Jira SLAs...
   Found 2 Jira violations

   ⚠️  ECD-585: In QA for 36.0h without update (SLA: 24h)
```

**What to do:**
1. **Review violation** - is it legitimate?
2. **Check ticket** - has there been recent activity?
3. **If legitimate** - SLA enforcement working correctly!
4. **If false positive** - adjust SLA thresholds or status logic

---

## Common Issues

### Issue: Timestamp Offset in Tests

**Symptom:** Test expects 20h but sees 26h (6h offset)

**Cause:** Timezone handling differences

**Fix:** Use safe margins in test data (e.g., 12h instead of 20h for "within SLA" tests)

### Issue: Module Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'src.tools.jira'
```

**Cause:** Running from wrong directory

**Fix:**
```bash
cd /Users/ethand320/code/citemed/project-manager
python tests/integration/test_sla_monitoring.py
```

### Issue: Database Lock

**Symptom:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Another process using `slack_state.db`

**Fix:**
```bash
# Find process
lsof | grep slack_state.db

# Kill process
kill <PID>

# Or just wait for it to finish
```

---

## Performance Benchmarks

**Unit Tests:**
- Execution time: ~2 seconds
- Tickets tested: 30 mock tickets
- API calls: 0 (mocked)

**Live Check (--no-slack):**
- Execution time: ~5-10 seconds
- Tickets checked: 100+ real tickets
- PRs checked: 10+ real PRs
- Jira API calls: 1 (search query)
- Bitbucket API calls: 2-3 (repo + PR details)

**Deduplication Test:**
- Execution time: <1 second
- Database writes: 3-4 records
- Slack API calls: 0

---

## Continuous Integration

### pytest Integration

Add to `pyproject.toml` or `pytest.ini`:
```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

**Run via pytest:**
```bash
pytest tests/integration/test_sla_monitoring.py -v
```

### GitHub Actions Example

```yaml
name: SLA Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python tests/integration/test_sla_monitoring.py
      - run: python tests/integration/test_sla_deduplication.py
```

---

## Summary

**For quick validation:**
```bash
python tests/integration/test_sla_monitoring.py
```

**For real data check:**
```bash
python scripts/core/sla_check_working.py --no-slack
```

**For deduplication validation:**
```bash
python tests/integration/test_sla_deduplication.py
```

All three tests are **dry-run by design** - they will NOT post to Slack or Jira.

---

**Ready for production?**
1. ✅ All unit tests pass
2. ✅ Live check shows expected violations
3. ✅ Deduplication logic verified
4. ✅ No false positives observed

Then remove the `--no-slack` flag and deploy!
