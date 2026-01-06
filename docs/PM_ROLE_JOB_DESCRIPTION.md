# Technical Product Manager - CiteMed Evidence Cloud Development

## Company Overview

CiteMed develops evidence management software for medical affairs, regulatory teams, and research institutions. Our Evidence Cloud Development (ECD) platform helps healthcare professionals manage literature reviews, regulatory submissions, and systematic evidence synthesis.

## Role Overview

We're seeking a **Technical Product Manager** to own the product roadmap, sprint execution, and team productivity for the CiteMed Evidence Cloud Development project. This role combines strategic product thinking with hands-on execution—you'll work directly with stakeholders to gather requirements, translate them into actionable tickets, monitor sprint health, and ensure the engineering team delivers high-quality features on time.

**Location:** Remote (US-based preferred)
**Reports To:** Director of Product / CTO
**Team Size:** 5 engineers (Django/Vue.js stack)

---

## Daily Responsibilities

### Morning (9:00 AM - 12:00 PM)

**Daily Standup Review & Sprint Health Monitoring**
- Review automated daily standup report covering:
  - Sprint burndown progress and velocity trends
  - Code-ticket alignment gaps (commits without tickets, tickets without work)
  - Developer productivity metrics (timesheet vs. actual code complexity)
  - SLA violation alerts (Jira comments, PR reviews, blocked tickets)
- Triage SLA violations and escalations
  - Follow up on Jira comments awaiting responses (2-day SLA)
  - Chase stale PR reviews (24-48 hour SLA)
  - Unblock developers stuck on dependencies
- Post standup summary to #ecd-standup Slack channel with key action items

**Stakeholder Engagement & Requirements Gathering**
- Monitor Jira Ideas Discovery project (MDP) for new feature requests
- Review stakeholder comments and questions on active tickets
- Respond to urgent requests from medical affairs, regulatory, or customer success teams
- Conduct quick feasibility assessments with engineering lead

### Afternoon (1:00 PM - 5:00 PM)

**Story & Ticket Creation**
- Convert approved ideas into detailed user stories using AI-assisted drafting tool
- Generate story drafts for 2-3 new features/bugs per day:
  - User story statement (As a... I want... So that...)
  - Business context and customer impact
  - Technical scope and API requirements
  - Comprehensive acceptance criteria
  - Definition of done
- Post drafts for stakeholder approval in Jira comment threads
- Create finalized tickets in ECD project once approved
- Refine existing tickets based on developer feedback

**Sprint Execution & Unblocking**
- Monitor ticket status transitions (To Do → In Progress → Pending Approval → Done)
- Address "Blocked" tickets immediately:
  - Investigate root cause (API dependency, unclear requirements, external blocker)
  - Connect developers with needed resources
  - Escalate to leadership if blockers are external
- Review PR review queue and nudge reviewers if approaching SLA deadline
- Answer developer questions on ticket scope, edge cases, and acceptance criteria

**Ad-Hoc Analysis & Reporting**
- Run custom JQL queries for executive stakeholders
- Generate burndown charts and velocity reports
- Investigate productivity gaps flagged by automated auditing
- Document process improvements in team wiki

---

## Weekly Responsibilities

### Mondays: Sprint Planning Prep & Backlog Grooming

**Sprint Health Review** (1-2 hours)
- Analyze previous week's metrics:
  - Sprint completion rate (target: ≥85% story points completed)
  - SLA compliance score (target: ≥90% team compliance)
  - Developer workload balance (identify over/under-utilized team members)
  - Code quality trends (PR rejection rate, bug escape rate)
- Identify bottlenecks and systemic issues
- Prepare recommendations for sprint planning meeting

**Backlog Grooming** (2-3 hours)
- Review top 20 backlog items for upcoming sprint
- Ensure all stories have:
  - Clear acceptance criteria
  - Technical feasibility assessment
  - Effort estimates from engineering
  - Dependencies documented
- Break down large epics into sprint-sized stories
- Reprioritize based on latest stakeholder feedback and roadmap shifts

### Wednesdays: Mid-Sprint Check-In & Risk Mitigation

