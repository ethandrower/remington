---
name: agile-workflows
description: Provides knowledge and best practices for agile software development workflows including sprint planning, daily standups, sprint reviews, retrospectives, backlog refinement, and velocity tracking. Use when planning sprints, conducting standups, analyzing sprint health, tracking velocity, or improving agile processes.
---

# Agile Workflows Skill

## Purpose
This skill provides knowledge and best practices for agile software development workflows, including sprint planning, daily standups, retrospectives, and agile ceremonies.

## Sprint Planning

### Sprint Planning Ceremony

**Duration:** 2-4 hours per 2-week sprint
**Participants:** Development team, Product Manager, Tech Lead

**Agenda:**
1. **Sprint Goal Definition** (30 min)
   - What business value will this sprint deliver?
   - What epic progress will be achieved?
   - Clear, measurable outcome statement

2. **Backlog Refinement** (45 min)
   - Review prioritized backlog
   - Ensure stories have acceptance criteria
   - Clarify requirements and dependencies
   - Break down large stories if needed

3. **Capacity Planning** (30 min)
   - Calculate team capacity (account for holidays, PTO)
   - Reserve 20% capacity for bugs and unexpected work
   - Account for ongoing commitments

4. **Story Selection** (60 min)
   - Team pulls stories from backlog based on priority
   - Discuss implementation approach
   - Identify technical risks
   - Commit to sprint scope

5. **Sprint Task Breakdown** (30 min)
   - Break stories into tasks
   - Assign initial ownership
   - Identify cross-team dependencies

### Sprint Planning Best Practices

**Story Sizing:**
- Use relative sizing (story points or t-shirt sizes)
- Stories should be completable within 3-5 days
- Break down stories larger than 8 points
- Include acceptance criteria for every story

**Epic Integration:**
- Map sprint stories to parent epics
- Ensure epic progress is balanced with maintenance work
- Target: 60-70% epic work, 30-40% bugs/maintenance

**Dependency Management:**
- Identify external dependencies early
- Create blocker tickets for dependencies
- Plan for dependencies to be resolved mid-sprint

**Capacity Considerations:**
- Account for meetings, reviews, planning overhead
- Reserve capacity for code reviews (10-15%)
- Plan for production support rotation

## Daily Standups

### Standup Format (Traditional)

**Duration:** 15 minutes maximum
**Participants:** Development team

**Each person answers:**
1. **What did I accomplish yesterday?**
   - Completed work, progress made
   - Link to tickets where possible

2. **What will I work on today?**
   - Planned tasks and goals
   - Focus areas

3. **Any blockers or impediments?**
   - Issues preventing progress
   - Help needed from team

### Standup Format (Automated via PM Agent)

**Duration:** Report generation + discussion
**Execution:** Automated daily via `/standup` command

**Report Sections:**
1. Sprint burndown and epic progress
2. Code-ticket gaps (stalled work)
3. Developer productivity insights
4. Team timesheet summary
5. SLA violations and follow-up actions

**Team Discussion Focus:**
- Address critical blockers immediately
- Review SLA violations and escalations
- Adjust priorities based on sprint risk
- Coordinate cross-team dependencies

### Standup Best Practices

**Focus on Flow:**
- Discuss work items, not people
- Identify impediments blocking progress
- Keep it time-boxed (strict 15 min)
- Defer detailed discussions to after standup

**Actionable Outcomes:**
- Clear owners for unblocking work
- Next steps defined for at-risk items
- Follow-up meetings scheduled if needed

**Remote Team Considerations:**
- Async standup updates via Slack
- Synchronous video standup 2-3x per week
- Written summaries for timezone differences

## Sprint Reviews

### Sprint Review Ceremony

**Duration:** 1-2 hours per 2-week sprint
**Participants:** Development team, Product Manager, Stakeholders

**Agenda:**
1. **Sprint Goals Review** (10 min)
   - Recap sprint objectives
   - Review success metrics

2. **Demo Completed Work** (45-60 min)
   - Live demonstrations of new features
   - Show working software, not slides
   - Each developer presents their work
   - Gather stakeholder feedback

3. **Epic Progress Update** (15 min)
   - Show advancement on strategic epics
   - Demo epic milestones achieved
   - Discuss remaining epic scope

4. **Sprint Metrics** (10 min)
   - Velocity achieved vs. planned
   - Completion rate
   - Bugs introduced vs. resolved
   - SLA compliance rate

5. **Stakeholder Feedback** (20 min)
   - Gather input on demonstrated work
   - Identify additional requirements
   - Adjust backlog priorities

### Sprint Review Best Practices

**Demo Preparation:**
- Test demos in production-like environment
- Have backup plans for technical issues
- Focus on user-facing value, not technical details
- Keep demos interactive and engaging

**Feedback Capture:**
- Document all stakeholder input
- Create follow-up tickets immediately
- Prioritize feedback for next sprint planning

**Transparency:**
- Show incomplete work and explain why
- Discuss challenges and lessons learned
- Be honest about sprint struggles

## Sprint Retrospectives

### Retrospective Ceremony

**Duration:** 1-1.5 hours per 2-week sprint
**Participants:** Development team (private, no stakeholders)
**Facilitator:** Rotate among team members

**Format: Start-Stop-Continue**

**What should we START doing?**
- New practices or tools to try
- Process improvements to adopt
- Collaboration approaches to experiment with

**What should we STOP doing?**
- Ineffective practices to eliminate
- Wasteful processes to remove
- Habits that slow us down

**What should we CONTINUE doing?**
- Effective practices to maintain
- Successes to build upon
- Team strengths to leverage

### Alternative Format: 4Ls

**Liked:**
- What went well this sprint?
- What did we enjoy?

