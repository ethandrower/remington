# `scripts/core/` — legacy PM routines (superseded, still running)

These are the Heroku-worker routines. Their logic was extracted into **pure functions**
that now live in openclaw-hq:

    openclaw-hq/agents/remington/mcp/remington_mcp/pm_core/

| Here (legacy) | Superseded by |
|---|---|
| `sla_check_working.py` | `pm_core.sla.check_slas` |
| `blocked_ticket_analyzer.py` | `pm_core.blocked.analyze_blocked_tickets` |
| `timesheet_report.py` | `pm_core.timesheet.build_timesheet` |
| `daily_priorities.py` | `pm_core.priorities.build_daily_priorities` |
| `pm_audit.py` | `pm_core.audit.run_pm_audit` / `compute_pm_audit` |
| `standup_workflow.py` | `pm_core.standup.run_standup` |
| `db_cleanup.py` | no `pm_core` twin — the agent's `tasks/db-cleanup.md` runbook |

`pm_core.portfolio.check_portfolio_health` has **no** legacy script here (BUILDOUT's
source map cites a `portfolio_health_check.py` that does not exist in this repo).

⚠️ **Two copies of this logic exist until the reactive cutover** (BUILDOUT step 6) retires
the pollers and this worker. Until then: **fix bugs in BOTH, or fix in `pm_core` and port
back.** A fix applied only here will be silently lost when the worker is retired; a fix
applied only there won't reach production while the worker still runs.

Do not add new PM routines here — add them to `pm_core` + `pm-mcp` in openclaw-hq.