**Sprint Burndown Analysis** (1 hour)
- Compare actual burndown vs. ideal burndown trajectory
- Identify at-risk tickets (no code activity in 2+ days)
- Forecast sprint completion probability based on current velocity
- Escalate concerns to engineering lead if sprint goals are jeopardized

**Developer Performance Review** (30 mins)
- Review timesheet-to-code complexity analysis for each developer:
  - Flag significant gaps (e.g., 8 hours logged, 2 hours of code commits)
  - Recognize exceptional productivity (complex features delivered under estimate)
  - Schedule 1-on-1s for underperforming or struggling developers
- Not punitive—focused on removing blockers and providing support

**Stakeholder Updates** (1 hour)
- Post mid-sprint status update to #ecd-status Slack channel
- Respond to questions on feature timelines
- Preview upcoming releases and gather feedback on priorities

### Fridays: Sprint Retrospective & Planning

**Sprint Review & Demo Prep** (1-2 hours)
- Verify all "Done" tickets meet acceptance criteria
- Review demo tickets with QA/engineering
- Prepare release notes for completed features
- Close out sprint in Jira (move incomplete tickets to next sprint)

**Retrospective Facilitation** (1 hour)
- Lead team retrospective meeting:
  - What went well?
  - What didn't go well?
  - What can we improve?
- Document action items and assign owners
- Track retrospective improvements sprint-over-sprint

**Sprint Planning** (2 hours)
- Present groomed backlog to engineering team
- Facilitate story point estimation (planning poker)
- Commit to sprint goal and scope
- Assign tickets to developers based on expertise and workload balance
- Update sprint metadata in Jira

---

## Sprint-Based Responsibilities (Every 2 Weeks)

### Sprint Kickoff (Day 1)

**Sprint Goals & Alignment**
- Publish sprint summary document with:
  - Sprint goal statement
  - Committed story points and key deliverables
  - High-priority bugs and tech debt items
  - Definition of success
- Share in #ecd-team Slack channel and email to stakeholders

**Engineering Alignment Meeting**
- Walk through each committed ticket with engineering team
- Clarify requirements, edge cases, and design decisions
- Identify potential blockers upfront
- Assign tickets to specific developers

### Mid-Sprint (Day 4-5)

**Risk Assessment & Scope Adjustment**
- Review sprint progress: are we on track for committed scope?
- If velocity is below plan:
  - Identify lowest-priority tickets for descoping
  - Get stakeholder buy-in on adjusted scope
  - Communicate changes to team
- If velocity is above plan:
  - Pull in next-highest priority tickets from backlog
  - Ensure team has capacity for stretch goals

**PR Review Blitz**
- Audit all open PRs for review status
- Identify PRs stuck in review for 48+ hours
- Directly request reviews from specific developers
- Escalate to engineering lead if review bottleneck persists

### Sprint Close (Day 10)

**Sprint Metrics Report**
- Generate comprehensive sprint report:
  - Planned vs. actual story points completed
  - Velocity trend (last 4 sprints)
  - SLA compliance score
  - Developer productivity breakdown
  - Bug escape rate and quality metrics
- Present to leadership in weekly ECD status meeting

**Release Coordination**
- Coordinate with DevOps on production deployment
- Write release notes for customer-facing changes
- Notify customer success team of new features
- Monitor production for immediate post-release issues

**Stakeholder Communication**
- Email sprint summary to stakeholders:
  - Features shipped this sprint
  - Key wins and accomplishments
  - Upcoming priorities for next sprint
  - Any changes to roadmap timeline

---

## Strategic Responsibilities (Monthly/Quarterly)

### Monthly: Product Roadmap Review

**Roadmap Prioritization** (4-6 hours/month)
- Analyze feature requests from multiple sources:
  - Customer success team (top pain points)
  - Sales team (deal blockers and feature parity)
  - Medical affairs stakeholders (regulatory requirements)
  - Engineering team (technical debt and infrastructure)
- Score and rank features using weighted criteria:
  - Customer impact (1-10)
  - Revenue impact (1-10)
  - Strategic alignment (1-10)
  - Engineering effort (S/M/L/XL)
