# Scheduling Setup Guide - Autonomous PM Agent

**Date:** 2025-10-29
**Status:** Ready for deployment

This guide explains how to set up automated scheduling for the Project Manager agent to run daily standups and hourly SLA checks.

---

## Quick Start Commands

```bash
# Test standup locally (dry-run)
python run_agent.py standup --dry-run

# Test SLA check locally (dry-run)
python run_agent.py sla-check --no-slack

# Run standup for real (posts to Slack)
python run_agent.py standup

# Run SLA check for real (posts to Slack, Jira, creates threads)
python run_agent.py sla-check
```

---

## Option 1: Cron (Simplest - Local/Server)

### Setup Steps

1. **Make run_agent.py executable:**
```bash
chmod +x /Users/ethand320/code/citemed/project-manager/run_agent.py
```

2. **Edit crontab:**
```bash
crontab -e
```

3. **Add cron jobs:**
```bash
# Daily standup at 9 AM ET (weekdays only)
0 9 * * 1-5 cd /Users/ethand320/code/citemed/project-manager && python run_agent.py standup >> /tmp/pm-agent-standup.log 2>&1

# Hourly SLA checks during business hours (9 AM - 5 PM ET, weekdays)
0 9-17 * * 1-5 cd /Users/ethand320/code/citemed/project-manager && python run_agent.py sla-check >> /tmp/pm-agent-sla.log 2>&1

# Alternative: SLA check every 2 hours
0 9,11,13,15,17 * * 1-5 cd /Users/ethand320/code/citemed/project-manager && python run_agent.py sla-check >> /tmp/pm-agent-sla.log 2>&1
```

4. **Verify cron jobs:**
```bash
crontab -l
```

5. **Monitor logs:**
```bash
# Watch standup logs
tail -f /tmp/pm-agent-standup.log

# Watch SLA logs
tail -f /tmp/pm-agent-sla.log
```

### Pros
- ✅ Simple, no additional infrastructure
- ✅ Built into macOS/Linux
- ✅ Easy to debug locally

### Cons
- ❌ Requires machine to be running 24/7
- ❌ No automatic restart on failure
- ❌ Manual log management

---

## Option 2: Heroku (Recommended - Cloud Deployment)

### Setup Steps

#### 1. Create Heroku App
```bash
# Install Heroku CLI first
brew install heroku/brew/heroku

# Login to Heroku
heroku login

# Create app
cd /Users/ethand320/code/citemed/project-manager
heroku create citemed-pm-agent

# Add Python buildpack
heroku buildpacks:set heroku/python
```

#### 2. Set Environment Variables
```bash
# Copy all vars from .env to Heroku config
heroku config:set ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="ATSTT3..."
heroku config:set SLACK_BOT_TOKEN="xoxb-..."
heroku config:set SLACK_CHANNEL_STANDUP="C02NW7QN1RN"

# Add developer account IDs
heroku config:set DEVELOPER_MOHAMED_JIRA="712020:27a3f2fe-9037-455d-9392-fb80ba1705c0"
heroku config:set DEVELOPER_AHMED_JIRA="5f1879a11a26ad00147b315c"
heroku config:set DEVELOPER_THANH_JIRA="712020:537b192d-bb7e-4ae4-8c4e-9663ff2a22c8"
heroku config:set DEVELOPER_JOSH_JIRA="627138d602e1c10069bc8bde"

# Set business hours
heroku config:set BUSINESS_HOURS_START=9
heroku config:set BUSINESS_HOURS_END=17
heroku config:set BUSINESS_TIMEZONE="America/New_York"
```

#### 3. Create Clock Worker (APScheduler)

