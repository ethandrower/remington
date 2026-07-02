# Task: PM Self-Audit

**Cadence:** Per-sprint — approximated weekly (Friday) or on a sprint-close hook (mechanism TBD).
**Purpose:** Grade Remington's OWN PM performance for the sprint (6 metric groups, A–D) and feed the score into the weekly reflection loop.

---

## State in
- Read the **`self_audit`** block from `../STATE.md` (`SPRINT_ID | date | score | notable_misses`) — for context / to avoid re-auditing a sprint already scored. This routine is **write-mostly**; `pm_audit` itself takes no `prior_state`.

## Steps
1. Determine the PM's Jira `accountId` (Remington's own PM identity — from config / roster lookup). This is required.
2. Call `pm.pm_audit(pm_account_id=<id>, sprint_id=<active or closing sprint, omit for active>)`.
3. Read the result:
   - `grades` / `overall_grade` — A/B/C/D per metric group and overall.
   - `breakdown` — the 6 groups (e.g. approval turnaround, blocker engagement, grooming/estimation coverage, transitions/reopens, mid-sprint scope churn, PM response time) with the numbers behind each grade.
   - Identify `notable_misses` — the lowest-grade groups and their driving metrics.

## Posting
- Post a concise scorecard to **#pm-agent-logs** (channel ID in cron) — self-reflection to Remington's own log channel, post directly. This routine grades Remington, not the team; it does **not** comment on developer tickets. No Jira writes; therefore no write-gating proposals here.
- The score also feeds the weekly reflection/review (per CARD reflection loop) — surface the overall grade and top miss so the weekly review can consume it.

## Write-back
- Append/overwrite the current sprint's row in the **`## self_audit`** block of `../STATE.md`: `SPRINT_ID | date | overall_grade | notable_misses`. Keep recent sprints; prune old ones.

## Self-loop guard
- Subject of the audit IS Remington (by `pm_account_id`), so here the PM's own actions are intentionally in scope. The guard flips: do **not** double-count or exclude Remington's comments — but do exclude other agents/bots if present so the score reflects the PM only.

## Skills
- `../skills/agile-workflows` (sprint mechanics, what good PM cadence looks like). No SLA/DoR skill required.
