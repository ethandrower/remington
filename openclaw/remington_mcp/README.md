# Remington MCP tool layer

The tools Remington's routines call, as two MCP servers the OpenClaw gateway loads.

```
remington_mcp/
├── trinity_mcp.py   # MCP server: Atlassian + Bitbucket (wraps the `trinity` pkg)
├── pm_mcp.py        # MCP server: PM routines (wraps pm_core)
├── pm_core/         # pure business logic extracted from scripts/core (no DB/Slack/Flask)
├── config.py        # env-driven PMConfig (project key, business hours, tz, holidays)
└── requirements.txt
```

## Design

- **`trinity_mcp`** — the *only* sanctioned Atlassian/Bitbucket path. Jira, Confluence,
  Bitbucket all flow through trinity's headless token auth. Reads + agent-gated writes.
- **`pm_mcp`** — wraps `pm_core`, the pure routine logic. Every tool **computes and
  returns** JSON; it never posts to Slack or writes to Jira (the agent does that via
  `trinity_mcp`, under the propose→approve→execute standing order).
- **State** — stateful tools (`sla_check`, `blocked_analysis`, `portfolio_audit`,
  `standup`) take a `prior_state` dict and return the new `state`. The agent reads the
  relevant block from `STATE.md`, passes it in, writes the returned state back. This
  replaces the old monolith's SQLite alert-tracker — see [`../ROUTINES.md`](../ROUTINES.md).

## Environment (set in the gateway process, never committed)

| Var | Used by | Notes |
|---|---|---|
| `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` | trinity (Jira/Confluence) | headless auth |
| `BITBUCKET_*` | trinity (Bitbucket) | per trinity config |
| `ATLASSIAN_PROJECT_KEY` (or `PM_PROJECT_KEY`) | pm_mcp | **required** |
| `ATLASSIAN_CLOUD_ID`, `JIRA_INSTANCE_URL` | pm_mcp | defaults to citemed cloud |
| `BUSINESS_HOURS_START/END`, `BUSINESS_TIMEZONE`, `COMPANY_HOLIDAYS` | pm_mcp | SLA business-hours math |

`trinity` must be installed in the same env (editable from `~/code/citemed/atlassian-trinity`).

## Run

```bash
pip install -r requirements.txt        # plus: pip install -e ~/code/citemed/atlassian-trinity
cd ..                                  # the openclaw/ dir (so remington_mcp is importable)
python -m remington_mcp.trinity_mcp    # stdio
python -m remington_mcp.pm_mcp         # stdio
```

## Register with the OpenClaw gateway

Add to the gateway's `~/.openclaw/openclaw.json` (mcpServers), pointing at this checkout:

```jsonc
"mcpServers": {
  "trinity": { "command": "python", "args": ["-m", "remington_mcp.trinity_mcp"],
               "cwd": "/path/to/citemed/project-manager/openclaw" },
  "pm":      { "command": "python", "args": ["-m", "remington_mcp.pm_mcp"],
               "cwd": "/path/to/citemed/project-manager/openclaw" }
}
```

## Tool inventory

**pm** (`pm_mcp`): `sla_check`, `blocked_analysis`, `portfolio_audit`, `standup`
(stateful — `prior_state`→`state`); `timesheet`, `daily_priorities`, `pm_audit`.

**trinity** (`trinity_mcp`): Jira reads (`jira_search`, `jira_get_issue`,
`jira_get_transitions`, `jira_lookup_user`, `jira_list_projects`, `jira_get_worklogs`,
`jira_get_status_history`, `jira_get_boards`, `jira_get_sprints`,
`jira_get_active_sprint`, `jira_get_sprint_issues`, `jira_get_completed_sprint_issues`);
Jira writes (`jira_add_comment`, `jira_transition_issue`, `jira_edit_issue`,
`jira_create_issue`); Confluence (`confluence_get_page`, `confluence_search`,
`confluence_list_space_pages`, `confluence_create_page`, `confluence_update_page`,
`confluence_add_comment`); Bitbucket (`bitbucket_list_pull_requests`,
`bitbucket_get_pull_request`, `bitbucket_get_pr_comments`, `bitbucket_get_pr_diff`,
`bitbucket_get_pr_activity`, `bitbucket_add_pr_comment`).

## Known port gaps (tracked, non-blocking)

- `pm_core/sla.py` `_check_pr_slas` → `[]` (PR staleness needs Bitbucket; `TODO(port)`).
- `pm_core/blocked.py` → returns comments for the agent to triage instead of the old
  inline Haiku call; drops `response_needed` re-categorization (`TODO(port)`).
- `standup` sections 3 (productivity) & 6 (deadline risk) are stubs the original never
  implemented; agent-side or follow-up.
- Several routines use `trinity.base` raw REST for fields `trinity.jira` doesn't expose
  (issuelinks, parent, duedate, changelog, `customfield_10020`). Still monolith-free.
