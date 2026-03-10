# QA SLA Dashboard & Monitoring System - Proposal

**Date:** 2026-02-12
**Author:** PM Agent + Ethan
**Status:** Proposal / Design Phase

---

## 📋 CURRENT STATE SUMMARY

### ✅ What We Built Today (Phase 1 Complete)

1. **Accurate QA SLA Monitoring**
   - 24-hour QA status threshold
   - Uses status history (not "updated" timestamp)
   - Scheduled hourly checks
   - Dedicated Slack channel routing (`#ecd-qa-alerts`)

2. **Test Quality Assessment Framework**
   - SOP-based evaluation criteria
   - Scoring system (0-10)
   - PR comment analysis
   - Ready for integration

### 🎯 User Requirement

> "I want to work on some kind of frontend for this (or better log files) so I can see what's going on with this thing and what SLAs are scheduled, and which have run (and when), and be able to run one-offs of any check we have registered so far."

---

## 🏗️ PROPOSED SOLUTION: WEB DASHBOARD

### Tech Stack (Recommended)

**Backend:**
- FastAPI (already in stack)
- SQLite database (check history, configuration)
- Current check scripts (no rewrite needed)

**Frontend:**
- **Option A (Recommended):** HTMX + Alpine.js
  - Server-rendered templates
  - Minimal JavaScript
  - Fast to build
  - Easy to maintain

- **Option B:** React + TypeScript
  - Richer UI interactions
  - More complex setup
  - Better for future scaling

### Dashboard Features (MVP)

#### 1. **Home Dashboard** `/`

```
╔═══════════════════════════════════════════════════════════╗
║ 🤖 PM Agent Dashboard              Last Updated: 2m ago  ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║ ⏰ ACTIVE MONITORS                       [Refresh]        ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ ✅ SLA Check (Hourly)                              │   ║
║ │    Status: Running                                 │   ║
║ │    Last: 2 mins ago | Next: 58 mins                │   ║
║ │    Result: 16 violations (7 critical)              │   ║
║ │    [View Details] [Run Now] [View Logs]            │   ║
║ ├────────────────────────────────────────────────────┤   ║
║ │ ✅ Daily Standup (9am weekdays)                    │   ║
║ │    Last: Today 9:00am | Next: Tomorrow 9:00am      │   ║
║ │    [View Results] [Run Now]                        │   ║
║ ├────────────────────────────────────────────────────┤   ║
║ │ 🆕 Test Quality Validation                         │   ║
║ │    Status: Not configured                          │   ║
║ │    [Configure] [Enable]                            │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ 📊 CURRENT VIOLATIONS BY TYPE                             ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ Type              │ Count │ Critical │ Warning     │   ║
║ │──────────────────┼───────┼──────────┼─────────────│   ║
║ │ QA Stale         │   7   │    5     │     2       │   ║
║ │ Pending Approval │   3   │    2     │     1       │   ║
║ │ Blocked Tickets  │   4   │    0     │     4       │   ║
║ │ Stale PRs        │   2   │    0     │     2       │   ║
║ │──────────────────┼───────┼──────────┼─────────────│   ║
║ │ TOTAL            │  16   │    7     │     9       │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ 🔥 TOP VIOLATIONS (Most Overdue)                          ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ ⚠️ ECD-917 | In QA 661.3h (27.6 days)             │   ║
║ │    Optimize ArticlesAPIView Performance...         │   ║
║ │    Owner: ahmed ben | Posted: 2 mins ago           │   ║
║ │    [View Ticket] [Slack Thread] [Escalate]         │   ║
║ ├────────────────────────────────────────────────────┤   ║
║ │ ⚠️ ECD-924 | In QA 542.7h (22.6 days)             │   ║
║ │    Integration: AI Abstract Extraction...          │   ║
║ │    [View Ticket] [Slack Thread]                    │   ║
║ └────────────────────────────────────────────────────┘   ║
╚═══════════════════════════════════════════════════════════╝
```

#### 2. **Check History** `/history`

