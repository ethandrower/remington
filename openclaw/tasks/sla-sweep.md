# Task: SLA Sweep

**Cadence:** Hourly, business hours — `0 9-18 * * 1-5` ET.
**Purpose:** Catch SLA breaches (QA stalled >24h, Pending-Approval >48h, Blocked >24h, Changes-Requested >48h) and alert once per breach with escalation — never re-spam.

---

## State in
- Read the **`sla`** block from `../STATE.md`.
- Parse its entries (`TICKET | breach_type | first_seen | last_alerted | escalation_level | status`) into a dict keyed by ticket, and pass it as `prior_state` so already-alerted breaches are suppressed / escalated, not re-fired.

## Steps
1. Call `pm.sla_check(prior_state=<sla block>)`.
2. Read the result:
   - `violations` — every current breach (informational; do **not** post all of these).
   - `alerts_to_send` — the cooldown/escalation-filtered list you actually act on. Each has `item_id`, `title`, `link`, `owner`, `severity`, `type`, `message`, `sla_note`.
   - `state` — the new `sla` block to persist.
3. If `alerts_to_send` is empty, write state back (step below) and stop — a quiet sweep is a valid sweep.

## Posting
- QA-stalled alerts → **#sla-qa-alerts**. All other breach types (Pending-Approval, Blocked, Changes-Requested) → **#sla-violations**. (Channel IDs are set in the cron job.)
- Group into one digest per channel. Use `message`/`sla_note` for the line, link the ticket, name the `owner`.
- **Write-gating:** posting the digest to Remington's own SLA channels is autonomous — post directly. But any **Jira comment** (`trinity.jira_add_comment`), **transition** (`trinity.jira_transition_issue`), or **@-mention escalation** of a person/lead (Level 3/4) is an outward write → **propose → approve → execute**. Draft it, post the proposal, wait for approval, then execute via trinity.

## Write-back
- Take the returned `state` and overwrite the **`## sla`** block in `../STATE.md`, one entry per line in the block's documented schema (`TICKET | breach_type | first_seen | last_alerted | escalation_level | status`). Drop entries the tool marks `resolved`.

## Self-loop guard
- The tool's breach detection may see Remington's own prior SLA comments. Ignore any comment/activity authored by Remington when judging "last update" — dedup on comment/author id so the agent never treats its own nudge as ticket movement.

## Skills
- `../skills/sla-enforcement` (breach logic, escalation matrix), `../skills/sla-alert-deduplication` (cooldown/escalation cadence), `../skills/team-communication` (alert tone).
