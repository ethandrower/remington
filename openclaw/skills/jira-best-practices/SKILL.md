---
name: jira-best-practices
description: Jira ticket standards — story/title/AC formatting, workflow statuses, comment etiquette, issue links, JQL patterns, custom fields, and ticket hygiene. Use when drafting/linting tickets, running JQL via trinity, commenting, or transitioning issues.
---

# Jira Best Practices

Standards Remington enforces and follows. Jira access is via `trinity` MCP:
`jira_search` (JQL), `jira_get_issue`, `jira_get_transitions`, `jira_get_status_history`,
`jira_add_comment`, `jira_transition_issue`, `jira_edit_issue`, `jira_create_issue`. Mechanical
ticket standards are also checked by `pm.lint_ticket` / drafted by `pm.draft_ticket`.

**Every comment, transition, edit, and create is a WRITE** → propose → approve → execute
(write-gating standing order). A JQL read that finds a problem is not permission to comment.

## Ticket creation

**User story:** `As a [persona], I want [goal], so that [benefit].`

**Titles:** start with a verb (Add/Fix/Implement/Update/Refactor), be specific, <100 chars,
include the feature/module. ✅ "Add bulk reference upload to project library" ❌ "Bug fix".

**Acceptance criteria — Given/When/Then:** testable, happy path + error cases + edge cases.
```
- Given I am a logged-in user with project access
- When I upload a valid .ris file
- Then all valid references import to the library
```

**Technical details (when relevant):** implementation approach, API endpoints, DB changes,
dependencies (blocks / is blocked by).

**Labels:** `bug` `enhancement` `tech-debt` `documentation` `urgent` `blocked` `research`
`quick-win`. **Components:** `frontend` `backend` `api` `database` `infrastructure`
`word-addon` `authentication`.

## Workflow

`To Do → In Progress → In Review → In QA → Pending Approval → Done` (with `Blocked` as a
temporary side state). Note the DoR-enforced statuses: **In Refinement**, **Ready for
Development**, **Ready for QA** (see the definition-of-ready skill).

Transition rules:
- **→ In Progress:** create git branch with the ticket key; comment the approach.
- **→ In Review:** PR opened + linked; reviewers tagged; self-reviewed.
- **→ Blocked:** comment the blocker, tag who can unblock, estimate resolution; daily updates.
- **→ Done:** AC checked off, PM approval documented, deployed, closing summary comment.

## Comment etiquette

✅ "Implementation complete. Ready for review. PR #123" · "Blocked on backend API. @dev ETA for
ECD-456?" ❌ "Done" · "Working on it" · "@everyone URGENT".

**Status update template:** Progress / Blockers / Next steps / ETA.
**Blocker template:** ⚠️ BLOCKED — what's needed, blocked-since date, who from, sprint impact,
estimated unblock date.

Tag only when you need a specific person to act; tag by **account ID** (see the
**developer-lookup-tagging** skill).

## Issue links

**Blocks / Is blocked by** (dependency) · **Relates to** (association) · **Duplicates** ·
**Parent / Subtask** (limit 3–7 subtasks) · **Epic Link**. Be explicit about what blocks what;
update when resolved. For idea→implementation links see the **ideas-management** skill.

## JQL patterns

```jql
# Current sprint
project = ECD AND sprint in openSprints()
# Blocked, oldest first
project = ECD AND status = Blocked ORDER BY created ASC
# Code-ticket gaps (In Progress, stale)
project = ECD AND status = "In Progress" AND updated < -2d
# PR review bottleneck
project = ECD AND status = "In Review" AND updated < -2d
# Stories without an epic
project = ECD AND "Epic Link" is EMPTY AND type = Story
# Unassigned To Do
project = ECD AND status = "To Do" AND assignee is EMPTY
```
Use `ORDER BY` for readability and relative dates (`-1d`, `-1w`) for dynamic queries. The
project key is env-driven (`ATLASSIAN_PROJECT_KEY`) — don't hardcode `ECD` in production logic;
it's shown here as the concrete example.

## Custom fields

`Epic Link` = `customfield_10014` · `Story Points` = `customfield_10016` · `Sprint` =
`customfield_10020` · Due date = `duedate` · Original estimate = `timeoriginalestimate`
(seconds; 28800 = 8h). Some of these aren't exposed by `trinity.jira` high-level calls; the
`pm` routines reach them via `trinity.base` raw REST (issuelinks, parent, duedate, changelog).

## Ticket hygiene

**Daily:** update tickets you're working, respond to comments, move through workflow promptly.
**Weekly:** clear stale items, close what's actually done, un-assign what you won't do, fix
estimates on scope change.

Anti-patterns: ❌ zombie tickets (In Progress for months) ❌ kitchen-sink tickets ❌ novel-length
descriptions ❌ vague AC ("make it work") ❌ missing context ❌ eternal blockers without escalation.