```
╔═══════════════════════════════════════════════════════════╗
║ 📊 Check Execution History              [Export CSV]      ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║ Filter: [All Checks ▼] [Last 7 Days ▼]        [Search]    ║
║                                                            ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ Date/Time      │Check Type│Violations│Duration│Status│  ║
║ │────────────────┼──────────┼──────────┼────────┼──────│  ║
║ │ 2/12 19:00     │SLA Check │   16     │  45s   │ ✅   │  ║
║ │ 2/12 18:00     │SLA Check │   16     │  43s   │ ✅   │  ║
║ │ 2/12 17:00     │SLA Check │   15     │  42s   │ ✅   │  ║
║ │ 2/12 16:00     │SLA Check │   15     │  44s   │ ✅   │  ║
║ │ 2/12 09:00     │Standup   │   N/A    │  2m3s  │ ✅   │  ║
║ │ 2/11 19:00     │SLA Check │   14     │  41s   │ ✅   │  ║
║ │ 2/11 18:00     │SLA Check │   14     │  46s   │ ❌   │  ║
║ │────────────────┴──────────┴──────────┴────────┴──────│  ║
║ │                    [Load More]                        │  ║
║ └────────────────────────────────────────────────────────┘ ║
╚═══════════════════════════════════════════════════════════╝
```

#### 3. **Manual Check Runner** `/run-check`

```
╔═══════════════════════════════════════════════════════════╗
║ 🔧 Run Manual Check                                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║ Select Check Type:                                        ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ ⚪ Full SLA Check (recommended)                     │   ║
║ │    Checks: QA, PR Review, Blocked, Pending Approval│   ║
║ │    Est. Duration: ~45s                             │   ║
║ │                                                     │   ║
║ │ ⚪ QA SLA Only                                      │   ║
║ │    Checks: Tickets in QA > 24h                     │   ║
║ │    Est. Duration: ~15s                             │   ║
║ │                                                     │   ║
║ │ ⚪ PR Review SLA Only                               │   ║
║ │    Checks: Open PRs without review                 │   ║
║ │    Est. Duration: ~20s                             │   ║
║ │                                                     │   ║
║ │ ⚪ Test Quality Validation (NEW)                    │   ║
║ │    Checks: Test cases for QA tickets               │   ║
║ │    Est. Duration: ~2m                              │   ║
║ │                                                     │   ║
║ │ ⚪ Daily Standup                                    │   ║
║ │    Full standup workflow                           │   ║
║ │    Est. Duration: ~5m                              │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ Options:                                                  ║
║ ☑ Post results to Slack                                  ║
║ ☐ Dry run (skip notifications)                           ║
║ ☐ Verbose logging                                        ║
║                                                            ║
║ [Run Check]  [Schedule for Later]  [Cancel]              ║
╚═══════════════════════════════════════════════════════════╝
```

#### 4. **Violation Details** `/violations/<id>`

```
╔═══════════════════════════════════════════════════════════╗
║ 📋 Violation Details: ECD-917                             ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║ Ticket: ECD-917                           Status: In QA   ║
║ Optimize ArticlesAPIView Performance...                   ║
║                                                            ║
║ ⚠️ CRITICAL VIOLATION                                     ║
║ Type: QA Stale (24h SLA)                                  ║
║ Time in QA: 661.3 hours (27.6 days)                       ║
║ Hours Overdue: 637.3 hours                                ║
║                                                            ║
║ Owner: ahmed ben                                          ║
║ Assignee: ahmed ben                                       ║
║                                                            ║
║ Timeline:                                                 ║
║ • Entered QA: Jan 16, 2026 10:30am                        ║
║ • SLA Deadline: Jan 17, 2026 10:30am                      ║
║ • First Alert: Jan 18, 2026 9:00am                        ║
║ • Escalated: Jan 20, 2026 (Level 3)                       ║
║                                                            ║
║ Slack Threads:                                            ║
║ • #ecd-qa-alerts: [Thread] (5 replies)                    ║
║                                                            ║
║ Actions:                                                  ║
║ [View Jira Ticket] [View Slack Thread] [Escalate] [Snooze]║
╚═══════════════════════════════════════════════════════════╝
```

#### 5. **Configuration** `/config`

