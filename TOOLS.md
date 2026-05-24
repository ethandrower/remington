# PM Tooling Index

Single source of truth for every PM tool in this repo. Check here **before** writing JQL, Python, or curl from scratch — most calculations and integrations already exist.

Ordering: PM scripts → Python modules → dashboard API → trinity → Atlassian MCP. Within each section: most useful first.

---

## 1. PM Workflow Scripts (`scripts/core/`)

End-to-end workflows. These are what the dashboard "Run" buttons trigger. Run from repo root.

| Script | Use when | Key flags |
| --- | --- | --- |
| `scripts/core/standup_workflow.py` | Daily 5-part standup: gap detection → productivity audit → timesheets → SLA → deadline risk. Posts to Slack. | `--dry-run`, `--date YYYY-MM-DD`, `--verbose` |
| `scripts/core/sla_check_working.py` | Run SLA monitor across all 4 categories (QA stale 24h, pending approval 48h, blocked 24h, changes-requested 48h). Uses `get_status_history` for accurate time-in-status. | `--report` (post Slack digest), `--dry-run` |
| `scripts/core/blocked_ticket_analyzer.py` | Claude-powered triage for "Blocked" tickets — checks for missing `is blocked by` link, resolved blockers, comment-response gaps. 48h dedup. | `--report` (Slack digest) |
| `scripts/core/daily_priorities.py` | Compute deadline-risk dashboard (overdue / critical / high / medium). No Slack post by default — returns list. | (none — programmatic) |
| `scripts/core/timesheet_report.py` | Per-developer timesheet vs. work analysis for the last N days. | `--days N`, `--user <accountId>` |
| `scripts/core/pm_audit.py` | PM productivity self-audit (currently in-flight, untracked). Measures sprint-level PM activity. | `--pm-id`, `--sprint-id`, `--dry-run` |
| `scripts/core/db_cleanup.py` | Maintenance — prune old check_runs / activity rows from dashboard DB. | (one-shot) |
| `scripts/core/jira_api_client.py` | Shared HTTP client. **Not a CLI** — imported by other scripts. |  |

---

## 2. Trinity Python API — `from trinity.{jira,confluence,base} import ...`

Trinity exposes a full Python API as a strict superset of what the old `src/tools/` modules did. **Use this from any script that needs in-process Atlassian access** — no subprocess, no manual HTTP, no shelling out.

### `from trinity.jira import ...`

`search_jira`, `get_jira_issue`, `add_jira_comment`, `edit_jira_issue`,
`transition_jira_issue`, `get_jira_transitions`, `lookup_jira_user`,
`list_jira_projects`, `get_issue_worklogs`, `fmt_seconds`,
`get_status_history`, `get_boards`, `get_sprints`, `get_active_sprint`,
`get_sprint_issues`, `get_completed_sprint_issues`, `get_release_issues`,
`get_current_sprint_completed`

### `from trinity.confluence import ...`

`get_confluence_page`, `create_confluence_page`, `update_confluence_page`,
`search_confluence`, `get_confluence_spaces`, `get_page_children`,
`add_confluence_comment`, `list_space_pages`

### `from trinity.base import ...`

`get_jira_auth_headers`, `get_confluence_auth_headers`, `get_bitbucket_auth_headers`,
`JIRA_BASE_URL`, `AGILE_BASE_URL`, `CONFLUENCE_BASE_URL`, `BITBUCKET_BASE_URL`,
`JIRA_WEB_URL`, `ATLASSIAN_CLOUD_ID`, `AtlassianClient`, `format_error`,
`build_adf_comment`. Plus typed exceptions: `TrinityError`, `AtlassianAPIError`,
`AuthenticationError`, `NotFoundError`, `RateLimitError`, `ConflictError`.

### Bitbucket Python API

`from trinity.bitbucket import BitbucketAPI` — fuller API than the CLI surface; use when the `trinity bb` subcommands aren't enough.

---

## 3. Dashboard API (`src/dashboard/app.py`)

Flask service. Default port via `DASHBOARD_PORT` env or 8080. Hit with `curl http://localhost:8080/api/...` to **read precomputed sprint state without recomputing**.

### Sprint health (use these instead of recomputing)

