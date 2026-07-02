# MEMORY.md — Remington's Long-Term Memory

Standing facts and rules. (Working task-status memory lives in `STATE.md`; day-to-day episodic notes in `memory/`.)

## Standing Rules

- **STATE.md is authoritative for "have I already handled this?"** Always read the relevant block before a routine and write it back after. Never re-alert a violation whose `sla` entry shows it was alerted within the cooldown, and never re-nudge a ticket whose `dor_nudges` entry is recent.
- **Evidence with every flag.** Every escalation or nudge carries the Jira link, the timestamp/age, and the specific gap. No hand-waves.
- **Tag by accountId, never by display name.** Resolve with `jira_lookup_user`. Display names collide.
- **Business-hours math.** SLA ages exclude weekends and configured holidays (`BUSINESS_HOURS_START/END`, `BUSINESS_TIMEZONE`, `COMPANY_HOLIDAYS`). The `pm` tools already apply this — don't recompute naively.
- **Writes are gated.** Jira comments/transitions, Confluence edits, and Slack @-mention escalations are proposed for approval before execution (see `SOUL.md`). Digests to my own channels are not.

## Jira Projects

- **ECD** — Evidence Cloud Development (main product dev): Story, Task, Bug, Epic, Initiative.
- **AI** — AI Module features.
- **MDP** — Ideas Discovery (Jira Product Discovery; `Idea` issue type only). Ideas feed ECD/AI. See the `ideas-management` skill.
- **CI** — Customer Insights (product discovery, customer-specific ideas).

## SLA Targets (defaults; business-hours)

| SLA | Target |
|---|---|
| Jira comment response (dev → stakeholder/PM) | 2 business days |
| PR review turnaround (ready → first review) | 24–48h |
| Blocked-ticket updates | daily; escalate after 2 days silent |
| PR staleness (commit activity) | 2 business days |
| Pending-approval duration | 48h |

The `sla-enforcement` skill holds the escalation ladder and tone (L1 soft → L4 leadership).

## Team & Systems

- **Owner:** Ethan Drower (Slack `U7L6RKG69`).
- **Roster:** loaded from config (`TEAM_MEMBER_*`) or Confluence. Needed by `daily_priorities` (pass a roster list of `{name, slack_id, jira_id}`).
- **Systems:** Jira (ECD/MDP/AI), Bitbucket (citemed_web, citemed_ai), Confluence (engineering space — release notes, roster).

## Channels (surfaces)

`#ecd-standup` · `#sla-violations` · `#sla-qa-alerts` · `#blocked-tickets` · `#timesheets` · `#portfolio-health` · `#sprint-planning` · `#pm-agent-logs`. (Channel IDs are set per cron job in `cron/jobs.json`.)
