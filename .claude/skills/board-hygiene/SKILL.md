---
name: board-hygiene
description: Detects and reports Jira board decay — work that shipped but was never closed, tickets orphaned under dead or missing parents, duplicate twins, and phantom issue keys. Use when running a periodic board sweep, when asked why the plan looks messy, before triaging an initiative, or when a ticket's status seems not to match reality. Surfaces candidates with evidence for a human to decide; never closes or reparents on its own.
---

# Board Hygiene Skill

## Purpose

Jira decays in predictable ways. This skill describes the decay patterns, the sweeps that find them, and the verification discipline that stops a sweep from doing damage.

It was written from a large ECD cleanup (August 2026) that closed 18 initiatives, adopted 15 parentless epics and rehomed roughly 90 items. Every pattern below was observed repeatedly, not theorised.

## The one rule that matters

**Detect and report. Do not close, decline, or reparent autonomously.**

Every correct close in that cleanup required reading the actual code to confirm the work had shipped, and several required a product decision only a human could make. A sweep acting on ticket metadata alone will close live work and keep dead work.

Your output is a triage list with evidence attached, for a human to act on.

## Decay pattern 1 — shipped but never closed

**The single most common defect.** It appeared in *every* initiative examined.

Symptom: a ticket sits in Draft, In Progress, QA, Pending Approval or Changes Requested while its code is merged on `develop`. Sometimes the ticket's own description says `Status: SHIPPED` with a PR number, and it is still open.

Observed: ECD-2117 and ECD-2118 both said "Status: SHIPPED" in their descriptions while sitting Draft / In Progress. Fourteen of twenty-nine open stories under one initiative were already delivered. AI-90 and AI-97 were merged and released while reading In Refinement / Pending Approval.

### The sweep

```
project = ECD AND statusCategory != Done
  AND status in ("Pending Approval", "Changes Requested", "QA", "Blocked", "In Refinement")
  AND updated <= -14d
ORDER BY updated ASC
```

For each hit, report:

- the ticket, its status, and how long it has been stale
- whether its description mentions a PR number or the word "shipped"
- **a code check** — does the thing it describes exist on `develop`?

The code check is what makes this useful. Without it you have produced a list of old tickets, which everyone already knows about.

### Verifying against code — the traps

- **Route on the description, not the summary.** ECD-1710 is titled "Configurable table defaults"; its body is entirely about the Performance Benefits *report builder*. ECD-2018 reads "failed Literature workflows"; its body is about report generation.
- **Never conclude "absent" from a truncated search.** A `head -5` on a grep once hid `pdf_stamp.py` and produced a confident, wrong "not built" conclusion. Re-run unbounded, and vary the term — the feature was called "stamp", not "watermark".
- **File existence is weak evidence; wiring is strong.** A module can exist without being reachable. Prefer URL routes, registered handlers, call sites, or a component actually imported and mounted.
- **A docstring naming the ticket is the strongest evidence there is.** The `ArticleFieldOverlay` model's docstring reads "(ECD-1273 / MDP-170)". Always grep the codebase for the issue key itself.

## Decay pattern 2 — orphans and dead parents

Three distinct problems. Run all three; they surface different things.

### 2a. Parentless epics

```
project = ECD AND type = Epic AND parent IS EMPTY AND statusCategory != Done
```

Invisible to every initiative-level view, and to Jira Plans, where parentless items land in an ungrouped pile at the bottom. Fifteen were found holding **61 open items** between them — including an IDOR security remediation with 8 live children, and four epics that were In Progress.

### 2b. Initiatives with no children

```
project = ECD AND type = Initiative AND statusCategory != Done
```

…then check each for children. An initiative with none is either finished or was never started; both are worth surfacing.

### 2c. Open work under a Complete / Declined parent

There is no single JQL for this. Fetch all open issues that have a parent, collect the distinct parent keys, look up their statuses, and report any child whose parent is `Complete` or `Declined`.

This is the nastiest pattern, because **the work looks fine on the ticket and is invisible everywhere else**. Two sub-tasks sat Blocked *in the active sprint* under a Complete story — nobody could see them to unblock them. A Critical bug sat unnoticed for four months inside a parentless bug-bash epic.

### Run the census BEFORE triaging, not after

A stranded ticket is invisible, so **the twin you can see is often the worse copy**. Twice during the cleanup the wrong duplicate was demoted: ECD-1404 said in its own first line "Consolidates ECD-1225" and carried the fuller text, but was stranded under a Complete parent, so only ECD-1225 was visible. Same with ECD-1631 (real content) and ECD-1632 (empty) — the empty one got rehomed.

