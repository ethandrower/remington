# PM Agent Dashboard - Setup Guide

**Simple Flask + Vue.js dashboard for monitoring PM agent checks**

---

## 🎯 What It Does

The dashboard provides:
- ✅ Real-time view of active SLA violations
- ✅ Check execution history
- ✅ Scheduled check status
- ✅ Manual one-off check execution
- ✅ Violation resolution tracking

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Flask should already be installed from requirements.txt
pip install Flask flask-cors
```

### 2. Start Dashboard

```bash
# Simple startup script
./start_dashboard.sh

# Or manually
python src/dashboard/app.py

# Custom port
DASHBOARD_PORT=5000 python src/dashboard/app.py
```

### 3. Access Dashboard

Open your browser to:
```
http://localhost:8080
```

---

## 📊 Features

### Home Dashboard
- **Stats Cards:** Total violations, critical count, warnings, last check
- **Violation List:** Filterable by type (QA, Pending Approval, Blocked, PRs)
- **Actions:** View Jira ticket, mark as resolved

### Scheduled Checks
- **View schedules:** See all configured checks and their frequency
- **Run manually:** Trigger any check on-demand
- **Check status:** See when each check last ran

### Check History
- **Execution log:** All check runs with timestamps
- **Performance:** Duration and violation counts
- **Status:** Success/failed indicators
- **Trigger source:** Scheduled vs manual

---

## 🔌 API Endpoints

### Dashboard API

```bash
# Get statistics
GET /api/stats

# Get active violations
GET /api/violations
GET /api/violations?type=qa_stale

# Resolve violation
POST /api/violations/{item_id}/resolve

# Get check history
GET /api/checks/history
GET /api/checks/history?type=sla-check&limit=50

# Get latest check
GET /api/checks/latest/{check_type}

# Get schedules
GET /api/checks/schedules

# Run manual check
POST /api/checks/run
{
  "check_type": "sla-check",
  "dry_run": false
}
```

---

## 🗄️ Database

**Location:** `.claude/data/bot-state/dashboard.db`

**Tables:**
- `check_runs` - Check execution history
- `active_violations` - Current SLA violations
- `check_schedules` - Configured check schedules

**Auto-initialized** on first run.

---

## 🔗 Integration with Existing Checks

The dashboard automatically integrates with:

1. **SLA Check** (`scripts/core/sla_check_working.py`)
   - Logs execution history
   - Stores violation data
   - Tracks resolution

2. **Daily Standup** (`run_agent.py standup`)
   - Execution tracking
   - Performance metrics

3. **Scheduler** (`clock.py`)
   - Reads check schedules
   - Updates last run timestamps

---

## 🎨 Technology Stack

- **Backend:** Flask (Python 3.9+)
- **Frontend:** Vue.js 3 (CDN, no build step)
- **CSS:** Bootstrap 5
- **Database:** SQLite
- **Icons:** Bootstrap Icons

---

## 🚢 Deployment

### Heroku (Production)

Add to `Procfile`:
```
web: gunicorn src.dashboard.app:app --bind 0.0.0.0:$PORT
```

Or run separately:
```
dashboard: python src/dashboard/app.py
```

### Environment Variables

```bash
DASHBOARD_PORT=8080  # Default: 8080
```

---

## 🛠️ Development

### Running Locally

```bash
# Terminal 1: Start dashboard
./start_dashboard.sh

# Terminal 2: Run PM agent service (optional)
python src/pm_agent_service.py

# Terminal 3: Run scheduler (optional)
python clock.py
```

### Adding New Check Types

1. **Add to database:**
```python
from src.database.dashboard_db import get_dashboard_db

db = get_dashboard_db()
db.upsert_schedule(
    'my-check',
    'daily at 2pm',
    'My custom check description'
)
```

2. **Add to run_agent.py:**
```python
def run_my_check(args):
    # Log start
    run_id = db.log_check_start('my-check', 'manual')

    # Run check logic
    # ...

    # Log completion
    db.log_check_complete(run_id, violations_found=count)
```

3. **Update frontend:**
- Check type will automatically appear in schedules
- Add to `formatCheckType()` in `templates/dashboard.html`

---

## 📖 Usage Examples

### View Active Violations

1. Go to dashboard
2. Click "Active Violations" tab
3. Filter by type (e.g., "QA Stale")
4. Click "Jira" to view ticket
5. Click "Resolve" when fixed

### Run Manual Check

**Method 1: From Dashboard**
1. Click "Run Check" button
2. Select check type
3. Toggle "Dry run" if needed
4. Click "Run Check"

**Method 2: From Schedules Tab**
1. Go to "Scheduled Checks"
2. Find the check
3. Click "Run Now"

### Check Execution History

1. Go to "Check History" tab
2. View all recent check runs
3. See duration, violations, status
4. Identify patterns (e.g., checks always failing)

---

## 🐛 Troubleshooting

### Dashboard won't start

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```bash
pip install Flask flask-cors
```

### No data showing

**Cause:** No checks have run yet

**Fix:**
```bash
# Run SLA check manually
python run_agent.py sla-check --dry-run

# Or from dashboard: Click "Run Check"
```

### Database locked error

**Cause:** Multiple processes accessing database

**Fix:**
```bash
# Stop all PM agent processes
pkill -f pm_agent_service
pkill -f clock.py

# Restart dashboard
./start_dashboard.sh
```

---

## 🎯 Roadmap

**Implemented:**
- ✅ Real-time violation dashboard
- ✅ Check execution history
- ✅ Manual check runner
- ✅ Scheduled check viewer

**Planned:**
- ⬜ Charts and graphs (violation trends)
- ⬜ Email/Slack alerts from dashboard
- ⬜ Custom alert thresholds
- ⬜ Multi-user authentication
- ⬜ Export reports (CSV, PDF)

---

## 📞 Support

**Issues?** Check the logs:
```bash
# Dashboard logs (in terminal)
# Check output when running ./start_dashboard.sh

# PM agent logs
tail -f .claude/data/bot-state/activity.log
```

**Need help?** Open an issue in the project repository.
