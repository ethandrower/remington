# Remington — Working State

Agent-maintained. **Read the relevant block at routine start; write it back at routine end.**
Keyed by Jira ticket / initiative id. This is curated working state (the "what's the status of
my tasks" memory), NOT episodic logs — keep it small and current; prune resolved entries.

See [`ROUTINES.md`](ROUTINES.md) for which routine owns which block.

---

## sla
<!-- SLA sweep. key = ticket. track so we don't re-alert the same violation every hour. -->
<!-- entry: TICKET | breach_type | first_seen | last_alerted | escalation_level | status(open/resolved) -->

_(none yet)_

## blocked
<!-- Blocked-ticket analysis. key = ticket. distinguish still-blocked vs resumed vs needs-response. -->
<!-- entry: TICKET | flagged_date | last_state(blocked/resumed/response-needed) | last_comment_id_seen -->

_(none yet)_

## action_items
<!-- Standup. key = item id. close the loop: did yesterday's item resolve? -->
<!-- entry: ID | created_date | description | owner | status(open/resolved) | source_ticket -->

_(none yet)_

## initiatives
<!-- Portfolio health audit. key = initiative/epic. snapshot health signals to show trend. -->
<!-- entry: INITIATIVE | last_audit_date | health_signals_snapshot | trend(improving/flat/declining) -->

_(none yet)_

## dor_nudges
<!-- Standup DoR + ticket-lint. key = ticket. avoid re-nagging the same gaps. -->
<!-- entry: TICKET | nudged_date | gaps_flagged -->

_(none yet)_

## self_audit
<!-- PM self-audit. key = sprint id. feeds weekly reflection. -->
<!-- entry: SPRINT_ID | date | score | notable_misses -->

_(none yet)_
