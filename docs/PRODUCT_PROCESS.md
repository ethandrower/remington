# Product Process — Idea Intake Playbook

How we go from a raw idea ("what if we…") to either a filed scope OR a documented "we already have this." This is the playbook the AI/PM agent follows when the user dumps an idea — instead of jumping to code.

**Where things live in this repo:**
- **Tickets** → Jira (the agent has Atlassian MCP access; tickets are the authoritative source)
- **Feature proposals / design docs** → `docs/<UPPERCASE_NAME>_PROPOSAL.md` (markdown, signed/dated)
- **Implementation summaries** → `docs/<NAME>_IMPLEMENTATION_SUMMARY.md`
- **Decisions** → `docs/<NAME>_DECISION.md`

The playbook fits this structure — Jira holds tickets, docs/ holds the longer scope writeups.

---

## When the playbook triggers

Any time the user says something like:
- "What if we did X?"
- "I'd like to add X."
- "Could the agent also handle Y?"
- "Save this for later."

The AI does NOT immediately start coding. It runs the playbook.

---

## The playbook (4 steps)

### Step 1 — DEDUP CHECK

Verify the idea isn't already implemented or in-flight.

1. **Code search:**
   - `grep -rn "<keyword>" src/ scripts/` for any existing implementation
   - Read the relevant file/function if found
2. **Jira search:** use the Atlassian MCP tools
   - `searchJiraIssuesUsingJql` with `text ~ "<keyword>" AND project = <project_key>` (active + recently closed)
   - Check status — open in current sprint? open in backlog? closed (with reason)?
   - Also search by reporter/assignee if the idea hints at who owns it
3. **Doc search:**
   - `grep -rin "<keyword>" docs/` for any existing proposal or decision doc
   - Read any matches end-to-end
4. **Memory search:**
   - `~/.claude/projects/-Users-ethand320-code-citemed-project-manager/memory/MEMORY.md` for prior context

**Outcome (one of):**
- *"X already exists at <path>:<line>"* → stop. Don't scope.
- *"X has an open Jira ticket: <PROJECT-KEY>"* → stop. Link to it.
- *"X has a recently-closed Jira ticket: <PROJECT-KEY> — closed because Y"* → confirm with user before re-opening.
- *"X has a doc in docs/<NAME>_PROPOSAL.md but no Jira ticket"* → proceed to Step 4 to file the Jira ticket from the existing proposal.
- *"Genuinely new — proceed to Step 2."*

**If a duplicate is found, stop and report.** Don't scope something that already exists.

### Step 2 — ROADMAP CHECK

If novel by code/Jira/doc search, check whether it's covered by an in-flight epic or near-term plan.

1. **Active epics:** JQL `project = <key> AND issuetype = Epic AND status in ("To Do", "In Progress")` — read each epic's description; is the idea adjacent to one?
2. **Sprint context:** check the `feature-queue.md` memory note OR the dashboard's `/api/agent/sprint-report` for what's currently in flight
3. **Decide:**
   - **Fully covered by Epic <KEY>** → file as a child story under that epic
   - **Partially covered** → scope a smaller delta ticket; link to the epic
   - **Not covered** → proceed to Step 3 with a fresh scope

**Outcome:** *"Goes under Epic X"* OR *"Adjacent to Epic X but separate"* OR *"Genuinely standalone — proceed to scope."*

### Step 3 — MVP SCOPE

Write a one-page proposal in `docs/`. Use the template below. The proposal becomes the single source of truth for what the Jira ticket(s) track.

**File path:** `docs/<UPPERCASE_FEATURE_NAME>_PROPOSAL.md`

**Template:**

```markdown
# <Feature Name> - Proposal

**Date:** YYYY-MM-DD
**Author:** PM Agent + <user>
**Status:** Proposal / Design Phase

---

## Origin

What did the user say, when, in what context. 1-3 sentences.
Example: *"Ethan asked on 2026-05-08 during the sprint review — wants automated alerts when a Jira ticket exceeds 24h in QA status."*

## Current State

What exists today that's relevant. Reference code paths and existing Jira tickets.

## User Requirement

Direct quote or paraphrase of what the user wants. Be specific.

## Proposed Solution — MVP

What's the smallest possible implementation that delivers value. Bullet list.
The MVP must be:
- Testable end-to-end
- Defensibly useful even if no further work happens
- Ship-able in one focused work session (target: ≤4 hours, hard cap: 8 hours)

## Out of Scope (deferred)

Bullet list of related ideas we're DELIBERATELY not doing in this proposal.
Each becomes a follow-up Jira ticket if needed.

## Technical Approach

How we build it. Tech-stack choices, integration points (Jira/Bitbucket/Slack APIs),
data model changes, cron/scheduling implications.

## Acceptance Criteria

- Criterion 1 (testable, observable)
- Criterion 2

## Estimate

Total hours (rough): N
Critical path: <which task is the constraint>

## Dependencies

- Depends on: <existing ticket, infra, API access>

## Open Questions

- Q1
- Q2

## Why This Matters

One paragraph: client/user value, or internal velocity gain.
```

