# Heroku Deployment Guide

## Overview

The CiteMed Project Manager Agent runs on Heroku with **TWO dynos**:

1. **worker** dyno - Real-time polling service (Slack/Jira monitoring)
2. **clock** dyno - Scheduled tasks (daily standup at 9 AM, hourly SLA checks)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Heroku Application                                     │
│                                                          │
│  ┌────────────────────┐      ┌────────────────────┐    │
│  │  Worker Dyno       │      │  Clock Dyno        │    │
│  │  (pm_agent_service)│      │  (clock.py)        │    │
│  ├────────────────────┤      ├────────────────────┤    │
│  │ - Slack polling    │      │ - Daily standup    │    │
│  │   (15s interval)   │      │   (9 AM weekdays)  │    │
│  │ - Jira polling     │      │ - Hourly SLA check │    │
│  │   (backup)         │      │   (business hours) │    │
│  │ - Webhook server   │      │ - Health checks    │    │
│  │   (Jira/Bitbucket) │      │                    │    │
│  │ - Instant responses│      │                    │    │
│  └────────────────────┘      └────────────────────┘    │
│                                                          │
│  Both dynos use Claude Code CLI (installed via npm)     │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Heroku CLI** installed and authenticated
2. **Git repository** with all recent changes committed
3. **Environment variables** ready (see below)

## Deployment Steps

### 1. Create Heroku App (if not exists)

```bash
# Navigate to project directory
cd /Users/ethand320/code/citemed/project-manager

# Create Heroku app
heroku create citemed-pm-agent

# Or use existing app
heroku git:remote -a citemed-pm-agent
```

### 2. Configure Buildpacks

The app requires **TWO buildpacks** (order matters!):

```bash
# Add Node.js buildpack first (for Claude Code CLI)
heroku buildpacks:add --index 1 heroku/nodejs

# Add Python buildpack second
heroku buildpacks:add --index 2 heroku/python

# Verify buildpacks
heroku buildpacks
```

Should output:
```
=== citemed-pm-agent Buildpack URLs
1. heroku/nodejs
2. heroku/python
```

### 3. Set Environment Variables

**Required:**
```bash
heroku config:set ANTHROPIC_API_KEY=your_api_key_here
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_EMAIL=your_email@citemed.com
heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN=your_atlassian_token
heroku config:set SLACK_BOT_TOKEN=xoxb-your-slack-token
heroku config:set SLACK_BOT_USER_ID=U09BVV00XRP
heroku config:set SLACK_CHANNEL_STANDUP=C02NW7QN1RN
```

**Optional (with defaults):**
```bash
heroku config:set ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
heroku config:set ATLASSIAN_PROJECT_KEY=ECD
heroku config:set SLACK_POLL_INTERVAL=15
heroku config:set BUSINESS_TIMEZONE=America/New_York
heroku config:set BUSINESS_HOURS_START=9
heroku config:set BUSINESS_HOURS_END=17
```

### 4. Copy Deployment Files to Root

```bash
# Copy Procfile to root
cp deployment/heroku/Procfile ./Procfile

# Copy runtime.txt to root
cp deployment/heroku/runtime.txt ./runtime.txt

# Verify package.json exists in root (for Claude Code installation)
ls -la package.json
```

### 5. Deploy to Heroku

```bash
# Add and commit deployment files
git add Procfile runtime.txt package.json
git add src/pm_agent_service.py  # Updated with dynamic PORT
git add deployment/heroku/app.json  # Updated with buildpacks
git commit -m "Configure Heroku deployment with dual-dyno architecture"

# Push to Heroku
git push heroku main

# Or if using a different branch:
git push heroku your-branch:main
```

### 6. Scale Dynos

```bash
# Enable both dynos
heroku ps:scale worker=1 clock=1

# Verify both are running
heroku ps
```

Should output:
```
=== worker (Basic): python -u src/pm_agent_service.py (1)
worker.1: up 2024/01/05 14:30:00 -0600 (~ 1m ago)

=== clock (Basic): python clock.py (1)
clock.1: up 2024/01/05 14:30:00 -0600 (~ 1m ago)
```

### 7. Verify Deployment

