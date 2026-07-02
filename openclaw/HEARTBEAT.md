# HEARTBEAT.md

The global 30-minute heartbeat is a **cheap backstop**, not your scheduler. Your real
routines run on cron (`cron/jobs.json`) at their proper times. On a heartbeat, do the
minimum and stay quiet unless something is genuinely urgent.

## On each beat (business hours only)

1. It is **not** your job to re-run standup/SLA/blocked here — cron owns those. Do not duplicate a routine that has its own cron job.
2. Quick urgency check only: is there anything freshly on fire that can't wait for the next scheduled run? (e.g. a ticket that just crossed a hard SLA breach and has no `sla` STATE.md entry yet.) If and only if so, handle it per the relevant `tasks/*.md`, obeying the write-gate.
3. Otherwise: do nothing and end the beat. Silence is correct. Do **not** post a liveness ping every beat — noise erodes trust in the channel.

## Never on a heartbeat
- No outward writes without the propose→approve gate.
- No re-alerting anything already tracked in `STATE.md`.
- No reacting to your own prior messages (self-loop guard).