- Update quarterly roadmap and communicate changes

**Competitive Analysis**
- Monitor competitor releases and feature updates
- Identify gaps in CiteMed's offering
- Propose features to maintain competitive advantage

### Quarterly: OKR Planning & Team Health

**OKR Definition & Tracking**
- Define quarterly product OKRs aligned with company goals:
  - Example: "Ship 3 major evidence synthesis features with ≥90% stakeholder satisfaction"
  - Example: "Improve sprint velocity by 15% through reduced tech debt"
- Track OKR progress weekly and report to leadership

**Team Health Assessment**
- Review 90-day trends:
  - Sprint velocity stability
  - SLA compliance trends
  - Developer satisfaction (from retrospectives)
  - Stakeholder satisfaction scores
- Identify systemic process improvements
- Propose team structure changes if needed

**Roadmap Presentation**
- Present next quarter's roadmap to executive team
- Justify prioritization decisions with data
- Get buy-in on timelines and resource allocation

---

## Required Skills & Experience

### Technical Skills
- **Jira/Confluence Expertise**: Advanced JQL queries, custom workflows, automation rules
- **Software Development Understanding**: Familiarity with Django, Vue.js, REST APIs (don't need to code, but must speak the language)
- **Git/GitHub Fluency**: Understand PR workflows, code review processes, branching strategies
- **Data Analysis**: SQL basics, Excel/Google Sheets for metrics analysis
- **Agile Methodologies**: Scrum certification preferred, 2+ years practicing Agile

### Domain Knowledge
- **Healthcare/Life Sciences Experience**: Understanding of medical affairs, regulatory submissions, literature review workflows (preferred but not required)
- **Enterprise SaaS**: Experience with B2B SaaS products serving compliance-driven industries

### Product Management Skills
- **Requirements Gathering**: Translate vague stakeholder requests into actionable, testable tickets
- **Prioritization Frameworks**: RICE, MoSCoW, Kano model
- **User Story Writing**: Expert at writing clear, concise user stories with acceptance criteria
- **Roadmap Planning**: Balance short-term delivery with long-term strategic goals

### Soft Skills
- **Communication**: Excellent written communication (Slack, Jira, email) and verbal (standups, sprint planning)
- **Stakeholder Management**: Juggle competing priorities from multiple departments
- **Unblocking & Facilitation**: Help team navigate ambiguity and make decisions quickly
- **Data-Driven Decision Making**: Use metrics to drive prioritization, not gut feel
- **Empathy**: Understand developer frustrations, customer pain points, and stakeholder constraints

---

## Success Metrics (90-Day)

### Delivery Metrics
- **Sprint Completion Rate**: ≥85% of committed story points delivered on time
- **Velocity Stability**: Velocity variance ≤15% sprint-over-sprint
- **Release Frequency**: Deploy to production every sprint (2 weeks)

### Quality Metrics
- **SLA Compliance**: ≥90% team compliance across all SLA categories:
  - Jira comment responses (2 business days)
  - PR reviews (24-48 hours)
  - Blocked ticket updates (daily)
- **Bug Escape Rate**: <5% of delivered features require hotfixes within 7 days
- **Code-Ticket Alignment**: 100% of commits linked to valid Jira tickets

### Stakeholder Satisfaction
- **Stakeholder NPS**: ≥8/10 average satisfaction score from monthly surveys
- **Feature Adoption**: ≥70% of shipped features see active usage within 30 days
- **Requirements Clarity**: ≤10% of tickets require significant mid-sprint clarification

### Team Health
- **Developer Satisfaction**: Positive retrospective feedback on PM support and ticket clarity
- **Escalation Rate**: <5% of issues reach Level 3/4 escalation
- **Meeting Efficiency**: Sprint planning and retrospectives complete within time-boxed duration

---

## Compensation & Benefits

- **Salary Range**: $110,000 - $150,000 (commensurate with experience)
- **Equity**: Stock options (0.25% - 0.75% depending on seniority)
- **Benefits**:
  - Health, dental, vision insurance (100% employee coverage)
  - 401(k) with 4% company match
  - Unlimited PTO (minimum 3 weeks/year)
  - Home office stipend ($1,500/year)
  - Professional development budget ($2,000/year)
- **Work-Life Balance**:
  - Core hours 10 AM - 3 PM ET (flexible schedule otherwise)
  - No expectation of after-hours work except rare production incidents
  - Async-first culture (limit synchronous meetings)

---

## Day in the Life: Example Schedule

### Monday - Sprint Planning Day

**9:00 AM** - Review weekend bot reports (SLA alerts, sprint burndown)
**9:30 AM** - Team standup (async Slack post, live Q&A)
**10:00 AM** - 1-on-1 with engineering lead (sprint readiness)
**11:00 AM** - Backlog grooming (refine top 10 stories)
**12:00 PM** - Lunch
**1:00 PM** - Sprint planning meeting (2 hours)
**3:00 PM** - Post sprint summary to Slack/email
**3:30 PM** - Review 3 new feature requests from stakeholders
**4:30 PM** - Draft user story for bulk EndNote import feature
**5:00 PM** - Post draft for stakeholder approval

### Wednesday - Mid-Sprint Check-In Day

**9:00 AM** - Review bot's mid-sprint health report
**9:30 AM** - Follow up on 2 blocked tickets from Monday
**10:00 AM** - Chase stale PR reviews (3 PRs stuck >48 hours)
**11:00 AM** - Stakeholder call: demo in-progress feature
**12:00 PM** - Lunch
**1:00 PM** - Create 2 bug tickets from support escalations
**2:00 PM** - Developer performance review (timesheet audit)
**3:00 PM** - Respond to Jira comments on 4 active tickets
**4:00 PM** - Draft mid-sprint update for #ecd-status channel
**4:30 PM** - 1-on-1 with developer struggling with unclear requirements

### Friday - Sprint Close & Retrospective Day

**9:00 AM** - Verify all "Done" tickets meet acceptance criteria
**10:00 AM** - Team retrospective (1 hour)
**11:00 AM** - Sprint metrics report preparation
**12:00 PM** - Lunch
**1:00 PM** - Leadership update: present sprint results
**2:00 PM** - Write release notes for deployed features
**3:00 PM** - Groom backlog for next sprint
**4:00 PM** - Send stakeholder email: sprint summary & next sprint preview
**4:30 PM** - Review automated productivity reports, flag outliers

---

## Why This Role is Unique

Traditional PMs spend 60% of their time in meetings and fighting fires. At CiteMed, you have an **AI-powered autonomous PM agent** that handles:

1. **Automated SLA Monitoring**: Bot tracks and escalates violations before they become crises
2. **Daily Standup Reports**: No need to manually compile metrics—bot generates comprehensive reports daily
3. **AI-Assisted Story Creation**: Bot drafts 80% of user stories based on stakeholder input; you refine and approve
4. **Code-Ticket Gap Detection**: Bot automatically flags commits without tickets and tickets without work
5. **Proactive Escalations**: Bot follows 4-level escalation matrix, only involving you when human judgment is needed

**This means you can focus on:**
- Strategic product decisions
- Deep stakeholder engagement
- Unblocking complex technical challenges
- Long-term roadmap planning

Instead of drowning in administrative overhead, you'll spend time on high-value PM work that actually moves the product forward.

---

## How to Apply

Send resume and cover letter to: careers@citemed.com

In your cover letter, please address:
1. **Technical Fluency**: Describe a time you worked closely with engineering teams. How did you bridge the gap between technical and non-technical stakeholders?
2. **Data-Driven PM**: Share an example where you used metrics to drive a product decision. What data did you collect, and what action did you take?
3. **Healthcare Domain** (if applicable): If you have healthcare/life sciences experience, describe how it would benefit your PM work at CiteMed.

**First-round interview process:**
- 30-min phone screen with Director of Product
- 1-hour case study: "Given this stakeholder request, how would you scope it into a sprint?"
- 1-hour technical deep-dive with engineering lead
- 30-min culture fit with CTO

We aim to complete the process within 2 weeks of application.

---

**CiteMed is an equal opportunity employer. We celebrate diversity and are committed to creating an inclusive environment for all employees.**