| Endpoint | Returns |
| --- | --- |
| `GET /api/agent/sprint-report` | Full computed sprint snapshot — burndown, velocity, per-dev breakdown. **Default when an agent or session needs current sprint state.** |
| `GET /api/sprint-pulse` | Current sprint pulse: per-developer status weights, role grouping (Dev/Design/All), banner state pills |
| `GET /api/sprint-burndown` | Ideal vs. actual burndown + scope-creep step-function |
| `GET /api/sprint-planning` | Active + upcoming sprint composition |
| `GET /api/sprint-planning/sprints` | Sprint list for the active board |

### Operational data

| Endpoint | Returns |
| --- | --- |
| `GET /api/stats` | Aggregate counts (active violations, recent runs) |
| `GET /api/violations` | Active SLA violations |
| `GET /api/checks/history` / `latest/<type>` | Past check runs (standup, SLA, blocked, etc.) |
| `GET /api/checks/schedules` | Scheduled jobs configuration |
| `GET /api/blocked/analysis` | Latest blocked-ticket analyzer output |
| `GET /api/timesheets` | Latest timesheet report |
| `GET /api/pr/reviews` | Reviewed PR commit history (`bb_reviewed_pr_commits`) |
| `GET /api/team-members` | Team roster (DB-backed) |
| `GET /api/team-members/lookup?q=<name>` | Live Jira+Slack search |
| `GET /api/agent/activity` | Activity tracker stream |
| `GET /api/pm-audit` | Latest PM self-audit |
| `GET /api/settings/channels` / `system` | Channel + system settings |

### Triggers (POST — kicks background thread, return immediately)

| Endpoint | Triggers |
| --- | --- |
| `POST /api/checks/run` | Generic check by `check_type` |
| `POST /api/blocked/run` | Blocked ticket analyzer |
| `POST /api/timesheets/run` | Timesheet report |
| `POST /api/pm-audit/run` | PM audit |
| `POST /api/violations/<id>/resolve` | Mark violation resolved |
| `POST /api/team-members/reconcile` | Re-sync roster against Jira/Slack |

---

## 4. Trinity CLI (`trinity ...`)

**Allow-listed.** Custom unified Atlassian CLI. JSON output by default. **Preferred for all Bitbucket work** and for any Atlassian operation the MCP doesn't expose.

```bash
trinity --json jira search "project = ECD AND sprint in openSprints()"
trinity jira show ECD-1234
trinity jira sprint-issues --sprint-id 123
trinity jira status-history ECD-1234
trinity jira release-issues --current-sprint
trinity jira transitions ECD-1234
trinity confluence search "title ~ 'Sprint Review'"
trinity bb list --state OPEN
trinity bb show 4567
trinity bb diff 4567
trinity bb activity 4567       # PR timeline — comments, approvals, commits
trinity bb comment 4567 "..."
```

Full surface (run `trinity <cmd> --help` for any specifics):

- **`trinity jira`** — `boards`, `comment`, `create`, `edit`, `issue-types`, `projects`, `release-issues`, `search`, `show`, `sprints`, `sprint-issues`, `status-history`, `transition`, `transitions`, `user`, `worklogs`
- **`trinity confluence`** — `children`, `comment`, `create`, `get`, `pages`, `search`, `spaces`, `update`
- **`trinity bb`** — `activity`, `comment`, `diff`, `list`, `show` (override workspace/repo with `-w`/`-r`)

---

## 5. Atlassian MCP (`mcp__atlassian__*`)

Convenience layer for **interactive chat use only**. Allow-listed for friction-free Jira/Confluence reads and simple writes (search, get, add comment, transition, edit). No Bitbucket coverage.

Do **not** call MCP tools from scripts — use `from trinity.{jira,confluence} import ...` instead. The MCP is per-message; trinity is reusable in-process and far cheaper than a subprocess.

---

## Decision tree

```
Need Atlassian/Bitbucket data?
├── In a script / dashboard?    → from trinity.{jira,confluence,base} import ...
├── Bitbucket?                  → trinity bb (CLI) or from trinity.bitbucket import BitbucketAPI
├── Sprint health snapshot?     → curl dashboard /api/agent/sprint-report
├── Sprint calculations
│   from raw data?              → don't — call /api/sprint-* or scripts/core/*
└── Interactive chat lookup?    → mcp__atlassian__* OR trinity CLI (either fine)
```
