# Heroku Deployment Guide

Complete guide for deploying the CiteMed Project Manager autonomous agent to Heroku.

---

## Quick Start (5 minutes)

### Prerequisites

1. **Heroku CLI** - Install: `brew install heroku/brew/heroku`
2. **Git repository** - Ensure code is committed
3. **Credentials ready** - Atlassian API token, Slack bot token

### One-Command Deploy

```bash
# Login to Heroku
heroku login

# Create app
heroku create citemed-pm-agent

# Set environment variables
heroku config:set \
  ATLASSIAN_SERVICE_ACCOUNT_EMAIL="your-email@atlassian.com" \
  ATLASSIAN_SERVICE_ACCOUNT_TOKEN="your_token_here" \
  ATLASSIAN_CLOUD_ID="67bbfd03-b309-414f-9640-908213f80628" \
  SLACK_BOT_TOKEN="xoxb-your-slack-token"

# Deploy
git push heroku main

# Scale worker dyno
heroku ps:scale worker=1

# Check logs
heroku logs --tail
```

---

## Detailed Setup

### Step 1: Create Heroku App

```bash
# Create app with specific name
heroku create citemed-pm-agent --region us

# Or let Heroku generate name
heroku create
```

### Step 2: Configure Add-ons

```bash
# Add scheduler (free)
heroku addons:create scheduler:standard

# Optional: Add Papertrail for log management (free tier)
heroku addons:create papertrail:choklad

# Optional: Add database if needed for future state persistence
# heroku addons:create heroku-postgresql:hobby-dev
```

### Step 3: Set Environment Variables

```bash
# Required: Atlassian credentials
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_EMAIL="remington-cd3wmzelbd@serviceaccount.atlassian.com"
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="YOUR_TOKEN_HERE"
heroku config:set ATLASSIAN_CLOUD_ID="67bbfd03-b309-414f-9640-908213f80628"
heroku config:set ATLASSIAN_PROJECT_KEY="ECD"

# Required: Slack credentials
heroku config:set SLACK_BOT_TOKEN="xoxb-YOUR-TOKEN"
heroku config:set SLACK_CHANNEL_STANDUP="C123ABC456"

# Optional: Configuration
heroku config:set BUSINESS_TIMEZONE="America/New_York"
heroku config:set BUSINESS_HOURS_START="9"
heroku config:set BUSINESS_HOURS_END="17"
heroku config:set DRY_RUN="false"

# View all config
heroku config
```

### Step 4: Deploy Code

```bash
# Add Heroku remote (if not already added)
heroku git:remote -a citemed-pm-agent

# Deploy
git push heroku main

# Or deploy from specific branch
git push heroku your-branch:main
```

### Step 5: Scale Worker Dyno

```bash
# Start worker dyno
heroku ps:scale worker=1

# Check dyno status
heroku ps

# View dyno info
heroku ps:type
```

### Step 6: Configure Scheduled Jobs

The worker dyno runs `clock.py` which handles scheduling automatically. But you can also use Heroku Scheduler for backup/redundancy:

```bash
# Open scheduler dashboard
heroku addons:open scheduler

# Add job via UI:
# - Command: python run_agent.py standup --notify-ethan
# - Frequency: Daily at 9:00 AM (adjust for timezone)
```

**Note:** With `clock.py` running, the Heroku Scheduler is optional. The clock process handles daily standups at 9 AM ET automatically.

---

## Monitoring & Management

### View Logs

```bash
# Tail logs in real-time
heroku logs --tail

# View recent logs
heroku logs -n 500

# Filter logs by dyno
heroku logs --dyno worker

# Search logs
heroku logs --tail | grep "Daily Standup"
```

### Run One-Off Commands

```bash
# Run standup manually
heroku run python run_agent.py standup

# Run SLA check
heroku run python run_agent.py sla-check

# Open Python console
heroku run python

# Run bash shell
heroku run bash
```

### Health Checks

```bash
# Check dyno status
heroku ps

# Check app info
heroku info

# View metrics (requires paid dyno)
heroku metrics
```

### Restart & Scale

```bash
# Restart all dynos
heroku restart

# Restart specific dyno
heroku restart worker.1

# Scale up
heroku ps:scale worker=2

# Scale down (stop)
heroku ps:scale worker=0
```

---

## Cost Breakdown

### Free Tier Option
- **Worker Dyno:** Free (550-1000 hours/month)
- **Scheduler Add-on:** Free
- **Papertrail (logs):** Free tier (50 MB/month)
- **Total:** $0/month

**Limitations:**
- Dyno sleeps after 30 min inactivity (not ideal for scheduled tasks)
- 550 free dyno hours/month (1000 with credit card)

### Recommended: Basic Tier
- **Basic Dyno:** $7/month (never sleeps)
- **Scheduler Add-on:** Free
- **Papertrail:** Free tier
- **Total:** $7/month

**Benefits:**
- Never sleeps (critical for scheduled tasks)
- Better for production use

### Premium Option
- **Standard-1X Dyno:** $25/month
- **Papertrail Standard:** $7/month (1GB logs)
- **Total:** $32/month

**Benefits:**
- Better performance
- More memory (512MB)
- Metrics dashboard

---

## Automatic Deployment from GitHub

### Option 1: Heroku GitHub Integration

1. **Connect GitHub repo:**
   ```bash
   # Via Heroku dashboard: Deploy tab → Connect to GitHub
   ```

