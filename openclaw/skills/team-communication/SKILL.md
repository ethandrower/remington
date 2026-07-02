---
name: team-communication
description: Slack/Jira messaging craft — escalation templates (Levels 1–4), standup report format, recognition, threading and @mention etiquette. Use when drafting any outward message the write-gate will send, or any escalation.
---

# Team Communication

Every message here is an outward **WRITE**. Under OpenClaw all Slack posts, Jira comments,
and Confluence edits go through the **write-gating standing order** (propose → approve →
execute). These templates are what you *propose*; post only after approval. Slack posting is
OC-native to the channels in `CARD.md` (`#ecd-standup`, `#sla-violations`, `#blocked-tickets`,
`#timesheets`, `#portfolio-health`, `#sprint-planning`, `#pm-agent-logs`); Jira comments go
via `trinity.jira_add_comment`.

## @mention etiquette

**Do mention** for: a direct question needing their response, blocking their work, a review/
approval request, or an escalation to them. **Don't mention** for FYIs, general updates, or
"anyone" questions. In Jira, tag by **account ID** — see the **developer-lookup-tagging** skill.
Use `@channel`/`@here` sparingly.

## Threading

Use threads for detailed discussion, escalation back-and-forth, and follow-up on automated
alerts. Don't bury urgent announcements in threads. Summarize the resolution and close the loop.

## Escalation templates (map to the 4-level matrix in sla-enforcement)

**Level 1 — soft reminder (Jira comment):**
> Hi @dev, gentle reminder that {ITEM} has been waiting {duration}. Could you give a quick
> update when you have a moment? Thanks!

**Level 2 — Jira comment + Slack thread:**
> Hi @dev, {ITEM} is now {X} days overdue (SLA: {threshold}). Please prioritize it or let me
> know if there are blockers. I've opened a Slack thread for visibility.

**Level 3 — team escalation (Slack team channel):**
> 🚨 Escalation: {ITEM} needs attention ({X} days overdue).
> @dev — status update? @tech-lead — advise if re-prioritization is needed.
> This may impact sprint goals. Thread: {link}

**Level 4 — leadership (Slack DM/channel to leadership):**
> ⚠️ CRITICAL ESCALATION — {ITEM} has exceeded SLA ({X} days overdue). Sprint goals at risk.
> Assigned: @dev · Tech Lead: @tech-lead · Impact: {downstream}. Immediate action required.
> Jira: {link} | Thread: {link}

### Scenario templates

**Blocked ticket:**
```
🚫 Blocked Ticket Requires Attention
Ticket: {KEY} — {summary} · Blocked: {X} days · Blocker: {desc} · Assigned: @dev
Action: [ ] @dev status update  [ ] @blocker-owner resolve dep  [ ] @tech-lead re-prioritize
Jira: {link} · SLA: daily updates required for blocked items
```

**Stale PR:**
```
⏰ PR Review Overdue — #{num} {title} · Author: @dev · Requested {X}d ago · SLA 24–48h
Reviewers: @r1 @r2 — can one of you review today? Blocking {KEY}. PR: {link} · Jira: {link}
```

**Code-ticket gap:**
```
⚠️ Potential Stalled Work — {KEY} {summary} · In Progress · Last git activity {X}d ago · @dev
@dev, status update? If blocked or need help, let us know. Jira: {link}
```

## Daily standup report (posted to `#ecd-standup`)

Header line + skimmable sections (bold headers, bullets, links). The standup routine is
7-part; surface each as its own block:

```
🏃 DAILY STANDUP — {date}
📊 SPRINT PROGRESS — Sprint {n} · {done}/{total} ({pct}%) · Epic {KEY} {pct}% · Risk 🟡 {reason}
🚨 CODE-TICKET GAPS ({n}) — {KEY}: @dev In Progress {d}d, no git activity …
⏱️ TIMESHEET GLANCE — total {h}h · avg {h}/dev · most active @dev
📊 SLA ROLL-UP ({n}) — Critical: … / Warnings: … / Recently resolved: …
📋 DoR NUDGES — missing due dates / estimates / stalled refinement (see definition-of-ready)
💡 ACTION ITEMS — [ ] @owner … (tracked in STATE.md `action_items`; close yesterday's first)
```

Detail sections go in the thread. Action items are tracked in the `action_items` STATE.md
block — always close the loop on yesterday's before opening new ones.

## Recognition

Recognize exceptional productivity/quality, going above and beyond, helping teammates,
solving hard problems. Be specific.
```
🌟 Shoutout to @dev — {specific wins: features delivered, zero review iterations, unblocked N teammates}. Great work! 🎉
```

## Stakeholder & incident comms

- **Weekly stakeholder update:** sprint status, key achievements, upcoming milestones,
  risks + mitigations, next-week focus. Strategic tone; lives in leadership surfaces.
- **Incident:** severity, status, impact, timeline, root cause, resolution, prevention, Jira link.

## Anti-patterns

❌ vague updates ("making progress") ❌ `@channel` for non-urgent items ❌ passive-aggressive
tone ("as I already mentioned") ❌ walls of text without formatting ❌ 👍 in place of a real
answer ❌ constructive feedback in public — use a DM.
