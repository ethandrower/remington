# Task: Portfolio Health Audit

**Cadence:** Weekly, Monday morning — `45 9 * * 1` ET (time TBD).
**Purpose:** Run the 7 initiative/epic hygiene signals across the portfolio and report per-initiative health with a trend vs last week.

---

## State in
- Read the **`initiatives`** block from `../STATE.md` (`INITIATIVE | last_audit_date | health_signals_snapshot | trend`).
- Parse to a dict keyed by initiative and pass as `prior_state` so the tool can carry a trend (improving / flat / declining) against last week's snapshot.

## Steps
1. Call `pm.portfolio_audit(prior_state=<initiatives block>)`.
2. Read the result:
   - `records[]` — per initiative/epic: `key`, `summary`, `findings[]` (each with `code`, `severity` critical/warning/info, `message`), `epic_count`, `active_epic_count`, `done_epic_count`, `link`.
   - `counts` — portfolio rollup (`total_initiatives`, `total_epics`, `total_findings`, severity tallies).
   - `state` — the new `initiatives` block (snapshot + trend).
3. Prioritize by severity: lead the digest with `critical` findings, then `warning`; fold `info` into a summary line.

## Posting
- Post the health digest to **#portfolio-health** (channel ID in cron) — autonomous, post directly. Per initiative: name, health line, notable findings with links, and trend arrow vs last week.
- Any **Jira comment/edit** on an initiative or epic (e.g. flagging a hygiene gap on the ticket) or **@-mention escalation** is an outward write → **propose → approve → execute** via trinity. The digest itself does not write to Jira.

## Write-back
- Overwrite the **`## initiatives`** block in `../STATE.md` from the returned `state`: one line per initiative with fresh `last_audit_date`, `health_signals_snapshot`, and computed `trend`. Prune initiatives that are Done/closed.

## Self-loop guard
- Hygiene signals are structural (links, estimates, status, dates), not comment-based — low self-loop risk. If a signal reads comment activity, ignore Remington-authored comments (dedup on id).

## Skills
- `../skills/jira-best-practices` (initiative/epic hierarchy, hygiene signals), `../skills/agile-workflows` (portfolio/roadmap framing).