2. **Enable automatic deploys:**
   - Choose branch (main)
   - Enable "Wait for CI to pass before deploy" (if using GitHub Actions)
   - Enable "Automatic deploys"

3. **Now every push to main auto-deploys!**

### Option 2: GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: "citemed-pm-agent"
          heroku_email: "your-email@example.com"
```

---

## Environment-Specific Configuration

### Development vs Production

Use separate Heroku apps:

```bash
# Create staging app
heroku create citemed-pm-agent-staging --remote staging

# Create production app
heroku create citemed-pm-agent --remote production

# Deploy to staging
git push staging main

# Deploy to production
git push production main
```

### Config Vars by Environment

```bash
# Set staging-specific vars
heroku config:set DRY_RUN=true --app citemed-pm-agent-staging

# Set production vars
heroku config:set DRY_RUN=false --app citemed-pm-agent
```

---

## Troubleshooting

### Issue: Worker Not Starting

**Check logs:**
```bash
heroku logs --tail
```

**Common causes:**
- Missing dependencies → Check `requirements.txt`
- Python version mismatch → Check `runtime.txt`
- Procfile syntax error → Validate `Procfile`

**Solution:**
```bash
heroku restart worker
```

### Issue: Scheduled Jobs Not Running

**Check clock process:**
```bash
heroku logs --tail | grep "Health check"
```

**Verify timezone:**
```bash
heroku config:get BUSINESS_TIMEZONE
```

**Test manually:**
```bash
heroku run python run_agent.py standup
```

### Issue: Authentication Errors (401)

**Verify credentials:**
```bash
heroku config | grep ATLASSIAN
```

**Test locally first:**
```bash
heroku config:get ATLASSIAN_SERVICE_ACCOUNT_EMAIL
heroku config:get ATLASSIAN_SERVICE_ACCOUNT_TOKEN
```

**Update credentials:**
```bash
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN="new_token"
```

### Issue: Out of Memory

**Check dyno size:**
```bash
heroku ps:type
```

**Upgrade dyno:**
```bash
heroku ps:type standard-1x
```

### Issue: Timeout Errors

**Increase timeout in clock.py:**
```python
timeout=600  # 10 minutes
```

**Or split long-running tasks:**
```bash
# Instead of one big task, break into smaller ones
heroku run python run_agent.py sprint-analyzer
heroku run python run_agent.py sla-monitor
```

---

## Rollback & Recovery

### Rollback to Previous Release

```bash
# View releases
heroku releases

# Rollback to previous version
heroku rollback

# Rollback to specific version
heroku rollback v42
```

### Backup & Restore

```bash
# Backup config vars
heroku config --json > config-backup.json

# Restore config vars
cat config-backup.json | jq -r 'to_entries[] | "\(.key)=\(.value)"' | xargs heroku config:set
```

---

## Security Best Practices

1. **Use service account credentials** - Never use personal API tokens
2. **Rotate tokens regularly** - Update every 90 days
3. **Enable 2FA on Heroku account**
4. **Use Heroku Config Vars** - Never commit secrets to git
5. **Enable audit logging** - Track all config changes
6. **Restrict Heroku access** - Only authorized team members

---

## Performance Optimization

### Reduce Memory Usage

```python
# In run_agent.py, clean up after each task
import gc
gc.collect()
```

### Reduce API Calls

```python
# Cache Jira results
from functools import lru_cache

@lru_cache(maxsize=100)
def get_issue(issue_key):
    # ...
```

### Use Background Jobs

For heavy tasks, consider using background job queues:

```bash
heroku addons:create heroku-redis:hobby-dev
pip install rq  # Redis Queue
```

---

## Monitoring & Alerts

### Heroku Metrics (Paid Dynos)

```bash
heroku metrics --dyno worker
```

### Custom Monitoring

Send metrics to external services:
- **Datadog** - `heroku addons:create datadog`
- **New Relic** - `heroku addons:create newrelic`
- **Sentry** - For error tracking

### Slack Alerts

Already implemented in `clock.py` via `notify_error()`.

---

## Next Steps After Deployment

1. **Test standup workflow:**
   ```bash
   heroku run python run_agent.py standup
   ```

2. **Verify Slack notifications working**

3. **Set up monitoring dashboards**

4. **Document team access procedures**

5. **Schedule weekly review of logs**

6. **Set up PagerDuty or similar for critical alerts**

---

## Commands Cheat Sheet

```bash
# Deploy
git push heroku main

# Logs
heroku logs --tail

# Config
heroku config
heroku config:set KEY=value

# Restart
heroku restart

# Run command
heroku run <command>

# Scale
heroku ps:scale worker=1

# Releases
heroku releases
heroku rollback

# Shell access
heroku run bash

# Open app dashboard
heroku open
heroku addons:open papertrail
heroku addons:open scheduler
```

---

## Support & Resources

- **Heroku Docs:** https://devcenter.heroku.com/
- **Heroku Status:** https://status.heroku.com/
- **Support:** `heroku help` or https://help.heroku.com/

**Internal Resources:**
- `.claude/FUTURE_WORK.md` - Roadmap and improvements
- `run_agent.py` - Main entrypoint
- `clock.py` - Scheduler process
- `BOT_INTEGRATION_SUMMARY.md` - Architecture overview

---

**Last Updated:** 2025-10-21
**Status:** ✅ Ready for deployment