### Sweep deeper than one level

After declining or closing anything, re-run the stranded check **against the items you just closed**, not only their parents. A cleanup that checked one level missed eight grandchildren under a declined epic, and separately stranded ECD-1177 by checking a parent but not its child.

## Decay pattern 3 — duplicate twins

Symptoms: identical or near-identical summaries; one empty and one with content; one saying "Consolidates ECD-XXXX"; a formal `is cloned by` link.

Group open issues by normalised summary and report collisions, and check clone links explicitly.

ECD-1176 and ECD-1982 were formally linked clones, both open, with **different assignees and different sprints** — two people could have built the same thing.

When you find a pair, report which has the fuller description and which is newer. The survivor is usually the one with content, not the one with the later key.

## Decay pattern 4 — phantom keys

**Four were found in one cleanup.** Initiative descriptions and definition-of-done lists routinely cite issue keys that do not exist — never created, or renumbered:

- ECD-1618 (Clio V1 charter), ECD-273 (RightFind epic), ECD-1709 (Reports Experience DoD), ECD-70 (Search Refinement DoD)

Jira never validates keys written inside description text. Extract every `ECD-\d+` / `AI-\d+` from initiative and epic descriptions, resolve each, and report the misses. Cheap to run, and it stops people treating a phantom as a real dependency.

## Routing: where homeless work belongs

Route by **subsystem**, into the July 2026 functional taxonomy.

Do not create release-named or quarter-named buckets. That pattern failed twice — ECD-1063 "Q1 2026 Bugs" and ECD-1623 "Demo Day Bug Bash V6.0.1" — and the second hid a Critical bug for four months. A release number records *when a thing was found*, not *what is broken*, so it tells nobody who should fix it. Release provenance belongs in `fixVersion`, which is a field, not a hierarchy.

The taxonomy initiatives are **permanent functional homes**, not delivery vehicles. Do not close one because its epics finished — ECD-2339 "Platform & Demo Tooling" was closed that way, and platform work then had nowhere to go at all.

A useful test for a Story: *does it sit in an epic under an initiative someone is actually driving?* If not, that is the signal it should not be worked, not a filing problem. Bugs are exempt — they are reactive and independent.

## Hierarchy constraints that will bite you

Jira rejects these outright with *"Given parent work item does not belong to appropriate hierarchy"*:

- A **Story or Task cannot be parented to an Initiative** — it needs an Epic.
- An **Epic cannot be parented to an Epic** — it needs an Initiative.
- A **Sub-task cannot be parented to an Epic or Initiative** — only to a Story / Task.

That last one is a dead end: **sub-tasks stranded under a Complete story can never be rehomed into the taxonomy.** They must be closed, rewritten as Stories, or have their parent reopened. Report them separately from ordinary stranding, because the remedy is different.

Cross-project parenting (AI-* under ECD-*) does work.

## Verification discipline

- **Verify writes with a direct issue fetch, never with search.** The search index lags by minutes; freshly-moved issues still report their old parent. Every confirmation in the cleanup used `show`, not `search`.
- **Check `sprint.state`, not just sprint presence.** A ticket in a *closed* sprint reading "In Progress" is not scheduled — it only looks alive. A direct fetch returns `sprint.state`; JQL search does not populate the sprint field at all. This single check reframed an entire initiative: not one of its 21 open items was in the active sprint.
- **"Deliberately left alone" decisions expire.** Three epics were spared an earlier sweep because "their initiative is active". When that initiative later closed, the reasoning silently became invalid. Re-check anything spared on a conditional.
- **Distinguish "not built" from "not hardened".** An epic's headline features can be shipped while its hardening tickets are genuinely outstanding. Never close a whole epic on the strength of its most visible child.

## What good output looks like

For each finding: the key, the pattern it matches, the evidence (a file path, a PR number, a docstring quote, a JQL result), and a **proposed** action — close as delivered / decline as superseded / fold into X / rehome to Y / needs a human decision. Group by cluster so a human can act on ten related items at once.

Flag separately and loudly:

- anything security-shaped — credentials in source, missing rate limits, permission gaps. These should never sit quietly in a triage queue.
- anything marked Critical, or sitting in the active sprint
- any ticket whose own description says it shipped

## Suggested cadence

- **Weekly:** the stale-status sweep (pattern 1). It is the highest-yield and the cheapest.
- **Fortnightly:** the orphan census (pattern 2). Parentless epics accumulate fastest after a burst of ticket creation.
- **Before any initiative triage:** the full census, so you are not triaging against a partial picture.
- **Monthly:** phantom keys and duplicate twins. Slower-moving, but each one silently misleads planning until found.
