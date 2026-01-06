# Project Manager Subagent: Sprint Burndown with Epic Progress

## Overview
This workflow provides comprehensive sprint burndown analysis combined with epic progress tracking. Shows how sprint work contributes to epic completion, identifies risks to both sprint delivery and epic advancement, and provides integrated planning insights.

## Prerequisites
- Atlassian MCP connection configured
- Access to ECD project in Jira
- Valid cloudId for Atlassian instance
- Active sprint in progress

## Key Analysis Components

### 1. Sprint Health Overview
- Total sprint items and completion status
- Sprint burndown velocity and trajectory
- Risk identification for sprint delivery

### 2. Epic Progress Integration
- Epic stories within current sprint
- Epic advancement through sprint work
- Cross-epic coordination in sprint

### 3. Combined Strategic Insights
- Sprint success impact on epic timelines
- Resource allocation optimization
- Next sprint planning recommendations

## Sprint Burndown + Epic Analysis Process

### Step 1: Get Current Sprint Overview
```
Tool: mcp__atlassian__searchJiraIssuesUsingJql
Parameters:
  - cloudId: "67bbfd03-b309-414f-9640-908213f80628"
  - jql: "project = ECD AND sprint in openSprints()"
  - fields: ["summary", "status", "issuetype", "customfield_10014", "updated"]
  - maxResults: 25
```

**Sprint Data Extraction:**
- Sprint items by status (Complete, In Progress, QA, Draft, **Blocked**, etc.)
- Issue types distribution (Story, Bug, Task, Sub-task)
- Epic link identification (customfield_10014)
- Recent activity patterns
- **Blocked tickets requiring immediate intervention**

**Current Sprint Example (Sprint 5):**
- 50 items in sprint
- 14 Complete (28%)
- 21 In Progress (42%)
- **5 Blocked (10%)** 🚨
- 15 Todo (30%)

### Step 2: Epic Story Analysis Within Sprint
Group sprint items by epic affiliation:

#### Epic Stories in Sprint:
```python
Epic ECD-77: "Cite While You Write - Microsoft Word Add-in"
├── ECD-410: "Search Project References..." (In Progress)
└── ECD-409: "Install, Authenticate, and Select Project" (In Progress)

Epic ECD-78: "Full Text Article Access"
├── ECD-398: "Manage and Fulfill Full Text Requests" (In Refinement)
└── ECD-397: "Request and Track Full Text Articles" (In Refinement)
```

#### Non-Epic Work:
- Bug fixes: 6 items (40% of sprint)
- Maintenance tasks: 3 items (20%)
- Infrastructure: 2 items (13%)

### Step 3: Sprint Burndown Calculation

#### Completion Metrics:
```python
Sprint Progress Analysis:
├── Total Items: 50
├── Complete: 14 (28%)
├── Active (In Progress + QA): 21 (42%)
├── Blocked: 5 (10%) 🚨
├── Todo/Draft: 15 (30%)
├── Epic Stories: 12 of 50 (24%)
└── Epic Stories Complete: 3 of 12 (25%)
```

#### Blocked Ticket Analysis:
```python
Blocked Items Requiring Intervention:
├── ECD-516: Request portal workflow (Highest Priority)
├── ECD-487: Full RIS Import/Export (High Priority)
├── ECD-350: Enhanced RIS Import/Export (High Priority)
├── ECD-504: Request Submission Portal (Medium Priority)
└── ECD-398: Manage Full Text Requests (Medium Priority)

Impact: 10% of sprint capacity blocked
Action: Immediate unblocking required for sprint success
```

#### Velocity Analysis:
- **Daily Completion Rate:** Items completed per day since sprint start
- **Remaining Capacity:** Days left × average daily completion
- **Burndown Trend:** Ahead/behind schedule analysis
- **Epic vs Non-Epic Velocity:** Completion rates by work type

### Step 4: Epic Progress Impact Assessment

#### Epic Advancement Through Sprint:
```markdown
Epic ECD-77: "Microsoft Word Add-in"
- Sprint Items: 2 stories (40% of epic scope)
- Current Status: Both In Progress
- Epic Impact: Major advancement if both complete
- Risk Level: 🟢 On track for significant progress

Epic ECD-78: "Full Text Article Access"
- Sprint Items: 2 stories (initial epic work)
- Current Status: Both In Refinement
- Epic Impact: Epic kickoff and foundation
- Risk Level: 🟡 Delayed start, refinement bottleneck
```

#### Epics NOT in Sprint:
- 23+ epics remain in planning phase
- No sprint work = no epic progress
- Planning bottleneck for epic portfolio

