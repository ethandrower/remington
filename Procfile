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

# Dokku deploy:
#   web    = the Flask dashboard (single worker to dodge the create_all
#            race tracked in remington#7). Externally routable via nginx.
#   worker = pm_agent_service does the Slack/Jira/Bitbucket polling and
#            keeps a uvicorn status endpoint internal-only. PORT is set
#            inline because Dokku assigns PORT='' to non-web procs and
#            int('') crashes (remington#7).
web: gunicorn "src.dashboard.app:app" --bind 0.0.0.0:$PORT --workers 1 --timeout 120
worker: env PORT=8001 python -u src/pm_agent_service.py

# One-off commands (run with `heroku run <command>`)
standup: python run_agent.py standup
sla-check: python run_agent.py sla-check
