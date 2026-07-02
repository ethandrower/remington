# Remington Buildout — Heroku monolith → OpenClaw consumer

Companion to [`CARD.md`](CARD.md) and the replatform proposal
(`../docs/REMINGTON_OPENCLAW_REPLATFORM_PROPOSAL.md`). Tracks what's built vs pending.

## Target shape

```
  OpenClaw (oc-prod)  ── Slack · cron · heartbeat · webhooks · session tracking
        │ loads
   trinity-mcp ─────────────────────── pm-mcp
   (Atlassian + Bitbucket, headless)   (PM tools over pm_core)
        └──────────────┬──────────────┘
                   pm_core  (pure callables — the one real refactor)
```

Keep the hands (MCP servers) with the code; the brain (this `openclaw/` dir) is managed
from openclaw-hq. Every external write goes through propose → approve → execute.

## Sequence (dependency-ordered)

| # | Step | What | Status |
|---|---|---|---|
| 1 | **trinity-mcp** | Wrap the `trinity` package as an MCP server (30 Jira/Confluence/Bitbucket tools, headless token auth). | ✅ built (`remington_mcp/trinity_mcp.py`); imports + authenticates live on oc-prod |
| 2 | **pm_core** | Extract SLA / blocked / portfolio / timesheet / priorities / audit logic out of `scripts/core/*` into pure functions that return data (no Slack/DB side effects). | ✅ built (`remington_mcp/pm_core/`); verified live vs real ECD data |
| 3 | **pm-mcp** | Compose `pm_core` into MCP tools. | ✅ built (`remington_mcp/pm_mcp.py`, 7 tools); `sla_check`/`blocked_analysis`/`portfolio_audit`/`standup` return real data |
| 4 | **OC workspace** | Author `SOUL/AGENTS/MEMORY/IDENTITY/USER/HEARTBEAT`; port skills; write cron + standing orders. | ✅ done — 6 bootstrap files, 7 skills, 7 task runbooks, `cron/jobs.json` |
| 5 | **Deploy** | Register `pm` agent + MCP servers + Slack account in `openclaw.json`; stage workspace-pm; deploy cron. | ◑ agent+MCP+Slack registered & gateway restarted (Piper intact); cron deployed to `#pm-agent-logs` (consolidated), **staged disabled**; awaiting bot channel-invite to enable + smoke-test |
| 6 | **Reactive cutover** | Jira/BB/Confluence outbound webhooks → `/hooks/agent`; delete the 4 pollers; park `pm_agent_service.py`. | ☐ not started (needs Atlassian-admin webhook config) |

Steps 1–4 complete; step 5 in flight (see `deploy/DEPLOY.md`). Deployed 2026-07-02.

### Known follow-ups
- `timesheet` returned `developers:0` for the last complete week on live data — verify the worklog query (may be legitimately empty, or a field/date issue in `pm_core/timesheet.py`).
- `pm_core/sla.py` `_check_pr_slas` still stubbed (Bitbucket PR staleness) — `TODO(port)`.
- Real per-channel Slack IDs pending (currently consolidated to `#pm-agent-logs`); split out once the 7 channels exist.

## Source → destination map (the IP that moves)

| Today (script) | Destination |
|---|---|
| `scripts/core/sla_check_working.py` | `pm_core.sla` → pm-mcp `sla_check` + cron |
| `scripts/core/blocked_ticket_analyzer.py` | agent reasoning (its embedded Claude call collapses into the OC agent) + cron |
| `scripts/core/portfolio_health_check.py` | `pm_core.portfolio` → pm-mcp `portfolio_audit` + weekly cron |
| `scripts/core/timesheet_report.py` | `pm_core.timesheet` → pm-mcp tool + Mon cron |
| `scripts/core/daily_priorities.py` | `pm_core.priorities` → pm-mcp tool |
| `scripts/core/pm_audit.py` | `pm_core.audit` (`compute_pm_audit` already pure) → pm-mcp + self-audit reflection |
| `scripts/core/standup_workflow.py` | cron job that calls pm-mcp tools, reasons, posts |
| `scripts/utilities/dor_enforcement.py` | `definition-of-ready` skill + pm-mcp `lint_ticket`/`enforce_dor` |
| `scripts/utilities/generate_release_notes.py` | skill + trinity-mcp (Jira read / Confluence write) |
| `src/agents/subgraphs/sprint_planning.py` | agent loop + pm-mcp propose/revise/apply slate tools |
| `src/monitors/{jira,bitbucket,confluence,slack}_monitor.py` | **deleted** — replaced by webhooks + OC Slack |
| `.claude/skills/*`, `.claude/procedures/*` | OpenClaw skills (mostly verbatim) |
| `pm_agent_service.py`, `src/orchestration/` | **parked** as reference (seed for a future bespoke harness) |

## Blockers / decisions
- remington#6 (Postgres 20GB, blocking writes) + #7 (dyno crashes) bite until cutover — but the
  replatform retires that worker, so most of that state disappears.
- Gateway already exists (oc-prod). Webhook exposure + bearer-secret rotation: TBD.
- Does the dashboard keep its own posting path or read through pm_core? (Proposal: dashboard stays.)
