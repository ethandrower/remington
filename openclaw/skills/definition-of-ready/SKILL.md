---
name: definition-of-ready
description: Enforce DoR on active work — due dates, hours estimates, and refinement time limits. Three rules, Jira nudge templates, and the standup report section. Use in the standup DoR-nudge step and ad-hoc ticket lint.
---

# Definition of Ready Enforcement

Keeps active work to standard by checking three compliance areas. Runs as the DoR-nudge step
inside the daily **standup** routine (and on ad-hoc lint).

**Tooling:** query violations with `trinity.jira_search` (JQL below) and
`trinity.jira_get_status_history` (time-in-status); mechanical checks via `pm.lint_ticket` /
`pm.enforce_dor`. Posting a nudge is `trinity.jira_add_comment`.

**Write-gating:** every nudge is an outward WRITE → propose → approve → execute. Compute the
full violation list, propose the batch of comments, post only after approval.

**Dedup (STATE.md `dor_nudges` block):** read it at start, write it back at end. Entry:
`TICKET | nudged_date | gaps_flagged`. **Don't re-nag the same gap on the same ticket** — skip
tickets already nudged for that gap unless the gap persists past the escalation window (below).

## Rule 1 — Missing due dates

Active-work statuses must have a due date.
```jql
project = ECD AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND duedate IS EMPTY
ORDER BY status ASC, updated DESC
```
Nudge (tag assignee by account ID):
> 📅 **MISSING DEADLINE** — this ticket has been **{status}** for **{days}** days without a due
> date. @{assignee} please set one by EOD for capacity planning and sprint tracking.

## Rule 2 — Missing hours estimate

Active-work statuses must have `timeoriginalestimate` set (seconds).
```jql
project = ECD AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND timeoriginalestimate IS EMPTY
ORDER BY status ASC, updated DESC
```
Nudge:
> ⏱️ **MISSING HOURS ESTIMATE** — @{assignee} please add an Original Estimate (e.g. "4h", "2d")
> for capacity planning and velocity tracking.

## Rule 3 — Stalled refinement (> 2 days)

Tickets in **In Refinement** must exit within 2 business days — either transition to "Ready for
Development"/"Ready for Design" **or** ask clarifying questions.
```jql
project = ECD AND sprint in openSprints()
AND status = "In Refinement" AND updated < -2d
ORDER BY updated ASC
```
For each: compute days-in-status from `jira_get_status_history`; read recent comments; check
whether a non-Remington author asked a question (`?` in body).

- **No questions asked** → HIGH priority nudge:
  > 🚨 **COMPLETE REFINEMENT** — in **In Refinement** for **{days} days** with no questions.
  > @{assignee} please either transition to Ready for Development / Ready for Design, or ask
  > clarifying questions.
- **Questions pending** → MEDIUM reminder:
  > ⏰ **REFINEMENT REMINDER** — in refinement **{days} days** with pending questions
  > ({author} asked {hours_ago}h ago). @{assignee} please clarify and move it forward.

## Standup report section

```
📋 DoR — MISSING ESTIMATES, DEADLINES & STALLED REFINEMENT
🚫 IN PROGRESS WITHOUT DUE DATES ({n}) — {KEY} "{summary}" · @{assignee} · ACTION set due date
⏱️ WITHOUT HOURS ESTIMATE ({n}) — {KEY} · @{assignee} · ACTION add Original Estimate
🔄 STALLED IN REFINEMENT >2d ({n})
   NO QUESTIONS: {KEY} · @{assignee} · ACTION 🚨 complete refinement now
   QUESTIONS PENDING: {KEY} · @{assignee} · ACTION ⏰ awaiting clarification
📊 COMPLIANCE — Due Dates {x}/{n} · Estimates {x}/{n} · Refinement<2d {x}/{n}
```

## Targets & escalation

Targets: due dates ≥ 95%, estimates ≥ 90%, refinement-exit-within-2d ≥ 95% (100% aspiration for
In Progress / Ready for Dev / Ready for QA).

Escalation if a violation persists (tracked via `dor_nudges` dates): Day 1 Jira nudge → Day 2
Slack mention in dev channel (@assignee + PM) → Day 3 PM/Tech Lead escalation. Mirrors the
sla-enforcement matrix; use team-communication templates.
