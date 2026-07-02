# Task: Daily Standup

**Cadence:** Daily, weekday mornings — `0 9 * * 1-5` ET.
**Purpose:** Post the 7-part tactical standup (burndown · code↔ticket gaps · productivity · timesheet glance · SLA roll-up · deadline risk · DoR enforcement) plus per-person daily priorities, and close the loop on yesterday's action items.

---

## State in
- Read the **`sla`**, **`action_items`**, and **`dor_nudges`** blocks from `../STATE.md`.
- Pass the whole state (at minimum the `sla` block, keyed by ticket) as `prior_state` to `standup` so the SLA roll-up and DoR sections dedup correctly.
- Keep `action_items` in hand to reconcile yesterday's open items (below). Keep `dor_nudges` so you don't re-nag the same gaps.

## Steps
1. Call `pm.standup(prior_state=<full STATE>)`. Read `sections` / the named blocks:
   - `sprint_burndown` (completion_pct, at_risk), `code_ticket_gaps`, `productivity_audit` (may be a stub), `timesheet_analysis`, `sla_monitoring` (roll-up), `deadline_risk`, `dor_enforcement` (with `suggested_comments` — DoR nudge texts keyed by ticket/assignee).
   - `alerts_to_send`, and the new `state`.
2. Get per-person priorities: fetch the team roster (from config / Confluence roster) and call `pm.daily_priorities(roster=<roster>, violations=<state.sla or standup sla roll-up>)`. Read `members[].tickets` (ranked, with `priority`, `age_hours`, `link`).
3. Reconcile action items: for each open entry in the `action_items` block, check whether it resolved (ticket moved, SLA cleared, gap closed per this run's sections). Mark resolved; carry forward the rest; open new items from today's gaps/risks.

## Posting
- Post the assembled standup digest + daily priorities to **#ecd-standup** (channel ID in cron). This digest to Remington's own channel is autonomous — post directly.
- **DoR nudges post to Jira**, so they are outward writes: for each `dor_enforcement.suggested_comments` entry, **propose → approve → execute**. Draft the comment (from the suggested text), post the proposal, wait for approval, then `trinity.jira_add_comment`. Same gate for any transition or @-mention escalation.

## Write-back
- Overwrite **`## action_items`** in `../STATE.md` with the reconciled set (`ID | created_date | description | owner | status | source_ticket`) — resolved rows dropped, new rows added.
- Overwrite **`## dor_nudges`** with the tickets nudged this run (`TICKET | nudged_date | gaps_flagged`).
- Fold the returned `state.sla` roll-up back into the **`## sla`** block only if the tool advanced it (the hourly sla-sweep owns that block; don't clobber fresher entries).

## Self-loop guard
- Code↔ticket gap and DoR detection must ignore Remington's own prior comments — dedup on comment/author id so its earlier nudges aren't read as developer activity or as a fresh gap.

## Skills
- `../skills/agile-workflows` (standup shape, burndown), `../skills/definition-of-ready` (DoR gaps + nudge wording), `../skills/team-communication` (digest tone, priorities), `../skills/sla-enforcement` (roll-up interpretation).
