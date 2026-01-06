# Heroku Procfile for CiteMed Project Manager Agent

# Worker dyno - runs real-time polling service (Slack/Jira monitoring)
worker: python -u src/pm_agent_service.py

# Clock dyno - runs scheduled tasks (daily standup, hourly SLA checks)
clock: python clock.py

# One-off commands (run with `heroku run <command>`)
# Example: heroku run standup
standup: python run_agent.py standup --notify-ethan
sla-check: python run_agent.py sla-check
sprint-health: python run_agent.py sprint-health
