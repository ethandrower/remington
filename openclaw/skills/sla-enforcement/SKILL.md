---
name: sla-enforcement
description: SLA definitions, business-hours math, the 4-level escalation matrix, exception handling, and alert deduplication via the STATE.md `sla` block. Use for the SLA sweep, blocked-ticket checks, and any comment/PR/approval overdue evaluation.
---

# SLA Enforcement

The valuable part is the thresholds and the escalation discipline. Preserve them.
Under OpenClaw the compute lives in `pm` MCP; every outward action is gated.

## Tooling (how this runs now)

- **Compute:** `pm.sla_check` returns the current violations as JSON. It is stateful —
  pass in the `sla` block from `STATE.md` as `prior_state`; it returns the new `state`.
  It never posts anything.
- **Reads/writes to Jira:** `trinity` MCP (`jira_search`, `jira_get_issue`,
  `jira_get_status_history`, `jira_add_comment`, `jira_transition_issue`).
- **PR staleness:** needs Bitbucket (`trinity.bitbucket_*`); `pm_core` PR SLAs are a known
  port gap today — evaluate PR staleness agent-side from `bitbucket_list_pull_requests` +
  `bitbucket_get_pr_activity` when needed.
- **Every Jira comment / transition and every Slack alert is a WRITE** → goes through the
  **write-gating standing order** (propose → approve → execute). `sla_check` computing a
  violation is not permission to post; surface the proposed alerts and wait for approval.

## SLA principles

1. **Measure outcomes, not activity** — responsiveness and throughput, not surveillance.
2. **Business hours only** — weekends and configured holidays don't count.
3. **Systematic, evidence-based escalation** — automatic and fair, never a personal call.
4. **Continuous improvement** — tune thresholds with the team from data.

## SLA definitions (CiteMed)

**Communication**
| # | SLA | Target | Owner |
|---|---|---|---|
| 1 | Jira comment response | 2 business days | assignee (or commenter awaiting follow-up); FYI-only excluded |
| 2 | PR review turnaround | 24–48h initial · 24h re-review · 24h final approval | assigned reviewers |
| 3 | Developer response to PR feedback | 4h critical · 24h feature · 48h non-urgent | PR author |

**Work progress**
| # | SLA | Target | Owner |
|---|---|---|---|
| 4 | PR staleness (no new commits) | 2 business days | PR author (excludes PRs awaiting review) |
| 5 | In-Progress ticket w/o git activity | 3 business days | assignee (excludes research/design, external deps) |
| 6 | Pending Approval duration | 48h | PM / CTO |

**Blockers**
| # | SLA | Target | Owner |
|---|---|---|---|
| 7 | Blocked ticket communication | daily update; escalate after 2 days | assignee |
| 8 | Blocked ticket resolution | 2 business days; 5 days → leadership | Tech Lead (technical) / PM (business) |

**QA & bugs**
| # | SLA | Target | Owner |
|---|---|---|---|
| 9 | QA turnaround | 48h from "In QA" | QA Lead |
| 10 | Bug fix response | 1 day critical · 3 days high · sprint-based med/low | assigned dev |

> The hourly **SLA sweep** routine specifically checks: QA stalled >24h · Pending-Approval
> >48h · Blocked >24h · Changes-Requested >48h. `pm.sla_check` does the business-hours math.

## Business hours

`BUSINESS_HOURS_START/END`, `BUSINESS_TIMEZONE`, `COMPANY_HOLIDAYS` are env-driven (Mon–Fri,
9–17 ET default). The clock **starts** on the triggering event, **pauses** outside hours /
weekends / holidays, **resumes** next business day 9am, and **resets** when the required
action is taken. `pm.sla_check` implements this — do not re-derive it by hand.

Quick sense-checks:
- Comment Mon 10am, 2-day SLA → deadline ~Wed 2pm.
- Comment Fri 3pm, 2-day SLA → clock starts, pauses over weekend → deadline ~Tue 4pm.
- Comment after 5pm or on a weekend → clock starts next business day 9am.

## Escalation matrix (4 levels)

Start gentle, increase visibility, escalate persistent issues, always stay professional.

| Level | Trigger | Actions | Tone |
|---|---|---|---|
| **1 Soft reminder** | first breach, 0–2 days overdue | friendly Jira comment tagging owner; "Warnings" in standup; no Slack thread yet | helpful, assumes good intent |
| **2 Direct alert** | 2+ days overdue, L1 unanswered | "OVERDUE" Jira comment + dedicated Slack thread tagging dev; "Critical Follow-Ups" in standup | urgent but professional |
| **3 Team escalation** | 4+ days overdue, blocking others | Jira comment tagging dev + tech lead; add tech lead to Slack thread; DM PM; flag "At Risk" | serious, support offered |
| **4 Leadership** | 7+ days overdue, all prior failed | Jira tag CTO/PM; DM CTO summary; "Sprint Risk" in standup; consider re-planning | critical, immediate action |

Escalation tiers map 1:1 to the deduplication `escalation_level` field below.
Full comment/Slack templates live in the **team-communication** skill — use them verbatim.

## Alert deduplication (STATE.md `sla` block)

Replaces the old SQLite `sla_alerts` table. **Read the `sla` block at sweep start, write it
back at sweep end.** Each entry (see STATE.md scaffold):
`TICKET | breach_type | first_seen | last_alerted | escalation_level | status(open/resolved)`.
Violation identity = `TICKET_breach_type` (e.g. `PR-114_pr_stale`, `ECD-123_comment_response`).

**Alert only when:**
1. **New** — no entry for this `TICKET_breach_type` → alert, add entry.
2. **Escalation increased** — computed level > stored `escalation_level` → alert, bump level.
3. **24h elapsed** — `now - last_alerted >= 24h` → re-alert, update `last_alerted`.

Otherwise **skip** (already alerted recently — respects that the owner may have replied).
When a violation drops out of `sla_check`'s output, mark its entry `status: resolved` (prune
later); optionally post a one-line "thanks, marking addressed" acknowledgement.

This prevents the classic failure: re-spamming the same violation every hour.

## Exceptions

**Pause the clock for:** external vendor/dependency waits, research/design tasks, approved
PTO, active production incidents. Document the exception as a Jira comment (reason + expected
resolution + workaround) — still a gated write.

**Do NOT pause for:** "too busy", "forgot", "didn't see it", "waiting for a meeting."

**De-escalate:** once the owner acts, reset the escalation level, acknowledge, and mark the
`sla` entry resolved. Don't escalate over weekends/after-hours-only breaches, or when the dev
commented within the last ~4h.

## Targets

Overall compliance ≥ 90%. L1 resolves ~80% without further escalation; <5% reach L3; <1%
reach L4. Track compliance by SLA type and trend over time — coach patterns, not incidents.
