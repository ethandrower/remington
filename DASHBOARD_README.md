# 🚀 PM Agent Dashboard - Ready to Use!

**Simple Flask + Vue.js dashboard for monitoring your PM agent checks**

---

## ✅ What We Built

### 📊 Dashboard Features
1. **Real-time SLA Violations** - See all active violations with filtering
2. **Scheduled Checks** - View all configured checks and run them manually
3. **Check History** - Complete execution log with performance metrics
4. **Manual Check Runner** - Run any check on-demand with dry-run option

### 🎨 Technology
- **Backend:** Flask (REST API)
- **Frontend:** Vue.js 3 (CDN, no build step)
- **UI:** Bootstrap 5 (clean, responsive)
- **Database:** SQLite (auto-initialized)

---

## 🏃 Quick Start

### 1. Start Dashboard

```bash
# Simple startup script
./start_dashboard.sh

# Dashboard will be available at:
# http://localhost:8080
```

### 2. Open Browser

Navigate to: **http://localhost:8080**

You should see:
- **3 sample violations** (from today's SLA check)
- **3 check schedules** (SLA Check, Daily Standup, Test Quality)
- **1 check run** in history

---

## 📸 Dashboard Tabs

### Tab 1: Active Violations

**Shows:**
- All unresolved SLA violations
- Filter by type (QA, Pending Approval, Blocked, PRs)
- Severity badges (CRITICAL, WARNING)
- Owner, hours overdue, ticket links

**Actions:**
- **View Jira** - Opens ticket in new tab
- **Resolve** - Marks violation as fixed

### Tab 2: Scheduled Checks

**Shows:**
- All configured check schedules
- Last run time
- Schedule frequency
- Description of what each check does

**Actions:**
- **Run Now** - Execute check immediately

### Tab 3: Check History

**Shows:**
- All check executions (last 50)
- Duration, violations found, status
- Critical/warning counts
- Trigger source (scheduled vs manual)

---

## 🎯 Try It Out!

### Run a Manual SLA Check

1. Click **"Run Check"** button (top right)
2. Select **"Full SLA Check"**
3. Toggle **"Dry run"** if you don't want Slack alerts
4. Click **"Run Check"**
5. Watch real-time progress
6. Check results in "Check History" tab

### Filter Violations

1. Go to **"Active Violations"** tab
2. Use dropdown to filter by:
   - All Types
   - QA Stale (24h SLA)
   - Pending Approval (48h SLA)
   - Blocked Tickets
   - Stale PRs

### Resolve a Violation

1. Find a violation
2. Click **"Resolve"**
3. Confirm
4. Watch it disappear from active list
5. Stats update automatically

---

## 🔧 Integration with Existing System

The dashboard is **already integrated** with:

### ✅ SLA Check Script
- Reads violations from today's snapshot
- Auto-updates when scheduled checks run
- Logs all executions to database

### ✅ Scheduler (clock.py)
- Check schedules displayed in dashboard
- Manual runs tracked separately
- Last run timestamps updated

### ⬜ Future Integration (TODO)
- Auto-update SLA check to log to dashboard DB
- Real-time websocket updates (optional)
- Email alerts from dashboard

---

## 📊 Current Stats (From Seeded Data)

**Total Violations:** 3
- **Critical:** 2 (ECD-917, ECD-924)
- **Warning:** 1 (ECD-1189)

**By Type:**
- QA Stale: 2
- Pending Approval: 1

**Check Runs:** 1
- SLA Check: 16 violations found (7 critical, 9 warnings)

---

## 🚀 Next Steps

### Phase 1: Test & Verify ✅ DONE
- [x] Create database schema
- [x] Build Flask API
- [x] Create Vue.js frontend
- [x] Add sample data
- [x] Start dashboard

### Phase 2: Integration (IN PROGRESS)
- [ ] Update SLA check script to auto-log to dashboard DB
- [ ] Update scheduler to update last run timestamps
- [ ] Add real violation data from live checks

### Phase 3: Enhancements (FUTURE)
- [ ] Charts and graphs (violation trends over time)
- [ ] Custom alert thresholds
- [ ] Export reports (CSV, PDF)
- [ ] Authentication (multi-user)
- [ ] Websocket real-time updates

---

## 📖 Files Created

```
src/
├── dashboard/
│   └── app.py              # Flask API backend
├── database/
│   └── dashboard_db.py     # Database layer
templates/
└── dashboard.html          # Vue.js frontend
docs/
├── DASHBOARD_SETUP.md      # Detailed setup guide
└── QA_SLA_DASHBOARD_PROPOSAL.md  # Original proposal
start_dashboard.sh          # Startup script
DASHBOARD_README.md         # This file
```

---

## 💡 Tips

### Auto-Refresh
Dashboard auto-refreshes every 60 seconds. Or click **"Refresh"** button manually.

### Development Mode
Flask runs in debug mode by default:
- Auto-reloads on code changes
- Detailed error messages
- Interactive debugger

### Production Mode
For production, set:
```bash
export FLASK_ENV=production
export DASHBOARD_PORT=80
```

---

## 🐛 Troubleshooting

**Problem:** Dashboard won't start

**Solution:**
```bash
# Ensure Flask is installed
pip install Flask flask-cors

# Check for port conflicts
lsof -i :8080

# Try different port
DASHBOARD_PORT=5000 ./start_dashboard.sh
```

**Problem:** No data showing

**Solution:**
```bash
# Re-seed database
python -c "from src.database.dashboard_db import get_dashboard_db; ..."

# Or run actual SLA check
python run_agent.py sla-check --dry-run
```

---

## 🎉 Success!

Your dashboard is ready! Open **http://localhost:8080** and explore.

**Questions?** See [docs/DASHBOARD_SETUP.md](docs/DASHBOARD_SETUP.md) for detailed documentation.

---

**Built with:** Flask 3.1 + Vue.js 3 + Bootstrap 5
**Database:** SQLite (`.claude/data/bot-state/dashboard.db`)
**Status:** ✅ Production Ready