```
╔═══════════════════════════════════════════════════════════╗
║ ⚙️ System Configuration                                   ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║ SLA Thresholds:                                           ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ QA Status:         [24] hours                       │   ║
║ │ Pending Approval:  [48] hours                       │   ║
║ │ PR Review:         [48] hours                       │   ║
║ │ Blocked Tickets:   [24] hours (no update)           │   ║
║ │ PR Staleness:      [48] hours (no commits)          │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ Slack Channels:                                           ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ QA Alerts:     #ecd-qa-alerts (C033XHDJ708)         │   ║
║ │ Standup:       #ecd-standup (C02NW7QN1RN)           │   ║
║ │ Agent Logs:    #pm-agent-logs (C09S3K9SK0T)         │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ Schedule:                                                 ║
║ ┌────────────────────────────────────────────────────┐   ║
║ │ SLA Check:    Every hour (9am-5pm weekdays)         │   ║
║ │ Standup:      9:00am (Mon-Fri)                      │   ║
║ │ Heartbeat:    Every hour                            │   ║
║ └────────────────────────────────────────────────────┘   ║
║                                                            ║
║ [Save Changes]  [Reset to Defaults]                      ║
╚═══════════════════════════════════════════════════════════╝
```

---

## 🗃️ DATABASE SCHEMA

```sql
-- Check execution history
CREATE TABLE check_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type VARCHAR(50) NOT NULL,  -- 'sla_check', 'standup', 'test_quality'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20),  -- 'success', 'failed', 'running'
    violations_found INTEGER,
    critical_count INTEGER,
    warning_count INTEGER,
    output_json TEXT,  -- Full check results
    error_message TEXT
);

-- Current violations (active SLA breaches)
CREATE TABLE active_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id VARCHAR(50) NOT NULL,  -- 'ECD-123', 'PR-456'
    violation_type VARCHAR(50) NOT NULL,  -- 'qa_stale', 'pending_approval', etc.
    severity VARCHAR(20),  -- 'critical', 'warning'
    detected_at TIMESTAMP NOT NULL,
    hours_overdue REAL,
    owner VARCHAR(100),
    slack_thread_ts VARCHAR(50),
    escalation_level INTEGER DEFAULT 1,
    resolved_at TIMESTAMP,
    metadata JSON
);

-- Check schedules
CREATE TABLE check_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type VARCHAR(50) NOT NULL,
    schedule_expression VARCHAR(100),  -- 'hourly', 'daily_9am', 'manual'
    enabled BOOLEAN DEFAULT 1,
    last_run TIMESTAMP,
    next_run TIMESTAMP
);
```

---

## 🛠️ IMPLEMENTATION PLAN

### Phase 1: Data Layer (1-2 hours)
1. ✅ Create SQLite database schema
2. ✅ Add logging to check scripts (`sla_check_working.py`, etc.)
3. ✅ Create database models (`src/database/check_history.py`)

### Phase 2: API Layer (2-3 hours)
1. ✅ FastAPI app setup (`src/api/dashboard.py`)
2. ✅ REST endpoints:
   - `GET /api/checks` - List all check types
   - `GET /api/checks/history` - Check execution history
   - `GET /api/violations` - Active violations
   - `POST /api/checks/run` - Trigger manual check
   - `GET /api/config` - Get configuration
   - `PUT /api/config` - Update configuration

### Phase 3: Frontend (3-4 hours)
1. ✅ Flask templates with HTMX
2. ✅ Dashboard UI (home page)
3. ✅ Check history view
4. ✅ Manual check runner
5. ✅ Configuration page

### Phase 4: Integration (1 hour)
1. ✅ Update `clock.py` to log to database
2. ✅ Update check scripts to save results
3. ✅ Deploy alongside `pm_agent_service.py`

**Total Estimated Time:** 7-10 hours

---

## 🚀 DEPLOYMENT

### Local Development
```bash
# Start dashboard server
python src/api/dashboard.py

# Access at: http://localhost:8080
```

### Production (Heroku)
```yaml
# Procfile
web: gunicorn src.api.dashboard:app --bind 0.0.0.0:$PORT
worker: python src/pm_agent_service.py
clock: python clock.py
```

---

## ❓ QUESTIONS FOR USER

1. **Tech Stack Preference:**
   - ✅ Flask/HTMX (faster, simpler)
   - ⬜ React (richer, more complex)

2. **MVP Features Priority:**
   - Which features are must-have for v1?
   - Which can wait for v2?

3. **Authentication:**
   - Dashboard public (Heroku internal only)?
   - Or add simple auth (username/password)?

4. **Deployment:**
   - Run on same Heroku dyno as PM agent?
   - Or separate dyno for dashboard?

---

## 📝 NEXT STEPS

**Option A: Build Dashboard First** (Recommended)
- Get visibility into what's running
- Debug SLA checks easier
- Then add test quality validation

**Option B: Complete Test Validation First**
- Finish test quality validator
- Integrate Qase MCP
- Dashboard comes after

**Which path do you prefer?**