**Learned:**
- What new insights did we gain?
- What skills did we develop?

**Lacked:**
- What was missing this sprint?
- What resources did we need?

**Longed For:**
- What do we wish we had?
- What would make us more effective?

### Retrospective Best Practices

**Psychological Safety:**
- Create blame-free environment
- Focus on systems, not individuals
- Encourage honest, constructive feedback
- What's said in retro stays in retro

**Actionable Outcomes:**
- Limit to 3-5 concrete action items
- Assign owners for each action
- Follow up on previous retro actions
- Track improvement over time

**Data-Driven Insights:**
- Review sprint metrics (velocity, SLA compliance, bug rate)
- Analyze productivity audit results
- Identify patterns from multiple sprints
- Use PM agent reports to inform discussion

**Continuous Improvement:**
- Experiment with one new practice per sprint
- Measure impact of process changes
- Iterate on team workflows
- Celebrate improvements achieved

## Backlog Refinement

### Refinement Session

**Duration:** 1 hour per week
**Participants:** Development team, Product Manager

**Goals:**
- Clarify upcoming stories
- Add acceptance criteria
- Identify technical dependencies
- Estimate story complexity
- Break down large items

### Refinement Best Practices

**Story Readiness:**
- Well-defined acceptance criteria
- Clear business value statement
- Technical approach discussed
- Dependencies identified
- Estimated within reasonable range

**Definition of Ready:**
- [ ] User story follows "As a [persona], I want [goal], so that [benefit]" format
- [ ] Acceptance criteria are clear and testable
- [ ] Dependencies identified and documented
- [ ] Technical approach discussed with team
- [ ] Sized/estimated by team
- [ ] No major open questions or uncertainties

## Definition of Done

### Story Completion Criteria

A story is "Done" when:
- [ ] Code is written and follows coding standards
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing (if applicable)
- [ ] Code reviewed and approved by peer(s)
- [ ] Documentation updated (inline comments, README, etc.)
- [ ] Acceptance criteria met and verified
- [ ] PR merged to main branch
- [ ] Deployed to staging environment
- [ ] Product Manager has approved functionality
- [ ] No critical bugs or issues remaining

### Sprint Completion Criteria

A sprint is "Done" when:
- [ ] Sprint goal achieved or explicitly de-scoped
- [ ] All "Done" stories meet Definition of Done
- [ ] Incomplete work returned to backlog
- [ ] Sprint review conducted with stakeholders
- [ ] Sprint retrospective completed with action items
- [ ] Sprint metrics recorded (velocity, bug count, SLA compliance)
- [ ] Documentation updated with sprint outcomes

## Velocity Tracking

### Calculating Velocity

**Story Points Method:**
```python
sprint_velocity = sum(story_points for all completed stories)
average_velocity = sum(last_3_sprint_velocities) / 3
```

**Ticket Count Method:**
```python
sprint_velocity = count(completed_tickets)
average_velocity = average(last_3_sprint_ticket_counts)
```

### Using Velocity for Planning

**Capacity Calculation:**
```python
next_sprint_capacity = average_velocity * 0.9  # 90% confidence
bug_reserve = next_sprint_capacity * 0.2       # 20% for bugs
epic_capacity = next_sprint_capacity * 0.8     # 80% for planned work
```

**Trend Analysis:**
- Velocity increasing → Team is improving
- Velocity stable → Sustainable pace achieved
- Velocity decreasing → Investigate bottlenecks, tech debt, or team changes

## Agile Metrics

### Sprint Health Indicators

**Burndown Chart:**
- Ideal burndown line (linear)
- Actual burndown (should trend toward zero)
- Warning if burndown flatlines mid-sprint

**Velocity Chart:**
- Track points/tickets completed per sprint
- Identify upward/downward trends
- Use for capacity planning

**Cumulative Flow Diagram:**
- Visualize work in each status (To Do, In Progress, Done)
- Identify bottlenecks (where work piles up)
- Ensure smooth flow through pipeline

### Team Health Metrics

**SLA Compliance Rate:**
- Target: ≥ 90% overall compliance
- Trend: Should improve over time
- Violations: Should decrease week-over-week

**Code-Ticket Gap Rate:**
- Target: < 5% of "In Progress" tickets without git activity
- Indicator of stalled work or unreported blockers

**PR Review Time:**
- Target: < 48 hours from submission to first review
- Critical for maintaining sprint velocity

**Bug Escape Rate:**
- Bugs found in production per sprint
- Target: Decreasing trend over time

## Agile Anti-Patterns to Avoid

### Sprint Planning Anti-Patterns
- ❌ Overcommitting to unrealistic scope
- ❌ Skipping capacity planning
- ❌ Not accounting for dependencies
- ❌ Accepting stories without acceptance criteria
- ❌ Planning tasks without team input

### Standup Anti-Patterns
- ❌ Exceeding 15 minutes regularly
- ❌ Turning into status report to manager
- ❌ Ignoring blockers without follow-up
- ❌ Skipping standups frequently
- ❌ Not involving whole team

### Retrospective Anti-Patterns
- ❌ Skipping retrospectives due to "no time"
- ❌ Not acting on retrospective outcomes
- ❌ Allowing blame or finger-pointing
- ❌ Repeating same format every time (boredom)
- ❌ Not tracking action items from previous retros

### Velocity Anti-Patterns
- ❌ Comparing velocity across teams
- ❌ Using velocity as performance metric
- ❌ Gaming the system (inflating story points)
- ❌ Ignoring quality to boost velocity
- ❌ Not accounting for varying team capacity

---

**This skill enables the PM agent to understand and enforce agile best practices, ensuring the team follows effective development workflows and continuously improves their processes.**