### Step 4 — FILE & TRIAGE

Once the proposal is written:

1. **Create Jira ticket(s)** via `createJiraIssue`:
   - Title: short feature name
   - Description: link to the proposal markdown + summary
   - Issue type: Story (or Epic if it'll have multiple child tickets)
   - Components/labels per project conventions
   - Link to parent Epic if any
2. **Update memory** if there's context that won't survive in Jira/docs alone (deadlines, client opinions, internal politics)
3. **State a triage recommendation:**
   - **Do now** — small + high-value + unblocks something
   - **This sprint** — fits remaining capacity
   - **Next sprint** — backlog with priority
   - **Backlog (cold)** — fine to schedule, no urgency
4. **Commit + push the proposal:**
   ```
   git add docs/<NAME>_PROPOSAL.md
   git commit -m "docs: Add <NAME> proposal (Jira: <PROJECT-KEY>)"
   git push
   ```

**Outcome:** Jira ticket on the board, proposal in repo, recommendation to user. User decides do-now vs. do-later.

---

## Anti-patterns (don't do these)

| Anti-pattern | Why it's bad |
|---|---|
| Coding before scoping | Loses audit trail; can't compare against alternatives |
| Skipping the dedup check | Files duplicate of an existing Jira ticket |
| Skipping Jira after writing the proposal | Doc rots without a tracked ticket |
| Skipping the proposal and only filing in Jira | No long-form rationale survives; Jira descriptions get truncated |
| Scoping past MVP | Proposals that estimate "8-15 hours" rarely ship; cut harder |
| Filing without a triage recommendation | User has no signal on whether to act now |
| One giant feature ticket | Should be Epic + multiple child stories if it spans multiple sessions |

---

## Triage levels (priority guide)

| Priority | Definition | Examples |
|---|---|---|
| **P0** | Blocks production / agent operation | Atlassian token rotation; PM agent crash loop |
| **P1** | Direct user value, requested or strongly implied | QA SLA dashboard; new alert channel routing |
| **P2** | Improves quality / unblocks future work | Refactor SLA check internals; better logging |
| **P3** | Nice to have, no urgency | Cosmetic dashboard tweaks; alternate tech-stack experiments |

---

## Example walkthrough (real-style)

> **User:** "What if the agent also pinged us when a PR has been waiting on review for more than 8 hours?"

**Step 1 dedup:**
```
$ grep -rni "review.*sla\|pr.*sla\|review.*alert" src/ scripts/  → no matches
$ searchJiraIssuesUsingJql(jql='text ~ "PR review SLA" AND project = ECD')  → 0 results
$ grep -rin "pr review" docs/  → no matches
```
→ *No existing implementation, no Jira ticket, no proposal.*

**Step 2 roadmap:**
```
$ searchJiraIssuesUsingJql(jql='project = ECD AND issuetype = Epic AND status != Done')  → 3 epics returned
  - Epic ECD-100: "QA SLA Monitoring" — adjacent! covers QA-status SLA, not PR-review SLA
  - Epic ECD-110: "Slack Alert Routing"
  - Epic ECD-120: "Sprint Dashboard"
```
→ *Adjacent to Epic ECD-100. Recommend filing as a sibling story under ECD-100 or as a new "Code Review SLA" epic if more PR-review work is anticipated.*

**Step 3 scope:**
File `docs/PR_REVIEW_SLA_PROPOSAL.md` with:
- MVP: Bitbucket webhook → check open PRs hourly → if any > 8h since last review activity → Slack alert to `#ecd-pr-alerts`
- Out of scope: per-author thresholds, mention rules, automatic re-request reviewer
- Estimate: 3 hours

**Step 4 file & triage:**
- Create Jira story under Epic ECD-100, title "Add PR-review SLA alert (>8h waiting)"
- Priority P2 — adjacent to a working epic, no client deadline
- Recommendation: **This sprint** if capacity allows, otherwise next sprint
- Commit proposal markdown
- Report Jira key + proposal path back to user

---

## Notes

- **Proposal vs. Jira description:** the proposal in docs/ is the long-form thinking; the Jira ticket points to it for context but only carries the title + acceptance criteria. Don't duplicate the entire proposal into Jira — link to it.
- **MVP discipline:** if you find yourself writing >4 hours of estimated work, split into multiple tickets and identify the smallest one as the MVP.
- **When the user says "save for later":** still run the playbook — write the proposal, file the Jira ticket as P3 backlog. Don't actually skip the work. "Save for later" means *don't ship today*, not *don't capture*.
