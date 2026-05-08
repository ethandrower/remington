# Heroku Procfile for PM Agent
#
# Only 1 dyno needed — the worker handles everything:
#   - Slack/Jira/Bitbucket polling and @mention responses
#   - PR code reviews
#   - SLA monitoring (internal thread, runs hourly)
#   - Daily standup (internal thread, runs weekdays 9am)
#
# web and clock dynos are available but not required:
#   web:   Flask dashboard — enable with `heroku ps:scale web=1` if needed
#   clock: Standalone scheduler — redundant, worker handles scheduling internally

# Dokku deploys: the pm_agent_service IS the web service (uvicorn webhook
# server). Run it as `web` so Dokku's nginx proxy can route HTTP/HTTPS to it.
# The legacy `web: gunicorn src.dashboard.app:app` is disabled here — the
# Flask dashboard has a multi-worker create_all race (see remington#7).
web: python -u src/pm_agent_service.py

# One-off commands (run with `heroku run <command>`)
standup: python run_agent.py standup
sla-check: python run_agent.py sla-check
