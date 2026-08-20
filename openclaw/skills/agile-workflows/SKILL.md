---
name: agile-workflows
description: Agile ceremony playbook — sprint planning, standups, reviews, retrospectives, backlog refinement, velocity/capacity math, and sprint health metrics. Use when planning sprints, running the standup routine, or analyzing sprint health.
---

# Agile Workflows

Reference for the ceremonies Remington runs or reports on. Sprint/velocity data comes from
`trinity` (`jira_get_active_sprint`, `jira_get_sprint_issues`,
`jira_get_completed_sprint_issues`, `jira_get_boards`) and `pm` compute
(`daily_priorities`, `timesheet`, sprint-slate tools). Any ticket write or slate application
is a gated write (propose → approve → execute) — in sprint planning only `apply_sprint_slate`
writes.

## Sprint planning

**Agenda (2–4h / 2-wk sprint):** goal definition → backlog refinement → capacity planning →
story selection → task breakdown.

- **Story sizing:** relative (points / t-shirt). Completable in 3–5 days; break down >8 pts.
  Every story has acceptance criteria.
- **Epic balance:** target 60–70% epic work, 30–40% bugs/maintenance.
- **Capacity:** reserve ~20% for bugs, ~10–15% for reviews; account for PTO/holidays/meetings.
- **Dependencies:** identify external deps early; create blocker tickets; plan mid-sprint resolution.

## Daily standup

The automated standup routine (09:00 ET, M–F, `#ecd-standup`) is 7-part: burndown · code↔ticket
gaps · productivity · timesheet glance · SLA roll-up · DoR nudges · action items — plus
per-person daily priorities. Format lives in the **team-communication** skill.

Human standup principles still apply: discuss work items not people, surface impediments,
time-box, defer deep dives, and produce clear owners + next steps for at-risk items.

## Sprint review

Recap goals → demo working software (not slides) → epic progress → metrics (velocity vs
planned, completion rate, bugs in/out, SLA compliance) → stakeholder feedback (capture as
tickets immediately). Show incomplete work honestly and explain why.

## Retrospective

Team-private, rotating facilitator, psychological safety (systems not individuals).

- **Start / Stop / Continue** or **4Ls** (Liked / Learned / Lacked / Longed for).
- Limit to 3–5 concrete action items with owners; follow up on last retro's items.
- Bring data: velocity, SLA compliance, bug rate, productivity audit (`pm.pm_audit`).

## Backlog refinement (weekly, ~1h)

Clarify upcoming stories, add acceptance criteria, identify deps, estimate, break down large items.

**Definition of Ready** (see also the **definition-of-ready** skill for enforcement):
- [ ] Story in "As a … I want … so that …" form
- [ ] Acceptance criteria clear and testable
- [ ] Dependencies identified/documented
- [ ] Technical approach discussed
- [ ] Sized/estimated
- [ ] No major open questions

## Definition of Done

Story is Done when: code written to standard · unit + integration tests passing · peer
reviewed/approved · docs updated · AC met/verified · PR merged · deployed to staging · PM
approved · no critical bugs.

Sprint is Done when: goal met or explicitly de-scoped · all Done stories meet DoD · incomplete
work returned to backlog · review + retro held · metrics recorded.

## Velocity & capacity

```
sprint_velocity   = sum(points of completed stories)   # or completed-ticket count
average_velocity  = mean(last 3 sprints)
next_capacity     = average_velocity * 0.9   # 90% confidence
bug_reserve       = next_capacity * 0.2
epic_capacity     = next_capacity * 0.8
```
Trend: rising = improving; stable = sustainable; falling = investigate bottlenecks / tech debt
/ team changes. Never compare velocity across teams or use it as a performance metric.

## Sprint health metrics

- **Burndown** — warn if it flatlines mid-sprint.
- **SLA compliance** — target ≥ 90%, improving.
- **Code-ticket gap rate** — target < 5% of In-Progress tickets without git activity.
- **PR review time** — target < 48h to first review.
- **Bug escape rate** — decreasing trend.
- **Cumulative flow** — watch where work piles up (bottleneck).

## Anti-patterns

❌ overcommitting / skipping capacity planning ❌ accepting stories without AC ❌ standups that
become status-to-manager or ignore blockers ❌ skipping retros or not acting on outcomes ❌
gaming story points / sacrificing quality for velocity.