```bash
# Check logs for both dynos
heroku logs --tail

# Look for these success indicators:
# Worker dyno:
#   ✅ Slack polling started (interval: 15s)
#   ✅ Jira polling started (interval: 60s)
#   🚀 Starting webhook server on port XXXXX
#
# Clock dyno:
#   ✅ Scheduler configured
#   Next standup: 2024-01-06 09:00:00
```

### 8. Test the Deployment

**Test Real-Time Responses (worker dyno):**
```bash
# Tag the bot in Slack
# Message: @PM Agent what's the status of ECD-862?
# Should get instant response
```

**Test Scheduled Tasks (clock dyno):**
```bash
# Run standup manually
heroku run standup

# Or wait for 9 AM ET on a weekday for automatic standup
```

**Test Health Endpoint:**
```bash
# Get the app URL
heroku info

# Check health endpoint
curl https://citemed-pm-agent.herokuapp.com/health
```

## Buildpack Installation Details

### Node.js Buildpack (First)
- Detects `package.json`
- Runs `npm install`
- Installs `@anthropic-ai/claude-code` globally
- Makes `claude` command available to Python processes

### Python Buildpack (Second)
- Detects `requirements.txt`
- Installs Python 3.11.11 (from `runtime.txt`)
- Installs all Python dependencies
- Runs both worker and clock processes

## File Structure

```
project-manager/
├── Procfile              # Defines worker and clock dynos
├── runtime.txt           # Python 3.11.11
├── package.json          # Claude Code CLI installation
├── requirements.txt      # Python dependencies
├── src/
│   └── pm_agent_service.py  # Worker dyno (real-time)
├── clock.py              # Clock dyno (scheduled)
└── deployment/
    └── heroku/
        ├── app.json      # Heroku app configuration
        ├── Procfile      # Source of truth (copy to root)
        └── runtime.txt   # Source of truth (copy to root)
```

## Cost Estimate

- **worker dyno** (Basic): ~$7/month
- **clock dyno** (Basic): ~$7/month
- **Total**: ~$14/month

Note: First 1000 dyno hours per month are free on Heroku's Eco plan.

## Monitoring

### View Logs
```bash
# All logs
heroku logs --tail

# Worker dyno only
heroku logs --tail --dyno worker

# Clock dyno only
heroku logs --tail --dyno clock
```

### Check Dyno Status
```bash
heroku ps
```

### Restart Dynos
```bash
# Restart both
heroku restart

# Restart specific dyno
heroku restart worker
heroku restart clock
```

## Troubleshooting

### Claude Code CLI Not Found
**Error:** `claude: command not found`

**Solution:**
```bash
# Verify buildpacks are in correct order
heroku buildpacks

# Should be: 1. nodejs, 2. python
# If wrong, remove and re-add in correct order
heroku buildpacks:clear
heroku buildpacks:add heroku/nodejs
heroku buildpacks:add heroku/python

# Redeploy
git commit --allow-empty -m "Trigger rebuild"
git push heroku main
```

### Port Binding Error
**Error:** `Web process failed to bind to $PORT within 60 seconds`

**Solution:** The worker dyno is NOT a web process, it's a background worker. Make sure Procfile uses:
```
worker: python -u src/pm_agent_service.py
```
NOT:
```
web: python -u src/pm_agent_service.py
```

### Environment Variables Not Set
```bash
# List all config vars
heroku config

# Set missing variable
heroku config:set VAR_NAME=value
```

### Database State Issues
```bash
# The SQLite databases are NOT persistent on Heroku!
# On dyno restart, all state is lost.
# This is OK for our use case (processed messages can be reprocessed safely)
```

## Next Steps After Deployment

1. **Monitor first 24 hours** - Watch logs for any errors
2. **Verify 9 AM standup** - Check Slack next weekday at 9 AM ET
3. **Test Slack mentions** - Verify instant responses
4. **Test Jira comments** - Tag bot in Jira, verify response
5. **Check SLA monitoring** - Verify hourly checks run during business hours

## Rollback

If deployment fails:
```bash
# Rollback to previous release
heroku rollback

# Or deploy specific commit
git push heroku commit_sha:main --force
```

## Support

- **Heroku Dashboard:** https://dashboard.heroku.com/apps/citemed-pm-agent
- **Logs:** `heroku logs --tail`
- **Debug:** `heroku run bash` (opens shell in dyno)
