# Task: Blocked-Ticket Analysis

**Cadence:** Daily, weekday mid-morning — `0 10 * * 1-5` ET.
**Purpose:** Run the decision tree over blocked tickets (no-link / blocker-resolved / cascading-block / legitimately-blocked), triage each thread, and digest — distinguishing still-blocked from resumed from needs-response.

---

## State in
- Read the **`blocked`** block from `../STATE.md` (`TICKET | flagged_date | last_state(blocked/resumed/response-needed) | last_comment_id_seen`).
- Parse to a dict keyed by ticket and pass as `prior_state` for 48h dedup and to detect state changes (blocked → resumed).

## Steps
1. Call `pm.blocked_analysis(prior_state=<blocked block>)`.
2. Read the result:
   - `tickets` / `by_category` — each ticket's `category`, `action`, `actionable`, `alert_target`, `needs_alert`, `link`, `assignee`.
   - Legitimately-blocked tickets carry recent `comments` (author, text, id) for you to triage — decide PM-hygiene vs resumed vs response-needed by reading the thread. The tool drops the old inline Haiku re-categorization (`response_needed` is now your call).
   - `alerts_to_send` and the new `state`.
3. For each ticket, compare its latest comment id to the stored `last_comment_id_seen` — new comments since last run are what warrant a fresh look; unchanged threads stay deduped.

## Posting
- Post the triage digest to **#blocked-tickets** (channel ID in cron) — autonomous, post directly. Group by category; call out resumed tickets (should leave blocked status) and response-needed tickets (assignee owes an update).
- Any **Jira comment** (e.g. asking the assignee for a status update), **transition** (un-blocking a resumed ticket), or **@-mention escalation** is an outward write → **propose → approve → execute** via trinity. Never comment/transition directly from this routine.

## Write-back
- Overwrite the **`## blocked`** block in `../STATE.md` from the returned `state`: one line per ticket with updated `last_state` and `last_comment_id_seen`. Drop tickets no longer blocked/resolved.

## Self-loop guard
- When reading each comment thread, ignore comments authored by Remington — dedup on comment id so its own prior "any update?" nudge is never mistaken for a developer response or a state change.

## Skills
- `../skills/jira-best-practices` (blocker hygiene, decision tree), `../skills/team-communication` (digest + nudge tone).