Create `clock.py`:
```python
#!/usr/bin/env python3
"""
Heroku Clock Worker - Scheduled Task Runner
Uses APScheduler to run standup and SLA checks on schedule
"""

from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_standup():
    """Run daily standup workflow"""
    print("⏰ Running scheduled standup...")
    try:
        subprocess.run(
            [sys.executable, "run_agent.py", "standup"],
            cwd=PROJECT_ROOT,
            check=True
        )
        print("✅ Standup completed")
    except Exception as e:
        print(f"❌ Standup failed: {e}")


def run_sla_check():
    """Run SLA compliance check"""
    print("⏰ Running scheduled SLA check...")
    try:
        subprocess.run(
            [sys.executable, "run_agent.py", "sla-check"],
            cwd=PROJECT_ROOT
        )
        print("✅ SLA check completed")
    except Exception as e:
        print(f"❌ SLA check failed: {e}")


def main():
    print("🚀 CiteMed PM Agent - Clock Worker Starting")

    scheduler = BlockingScheduler(timezone="America/New_York")

    # Daily standup at 9 AM ET (weekdays)
    scheduler.add_job(
        run_standup,
        'cron',
        hour=9,
        minute=0,
        day_of_week='mon-fri',
        id='daily_standup'
    )

    # Hourly SLA checks during business hours (9 AM - 5 PM ET, weekdays)
    scheduler.add_job(
        run_sla_check,
        'cron',
        hour='9-17',
        minute=0,
        day_of_week='mon-fri',
        id='hourly_sla_check'
    )

    print("📅 Scheduled Jobs:")
    for job in scheduler.get_jobs():
        print(f"  • {job.id}: {job.next_run_time}")

    print("\n✅ Scheduler started")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Scheduler stopped")


if __name__ == "__main__":
    main()
```

#### 4. Update requirements.txt
Add APScheduler:
```bash
echo "APScheduler==3.10.4" >> requirements.txt
```

#### 5. Create Procfile
```bash
echo "clock: python clock.py" > Procfile
```

#### 6. Deploy to Heroku
```bash
git add .
git commit -m "Add Heroku clock worker for scheduled jobs"
git push heroku main

# Scale up the clock worker (this costs $7/month for hobby dyno)
heroku ps:scale clock=1
```

#### 7. Monitor on Heroku
```bash
# View logs
heroku logs --tail --source clock

# Check dyno status
heroku ps

# Restart if needed
heroku restart
```

### Pros
- ✅ Cloud-hosted, runs 24/7
- ✅ Automatic restart on failure
- ✅ Easy deployment via git
- ✅ Built-in logging dashboard
- ✅ Scale up/down easily

### Cons
- ❌ Costs $7/month (hobby dyno)
- ❌ Requires git-based deployment
- ❌ Heroku-specific configuration

---

## Option 3: GitHub Actions (Free Alternative)

### Setup Steps

Create `.github/workflows/pm-agent-scheduler.yml`:

```yaml
name: PM Agent Scheduler

on:
  schedule:
    # Daily standup at 9 AM ET = 2 PM UTC (weekdays)
    - cron: '0 14 * * 1-5'

    # SLA checks every 2 hours during business hours
    # 9 AM, 11 AM, 1 PM, 3 PM, 5 PM ET = 2 PM, 4 PM, 6 PM, 8 PM, 10 PM UTC
    - cron: '0 14,16,18,20,22 * * 1-5'

  workflow_dispatch:  # Allow manual triggering

jobs:
  run-standup:
    if: github.event.schedule == '0 14 * * 1-5'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily standup
        env:
          ATLASSIAN_CLOUD_ID: ${{ secrets.ATLASSIAN_CLOUD_ID }}
          ATLASSIAN_SERVICE_ACCOUNT_TOKEN: ${{ secrets.ATLASSIAN_SERVICE_ACCOUNT_TOKEN }}
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_STANDUP: ${{ secrets.SLACK_CHANNEL_STANDUP }}
          DEVELOPER_MOHAMED_JIRA: ${{ secrets.DEVELOPER_MOHAMED_JIRA }}
          DEVELOPER_AHMED_JIRA: ${{ secrets.DEVELOPER_AHMED_JIRA }}
          DEVELOPER_THANH_JIRA: ${{ secrets.DEVELOPER_THANH_JIRA }}
          DEVELOPER_JOSH_JIRA: ${{ secrets.DEVELOPER_JOSH_JIRA }}
        run: python run_agent.py standup

  run-sla-check:
    if: github.event.schedule != '0 14 * * 1-5'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run SLA check
        env:
          ATLASSIAN_CLOUD_ID: ${{ secrets.ATLASSIAN_CLOUD_ID }}
          ATLASSIAN_SERVICE_ACCOUNT_TOKEN: ${{ secrets.ATLASSIAN_SERVICE_ACCOUNT_TOKEN }}
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_STANDUP: ${{ secrets.SLACK_CHANNEL_STANDUP }}
          DEVELOPER_MOHAMED_JIRA: ${{ secrets.DEVELOPER_MOHAMED_JIRA }}
          DEVELOPER_AHMED_JIRA: ${{ secrets.DEVELOPER_AHMED_JIRA }}
          DEVELOPER_THANH_JIRA: ${{ secrets.DEVELOPER_THANH_JIRA }}
          DEVELOPER_JOSH_JIRA: ${{ secrets.DEVELOPER_JOSH_JIRA }}
        run: python run_agent.py sla-check
```

