# Task: DB Cleanup / Retention

**Cadence:** Daily, overnight — `0 3 * * *` ET.
**Purpose:** Housekeeping only. Prune stale checkpoints / retention rows if any remain.

> **Mostly obsolete in the OpenClaw world.** In the Heroku monolith this pruned SQLite alert-trackers and LangGraph checkpoint tables. Under OpenClaw, cross-run memory lives in `../STATE.md`, and checkpointing is the gateway's concern — there is no PM-owned database to prune. Keep this routine minimal; it is a safety-net, not a data pipeline.

---

## State in
- None. This routine does not read or write any `../STATE.md` block — the state blocks are curated by their owning routines (sla-sweep, blocked-analysis, standup, portfolio-audit, pm-self-audit) and must not be pruned here.

## Steps
1. If the gateway exposes a checkpoint/retention prune primitive, invoke it. Otherwise there is nothing to do — the monolith's SQLite tables no longer exist in this deployment.
2. Optionally sanity-check `../STATE.md` size: if any block has grown with long-resolved entries, note it (do **not** auto-prune — the owning routine drops resolved rows on its own next run).

## Posting
- Post a one-line liveness/no-op summary to **#pm-agent-logs** (channel ID in cron) — autonomous, post directly. No Jira/Slack broadcast writes; no write-gating.

## Write-back
- None.

## Self-loop guard
- N/A — no comments or messages are read.

## Skills
- None.