### Step 5: Generate Combined Sprint-Epic Report

Create: `.claude/subagents/project-manager/sprint-reports/[SPRINT-NAME]/[YYYY-MM-DD]-burndown-epic.md`

#### Report Structure:
```markdown
# Sprint Burndown + Epic Progress - [Sprint Name] - [Date]

## 🎯 Sprint Health Dashboard
**Sprint:** [Name] | **Days Elapsed:** X of Y | **Burndown Status:** [On Track/Behind/Ahead]

### Sprint Completion Metrics
- **Total Items:** X
- **Complete:** X (X%) ✅
- **In Progress:** X (X%) ⚙️
- **Blocked:** X (X%) 🚨
- **At Risk:** X (X%) ⚠️
- **Todo:** X (X%) 📝
- **Daily Velocity:** X.X items/day

### Sprint Burndown Trajectory
- **Items Remaining:** X
- **Days Remaining:** X
- **Required Daily Velocity:** X.X items/day
- **Projected Completion:** [Date] ([On Time/Early/Late])

---

## 🚀 Epic Progress Through Sprint

### Active Epic Stories (X items, X% of sprint)

#### Epic [ECD-XX]: [Epic Name]
**Sprint Contribution:** X stories (X% of epic scope)
- **[ECD-XXX]** - [Story Name] - [Status] - [Recent Activity]
- **[ECD-XXX]** - [Story Name] - [Status] - [Recent Activity]

**Epic Impact Analysis:**
- **Current Sprint Advancement:** [Major/Moderate/Minor] epic progress
- **Epic Completion Impact:** Sprint work represents X% of total epic
- **Risk Assessment:** [🟢🟡🔴] [Risk description]
- **Next Sprint Implications:** [What this enables for next sprint]

### Epic Stories in Sprint Pipeline (X items)
[Stories in refinement/ready that belong to epics]

### Epics NOT Represented in Sprint
- **X epics** remain in planning phase
- **Epic Activation Bottleneck:** No sprint work = stalled epic progress

---

## 📊 Integrated Sprint-Epic Analysis

### Sprint Success Impact on Epic Timelines

#### High Impact Epic Stories (Sprint success critical for epic progress)
- **[ECD-XXX]** - If completed: Epic advances X%, Timeline: [Impact]
- **[ECD-XXX]** - If delayed: Epic timeline at risk, Dependencies: [List]

#### Sprint Resource Distribution
- **Epic Development:** X% of sprint capacity
- **Bug Fixes/Maintenance:** X% of sprint capacity
- **Infrastructure/Debt:** X% of sprint capacity
- **Optimization Opportunity:** [Recommendation for balance]

### Cross-Epic Coordination
- **Shared Dependencies:** [Stories that impact multiple epics]
- **Resource Conflicts:** [Team members working on multiple epic stories]
- **Coordination Risks:** [Dependencies between epic stories in sprint]

---

## 🚨 Combined Risk Assessment

### Blocked Tickets (Immediate Action Required)
- **[ECD-XXX]** - **Status: BLOCKED** - [Blocker description] - **Priority:** [High/Medium/Low]
- **[ECD-XXX]** - **Status: BLOCKED** - [Blocker description] - **Priority:** [High/Medium/Low]
**Automated Actions:** Jira comments added, Slack alerts sent to assignees

### Sprint Delivery Risks
- **[ECD-XXX]** - [Risk description] - **Impact:** Sprint timeline
- **[ECD-XXX]** - [Risk description] - **Impact:** Epic progress

### Epic Progress Risks
- **Epic [Name]** - **Risk:** [Description] - **Sprint Impact:** [How sprint affects epic]
- **Epic [Name]** - **Risk:** [Description] - **Mitigation:** [Action needed]

### Strategic Risks
- **Epic Starvation:** X% of epics not represented in sprint work
- **Velocity Imbalance:** [Epic vs maintenance work distribution concerns]
- **Dependency Cascades:** [How sprint delays affect multiple epics]

---

## 📅 Sprint + Epic Forecasting

### Likely Sprint Outcomes
- **Epic Stories Completed:** X of Y
- **Epic Progress:** [Epic Name] achieves X% completion
- **Sprint Delivery:** [On time/delayed] completion projected

### Next Sprint Planning Implications
- **Epic Stories Ready:** X stories from Y epics ready for next sprint
- **Epic Prioritization:** [Which epics should get sprint allocation]
- **Capacity Recommendations:** [Epic work vs maintenance balance]

### Epic Timeline Updates
- **Accelerated Epics:** [Epics ahead of schedule due to sprint progress]
- **At-Risk Epics:** [Epics behind schedule, need sprint prioritization]
- **Planning Phase Epics:** [When to activate stalled epics]

---

## 💡 Strategic Insights & Recommendations

### Sprint Optimization for Epic Progress
1. **Epic Story Prioritization:** Focus on [specific stories] for maximum epic impact
2. **Resource Reallocation:** Consider moving [X people] from maintenance to epic work
3. **Dependency Resolution:** Unblock [specific dependencies] to enable epic advancement

### Epic Portfolio Health
1. **Activation Strategy:** Recommend activating [X epics] in next sprint
2. **Planning Bottleneck:** [X epics] need story breakdown and assignment
3. **Strategic Focus:** Concentrate on [epic categories] for business impact

### Cross-Sprint Epic Planning
1. **Multi-Sprint Epics:** [Epic Name] requires X more sprints for completion
2. **Epic Sequencing:** Complete [Epic A] before starting [Epic B] due to dependencies
3. **Capacity Planning:** Need X% epic work allocation to meet epic timeline goals

---

**Generated:** [Timestamp]
**Next Analysis:** [Date + 1 day]
**Sprint End:** [Sprint end date]
**Epic Reviews:** [Next epic progress review date]
```

