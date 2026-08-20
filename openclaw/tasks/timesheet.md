# Task: Weekly Timesheet / Worklog

**Cadence:** Weekly, Monday morning — `30 9 * * 1` ET.
**Purpose:** Report logged hours vs estimates per developer for the completed week; flag over-estimate and under-logged outliers.

---

## State in
- **Stateless** routine — no required STATE.md block. Optional: keep a light hours-per-dev trend vs prior weeks if you maintain one, but there is no owned block. Do not write STATE.md.

## Steps
1. Call `pm.timesheet(week_offset=0)` — `week_offset=0` is the last complete week. (Use `current_week=True` only for a mid-week snapshot on request.)
2. Read the result:
   - `developers[]` — per dev `name`, `logged_seconds`, `estimate_seconds`, `issues[]`, plus human-readable rollups.
   - `team_total_seconds` / `team_total_human`, `week_label`, `week_start`, `week_end`.
3. Compute/flag outliers: logged far below estimate (under-logging) and issues where logged ≫ estimate (over-estimate / scope creep). Use the per-issue `entries` to attribute.

## Posting
- Post the weekly report to **#timesheets** (channel ID in cron) — autonomous digest to Remington's own channel, post directly.
- This is a **read-only** routine: do not comment on or edit any Jira issue. If a flag warrants a Jira nudge or @-mention, that is an outward write → **propose → approve → execute** via trinity (kept separate from the digest).

## Write-back
- None. (No STATE.md block owned by this routine.)

## Self-loop guard
- Not applicable — worklog data is developer-authored; Remington logs no work. If you cross-reference comments for context, still ignore Remington-authored ones.

## Skills
- `../skills/agile-workflows` (estimation vs actuals), `../skills/team-communication` (report tone). No SLA/DoR skill needed.