Add secrets to GitHub repo settings:
- Settings → Secrets and variables → Actions → New repository secret
- Add all environment variables as secrets

### Pros
- ✅ Completely free
- ✅ Built-in CI/CD
- ✅ Easy to modify schedules
- ✅ Version controlled

### Cons
- ❌ Requires public/private GitHub repo
- ❌ GitHub Actions has usage limits
- ❌ No persistent storage (stateless)

---

## Monitoring & Maintenance

### Check if Automation is Running

```bash
# For cron:
grep "CRON" /var/log/syslog  # Linux
log show --predicate 'eventMessage contains "cron"' --last 1h  # macOS

# For Heroku:
heroku logs --tail --source clock

# For GitHub Actions:
# Check Actions tab in GitHub repo
```

### View Generated Reports

```bash
# Local reports
ls -lh .claude/data/standups/
cat .claude/data/standups/$(date +%Y-%m-%d)-standup.md

# SLA tracking
ls -lh .claude/data/sla-tracking/daily-snapshots/
cat .claude/data/sla-tracking/active-violations.json
```

### Troubleshooting

#### Standup not running?
```bash
# Test manually
python run_agent.py standup --dry-run

# Check logs
tail -f /tmp/pm-agent-standup.log

# Verify environment
python -c "import os; print('SLACK_BOT_TOKEN:', bool(os.getenv('SLACK_BOT_TOKEN')))"
```

#### SLA checks not posting to Jira/Slack?
```bash
# Test manually without posting
python run_agent.py sla-check --no-slack

# Test with posting
python run_agent.py sla-check

# Check permissions
python -c "from sla_escalation import post_jira_comment; print('Module loaded')"
```

#### Heroku dyno not starting?
```bash
# Check logs
heroku logs --tail

# Restart dyno
heroku restart

# Check config
heroku config
```

---

## Recommended Setup

**For Development/Testing:**
- Use **cron** for local testing
- Run `--dry-run` mode to avoid posting

**For Production:**
- Use **Heroku** for 24/7 reliability
- Set up log monitoring
- Weekly review of SLA compliance trends

---

## Next Steps After Setup

1. **Week 1: Monitor**
   - Check logs daily
   - Verify Slack posts appear
   - Confirm Jira comments posted
   - Review SLA violation accuracy

2. **Week 2: Tune**
   - Adjust escalation thresholds if needed
   - Refine violation detection logic
   - Add/remove developers from .env

3. **Week 3: Expand**
   - Add more SLA types (QA turnaround, etc.)
   - Integrate with additional repositories
   - Create weekly trend reports

---

## Cost Breakdown

| Option | Monthly Cost | Reliability | Maintenance |
|--------|-------------|-------------|-------------|
| **Cron** | $0 (requires running machine) | Medium | Manual |
| **Heroku** | $7/month (hobby dyno) | High | Minimal |
| **GitHub Actions** | $0 (within free tier) | Medium | Low |

**Recommendation:** Start with **cron** for testing, migrate to **Heroku** for production.

---

## Support

If scheduling isn't working:
1. Check environment variables are set
2. Verify .claude/data directories exist
3. Test commands manually first
4. Review logs for errors
5. Ensure Slack/Jira tokens are valid

---

**Last Updated:** 2025-10-29
**Status:** Ready for deployment