## Advanced Analysis Features

### Epic Velocity Tracking
```python
Epic Completion Velocity:
- Stories per sprint: Average epic story completion
- Epic advancement rate: % epic completion per sprint
- Cross-sprint epic trends: Multi-sprint epic patterns
- Epic completion forecasting: Timeline projections
```

### Sprint-Epic Correlation Analysis
```python
Correlation Metrics:
- Epic representation % in sprint vs epic progress rate
- Sprint velocity vs epic story completion rate
- Bug/maintenance load impact on epic development velocity
- Epic complexity vs sprint completion success rate
```

### Dynamic Burndown Adjustments
- **Epic Priority Changes:** Adjust sprint focus based on epic urgency
- **Dependency Discoveries:** Update burndown when epic dependencies found
- **Resource Allocation:** Real-time sprint capacity optimization
- **Scope Changes:** Handle epic story additions/removals mid-sprint

## Daily Execution Workflow

### Morning Sprint-Epic Health Check
```bash
# Daily combined analysis
python sprint_epic_tracker.py --sprint-current --epic-integration
```

**Daily Analysis Includes:**
- Sprint burndown status vs target
- Epic story progress overnight
- Blockers affecting both sprint and epic goals
- Resource allocation recommendations

### Weekly Sprint-Epic Planning
```bash
# Weekly strategic review
python sprint_epic_tracker.py --weekly-forecast --epic-planning
```

**Weekly Analysis Includes:**
- Sprint trajectory vs epic timeline impact
- Next sprint epic story candidates
- Epic activation recommendations
- Cross-epic dependency coordination

### Sprint Retrospective with Epic Impact
```bash
# End of sprint analysis
python sprint_epic_tracker.py --sprint-retro --epic-outcomes
```

**Retrospective Analysis:**
- Epic progress achieved through sprint
- Epic timeline updates based on sprint outcomes
- Epic activation strategy for next sprint
- Process improvements for epic development velocity

## Integration with Other PM Capabilities

### Standup Analysis Integration
- Daily standup insights include epic progress context
- Epic story blockers highlighted in standup reports
- Cross-team coordination for epic stories in sprint

### Risk Assessment Integration
- Sprint risks evaluated for epic timeline impact
- Epic risks assessed for sprint delivery impact
- Combined risk mitigation strategies

### Release Planning Integration
- Epic completion forecast informs release timeline
- Sprint velocity trends used for epic release planning
- Cross-epic dependencies mapped to release coordination

## Key Success Metrics

### Sprint-Epic Health Indicators
- **Epic Story Completion Rate:** % of epic stories completed per sprint
- **Epic Advancement Velocity:** Average % epic completion per sprint cycle
- **Sprint-Epic Alignment:** % of sprint capacity allocated to epic work
- **Cross-Epic Coordination:** Success rate of multi-epic sprint coordination

### Strategic Impact Measures
- **Epic Portfolio Activation:** Rate of transitioning epics from planning to active
- **Epic Timeline Accuracy:** Forecast vs actual epic completion alignment
- **Resource Utilization:** Epic development vs maintenance work balance
- **Business Value Delivery:** Epic completion correlation with business goals

This workflow provides comprehensive visibility into both tactical sprint execution and strategic epic progression, enabling data-driven decisions for optimal development velocity and business value delivery.
