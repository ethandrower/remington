# Remington — Routine Catalog (spec)

Companion to [`CARD.md`](CARD.md) and [`BUILDOUT.md`](BUILDOUT.md). This is the **full-port**
routine spec: every routine the Heroku monolith runs today, mapped to its OpenClaw cadence,
the tools/skills it needs, and the **state** it reads/writes. It is the reference that drives
the cron job definitions, `AGENTS.md` standing orders, and the `pm-mcp` tool surface.

**Two decisions baked in (2026-06-28):**
1. **Full port** — all routines carry over at cutover; no capability regression vs the monolith.
2. **Curated `STATE.md`** — state-dependent routines read/write a single agent-maintained
   markdown file keyed by ticket/initiative ID (see [State](#state) below). Deliberate
   stepping-stone until a real task-state store is designed.

Cadence buckets follow HQ `CONVENTIONS.md`. All clock times are **ET**.

---

## ⚡ Reflexes — webhook / mention driven (NOT cron)

| Routine | Trigger | What it does | Tools | Skills | STATE.md |
|---|---|---|---|---|---|
| Slack reply | @mention / DM in any Remington channel | Context-aware PM answer in-thread | trinity-mcp (read), pm-mcp | team-communication | thread memory (OC-native) |
| Jira reply | comment @mention → `/hooks/agent` | Respond on the ticket | trinity-mcp | jira-best-practices | self-loop dedup |
| Bitbucket reply / review | PR @mention or new commit | Answer or run code review | trinity-mcp (BB) | — | dedup processed PR/commit ids |
| Confluence reply | page comment @mention | Respond on the page | trinity-mcp | — | dedup |

All reflexes inherit HQ standing orders **`self-loop-guard`** (never react to own output; dedup
on stable id) and **`write-gating`** (propose→approve→execute for any write).

---

## 🕐 Hourly / continuous (cron)

| Routine | Cron (ET) | What it does | Tools | Skills | STATE.md |
|---|---|---|---|---|---|
| **SLA sweep** | `0 9-18 * * 1-5` | QA stalled >24h · Pending-Approval >48h · Blocked >24h · Changes-Requested >48h (business-hours math) → post alerts | pm-mcp `sla_check`, Slack | sla-enforcement, sla-alert-deduplication | **R/W** — `sla` block: which violations already alerted, escalation level, resolved |
| **Heartbeat** | OC-native 30m | Liveness ping (business hours) | — | — | last-beat marker |

> Heartbeat rides OpenClaw's existing global 30m beat — not a dedicated cron.

---

## 📅 Daily (cron)

| Routine | Cron (ET) | What it does | Tools | Skills | STATE.md |
|---|---|---|---|---|---|
| **Standup** | `0 9 * * 1-5` | 7-part: burndown · code↔ticket gaps · productivity · timesheet glance · SLA roll-up · DoR nudges (posts Jira) · action items. Includes per-person **daily priorities**. | pm-mcp (`sla_check`, `timesheet`, `daily_priorities`, `lint_ticket`/`enforce_dor`), trinity-mcp, Slack | agile-workflows, definition-of-ready, team-communication | **R/W** — `action_items`: did yesterday's items resolve? open new ones |
| **Blocked-ticket analysis** | `0 10 * * 1-5` | 3-step decision tree; reads each comment thread → PM-hygiene / resumed / response-needed; digest | pm-mcp `blocked_analysis`, trinity-mcp | jira-best-practices | **R/W** — `blocked`: flagged set, last state (blocked/resumed), last comment seen |

---

## 📆 Weekly (cron)

| Routine | Cron (ET) | What it does | Tools | Skills | STATE.md |
|---|---|---|---|---|---|
| **Timesheet / worklog** | `30 9 * * 1` | Hours vs estimates, over-estimate flags | pm-mcp `timesheet`, trinity-mcp | — | optional trend vs prior weeks |
| **Portfolio health audit** | `45 9 * * 1` *(time TBD)* | 7 Initiative/Epic hygiene signals | pm-mcp `portfolio_audit` | jira-best-practices | **R/W** — `initiatives`: per-initiative health snapshot + trend |
| **PM self-audit** | per-sprint *(mechanism TBD — weekly Fri or sprint-close hook)* | Per-sprint scorecard on Remington's OWN PM performance; feeds reflection | pm-mcp `pm_audit` | — | **W** — `self_audit`: score by sprint; feeds weekly review |
| **DB cleanup / retention** | `0 3 * * *` | Prune checkpoints + retention tables | — | — | — |

---

## 🧠 On-demand — conscious skills (invoked, NOT cron)

| Routine | Invocation | What it does | Tools | Skills |
|---|---|---|---|---|
| **Sprint planning** | asked in Slack | propose → feedback → approval → execute slate; only `apply_sprint_slate` writes | pm-mcp slate tools | agile-workflows + write-gating |
| **Release notes** | asked | Jira → Confluence, grouped by module | trinity-mcp | — |
| **Ticket draft + lint** | asked | Mechanical standards gate (naming, Outcome/AC, hierarchy) | pm-mcp `draft_ticket` / `lint_ticket` | definition-of-ready, jira-best-practices |
| **Ideas intake / management** | asked | Idea → triaged story per the intake playbook | pm-mcp, trinity-mcp | ideas-management-workflow |
| **Ad-hoc Jira** | asked | search / get / comment / transition / user-lookup | trinity-mcp | — |

---

## State

Several routines are **incorrect without cross-run memory** — today the monolith fakes this
with SQLite (`sla_alert_tracker`, processed-message sets, `last_check`). In the OpenClaw
paradigm that state moves to a single curated **`STATE.md`** the agent reads at routine start
and writes at routine end, keyed by Jira ticket / initiative id. This is a stepping-stone to a
proper task-state store, not the final architecture.

Blocks (see `STATE.md` scaffold):

| Block | Keyed by | Written by | Read by |
|---|---|---|---|
| `sla` | ticket key | SLA sweep | SLA sweep, standup (roll-up) |
| `blocked` | ticket key | blocked analysis | blocked analysis, standup |
| `action_items` | item id | standup | standup |
| `initiatives` | initiative key | portfolio audit | portfolio audit, standup |
| `dor_nudges` | ticket key | standup (DoR), ticket-lint | standup |
| `self_audit` | sprint id | PM self-audit | weekly reflection |

**Why it matters:** prevents the classic failures — SLA sweep re-spamming the same violation
every hour, blocked analysis unable to tell "still blocked" from "resumed," standup never
closing the loop on yesterday's action items.

---

## Tool surface implied by this catalog

- **trinity-mcp** — Atlassian + Bitbucket primitives (headless token auth): Jira search/get/
  comment/transition/changelog/worklog, sprint/board reads, Confluence read/write, Bitbucket PRs.
- **pm-mcp** (over `pm_core`) — `sla_check`, `blocked_analysis`, `portfolio_audit`, `timesheet`,
  `daily_priorities`, `pm_audit`, `draft_ticket`, `lint_ticket`/`enforce_dor`, sprint-slate tools,
  release-notes helper.
- **Slack** — OC-native channel posting (surfaces listed in `CARD.md`).

## Open decisions
- Portfolio-audit and self-audit exact schedule (self-audit wants a sprint-close trigger, which
  cron can only approximate weekly).
- Does DoR enforcement nudge live inside standup, or as its own routine?
- `STATE.md` size management — when does it need pruning / splitting per block?
