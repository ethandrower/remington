---
name: developer-lookup-tagging
description: Identify the right developer for a ticket and tag them by Jira account ID in automated comments. Assignment priority order, lookup via trinity, mention format, and anti-spam rules. Use before posting any developer-targeted Jira comment.
---

# Developer Lookup & Tagging

Reliable developer identification and tagging for automated PM comments. Always resolve to an
**account ID** — that is what triggers a real Jira notification.

## Step 1 — Identify the developer

Priority order:
1. **Current assignee** — `trinity.jira_get_issue` → `assignee` (`displayName`, `accountId`).
2. **Recent git activity** — the developer committing on the related branch. Get PR/commit
   authors via `trinity.bitbucket_list_pull_requests` / `bitbucket_get_pr_activity` (repos:
   `citemed_web`, `citemed_ai`). This replaces shelling out to `git log`.
3. **Historical assignee** — from changelog (`jira_get_status_history` / raw changelog).
4. **Epic owner** — if the story rolls up to an epic with a clear owner.
5. **Default team assignment** — fallback by ticket type.

## Step 2 — Look up the account ID

```
trinity.jira_lookup_user(query="First Last")  →  accountId
```
Replaces the old `mcp__atlassian__lookupJiraAccountId`. Cache resolved IDs in working memory
for the run; refresh when a lookup fails, a new committer appears, or ~monthly.

Known IDs (verify via lookup; roster is env-driven — `TEAM_MEMBER_*` / Confluence sync):
- Ethan Drower — `712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e`
- Mohamed Belkahla — `712020:27a3f2fe-9037-455d-9392-fb80ba1705c0`

## Step 3 — Tag in the comment

Mention format is the Jira account-ID mention: `[~accountid:ACCOUNT_ID]`. Post via
`trinity.jira_add_comment` — a gated WRITE (propose → approve → execute).
```
🚨 PM Analysis Alert: [~accountid:{ACCOUNT_ID}]
No git activity on this In-Progress ticket in 3 days. Different branch? Status update needed?
Sprint deadline {date} at risk.
```

**Fallback** (if account-ID mention is rejected/escaped by the instance, as older monolith
runs saw): target by **bold name** — `**@Mohamed Belkahla** — {message}` — so the developer is
still clearly identified. Try the account-ID mention first; fall back on failure.

## Comment templates by scenario

- **Gap detection (no git activity):** ask if work is on another branch / status needs updating;
  note sprint deadline risk.
- **Status mismatch (code merged but still In Progress):** ask whether it should be Complete.
- **Productivity recognition:** call out strong code-ticket alignment (commits, PR merged, on
  schedule) — keep recognition specific.
- **Code without ticket:** note the branch + commit count and ask to link/create the ticket.

Full escalation wording lives in the **team-communication** skill.

## Anti-spam rules

- Don't tag on draft tickets (no action needed yet).
- Don't re-comment if updated < 24h ago, or if the same person was already tagged for the same
  issue within 48h. (Cross-check the relevant STATE.md block — `sla` or `dor_nudges` — for
  what's already been alerted.)

## When to tag multiple people

Epic owner + story dev (epic-level issues) · tech lead + dev (process violations) · whole team
(sprint-wide concerns). Otherwise tag one owner. On lookup failure: post untagged rather than
guess.
