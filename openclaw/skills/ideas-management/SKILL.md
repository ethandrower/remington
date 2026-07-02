---
name: ideas-management
description: CiteMed idea intake via Jira Product Discovery (MDP/CI) and linking ideas to implementation (ECD/AI). Duplicate search, idea template, issue-link creation, and the /idea flow. Use for the ideas intake/management on-demand routine.
---

# Ideas Management

CiteMed uses **Jira Product Discovery** for ideas, feeding implementation projects.

**Projects:**
- **MDP** ("Ideas Discovery") — primary ideas project, `Idea` issue type only. `MDP-XXX`.
- **CI** ("Customer Insights") — customer-specific ideas, `Idea` only. `CI-XXX`.
- **ECD** ("Evidence Cloud Development") — implementation: Story/Task/Bug/Epic/Initiative.
- **AI** ("AI Module") — implementation: same types. `AI-XXX`.

**Tooling:** all Jira ops go through `trinity` MCP — `jira_search` (duplicate search),
`jira_create_issue` (idea + implementation), `jira_add_comment` (link documentation).
Replaces the old `mcp__atlassian__*` calls and the raw `curl` to the Jira REST API. Every
create/comment/link is a gated WRITE (propose → approve → execute) — present the idea draft and
proposed links for approval before writing.

## Create a new idea

**1. Search for duplicates first** (avoid clutter):
```
trinity.jira_search(jql='project = MDP AND issuetype = Idea AND status != Done',
                    fields=["key","summary","description","status"])
```
Also scan CI. Present near-duplicates and ask proceed-or-merge before creating.

**2. Create in MDP** (never create Ideas in ECD/AI — they lack the Idea type):
`trinity.jira_create_issue(project="MDP", issuetype="Idea", summary=..., description=...)`.

Description template:
```
## Problem Statement — what user problem does this solve?
## Proposed Solution — the approach, briefly
## User Benefits — bullets
## Design Considerations — key technical / UX notes
## Related Work — links to ECD/AI tickets
## Context — Source (customer/internal/competitive) · Priority · Motivation (why now)
```
Labels: `ux`, category tag, source tag, etc. Summaries are 5–10 words.

## Link idea → implementation

**Preferred — real issue link** via `trinity.jira_edit_issue` / an issue-link tool (or
`trinity.base` raw REST if the high-level call doesn't expose issuelinks — a known port gap):
```
type "Implements": inwardIssue = MDP-96, outwardIssue = ECD-808
```
Link types: **Implements / is implemented by** (idea → story/epic) · **Relates** (general) ·
**Blocks** (dependency). One idea can map to many implementation tickets; one epic can
implement many ideas.

**Fallback — document via comments** on both tickets (`trinity.jira_add_comment`) listing the
implementing tickets + epic, when a real link can't be created.

## Convert an approved idea

1. Create Epic (large) or Story (small) in ECD/AI referencing the MDP idea.
2. Link `MDP-XX "is implemented by" ECD-XXX`.
3. Advance the MDP idea through Discovery → Validated → In Progress → Shipped.

## /idea flow (on-demand)

1. Gather idea details → 2. Search duplicates (MDP + CI) → 3. Present similar, ask proceed/merge
→ 4. Confirm new → 5. Search related ECD/AI stories → 6. Suggest links → 7. User approves links
→ 8. Create MDP idea (gated) → 9. Add comment / create links (gated) → 10. Return the MDP-XXX URL.

## Do / avoid

✅ always create ideas in MDP/CI · descriptive summaries · problem + benefits · relevant labels ·
search before creating · document links when direct linking is unavailable.
❌ Idea tickets in ECD/AI · Stories in MDP · skipping duplicate search · leaving ideas unlinked.
