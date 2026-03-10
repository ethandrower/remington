# Project Manager Subagent: PR and Git Branch Analysis

## Overview
Comprehensive analysis that correlates git branch activity, pull requests, and commits with Jira ticket status to identify code-ticket gaps, measure developer productivity, and ensure sprint delivery alignment.

## Prerequisites
- Atlassian MCP connection configured
- Git repository access with ECD branch naming convention
- Valid cloudId for Atlassian instance
- Developer account ID lookup capability

## Core Analysis Components

### 1. Code-Ticket Correlation Analysis
- Git branch activity vs Jira ticket status alignment
- PR merge status vs ticket completion tracking
- Commit frequency vs work progress validation
- Developer assignment vs actual code contribution

### 2. Developer Productivity Metrics
- Commit velocity per developer per sprint
- PR merge success rates and timing
- Ticket completion vs code delivery correlation
- Code quality indicators (pre-commit usage, etc.)

### 3. Automated Gap Detection & Alerting
- In Progress tickets without git activity
- Completed tickets without merged PRs
- Code activity without corresponding ticket updates
- Developer-specific productivity patterns

## PR/Git Analysis Process

### Step 1: Get Current Sprint Tickets with Developer Info
```
Tool: mcp__atlassian__searchJiraIssuesUsingJql
Parameters:
  - cloudId: "67bbfd03-b309-414f-9640-908213f80628"
  - jql: "project = ECD AND sprint in openSprints()"
  - fields: ["summary", "status", "issuetype", "assignee", "updated", "customfield_10014"]
  - maxResults: 25
```

**Extract Key Data:**
- Ticket status and assignee information
- Last updated timestamps for activity correlation
- Epic linkage for broader progress context

### Step 2: Analyze Git Branch Activity
```bash
# Get recent commits with developer and ticket correlation
git log --oneline --since="1 week ago" --all --grep="ECD-"

# Get branch activity for specific tickets
git log --pretty=format:"%h | %an | %ad | %s" --date=short --grep="ECD-XXX" --all

# Check branch status for ticket branches
git branch -a | grep "ECD-" | head -20
```

**Git Analysis Targets:**
- ECD-prefixed branches matching ticket numbers
- Recent commit activity (last 7-14 days)
- Author identification for developer productivity
- PR merge patterns via commit messages

### Step 3: Developer Productivity Analysis

#### Commit Activity Metrics:
```python
Developer Analysis:
├── Commit Count: commits per developer per week
├── Branch Activity: active branches per developer
├── PR Success Rate: merged PRs vs total PRs
├── Ticket Alignment: % of commits with matching ticket status
└── Code Quality: pre-commit hook usage, formatting compliance
```

#### Real Example Analysis:
```
Mohamed Belkahla (Last 7 Days):
├── Commits: 15+ commits across 3 branches
├── PRs Merged: 2 (ECD-333, infrastructure fixes)
├── Tickets: ECD-333 Complete ✅ (Perfect alignment)
├── Code Quality: All commits use pre-commit hooks ✅
└── Productivity: High velocity, excellent completion

Jason Fry (Last 7 Days):
├── Commits: 8 commits across 2 branches
├── PRs Merged: 2 (ECD-339, ECD dependencies)
├── Tickets: Both Complete ✅ (Perfect alignment)
├── Code Quality: Clean commit messages, proper formatting ✅
└── Productivity: Consistent delivery, good quality
```

### Step 4: Code-Ticket Gap Detection

#### Gap Categories:

**🔴 High Priority Gaps:**
- **In Progress + No Git Activity** (3+ days)
- **Complete Status + No Merged PR**
- **Heavy Git Activity + No Ticket Status Update**

**🟡 Medium Priority Gaps:**
- **Assigned + No Recent Commits** (1-2 days)
- **Branch Exists + Ticket Still Draft**
- **PR Merged + Ticket Not Complete**

**🟢 Low Priority Monitoring:**
- **Recent Assignment + Early Development**
- **Epic Stories + Coordinated Development**

#### Real Gap Examples Detected:
```
🔴 ECD-409: "Install, Authenticate, and Select Project"
├── Status: In Progress ⚠️
├── Assignee: Not assigned ⚠️
├── Git Activity: No commits found ❌
├── Sprint Impact: High - due this sprint
└── Action: Contact assignee or reassign

🔴 ECD-410: "Search Project References and Insert"
├── Status: In Progress ⚠️
├── Assignee: Not assigned ⚠️
├── Git Activity: No commits found ❌
├── Sprint Impact: High - due this sprint
└── Action: Contact assignee or reassign
```

### Step 5: Automated Developer Identification

#### Developer Lookup Priority:
1. **Current Assignee** (from ticket.assignee field)
2. **Git Commit Author** (recent commits on ECD-XXX branch)
3. **Historical Assignment** (from ticket changelog)
4. **Epic Owner** (for story-level issues)
5. **Team Pattern** (by ticket type/area)

#### Account ID Resolution:
```python
Tool: mcp__atlassian__lookupJiraAccountId
Parameters:
  - cloudId: "67bbfd03-b309-414f-9640-908213f80628"
  - searchString: "Mohamed Belkahla"

# Store for automated commenting:
Known Developers:
├── Mohamed Belkahla: 712020:27a3f2fe-9037-455d-9392-fb80ba1705c0
├── Ethan Drower: 712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e
└── [Others via lookup as needed]
```

### Step 6: Generate Analysis Report

Create: `.claude/subagents/project-manager/pr-git-reports/[YYYY-MM-DD]-code-ticket-analysis.md`

#### Report Structure:
```markdown
# PR/Git Branch Analysis - [Date]

## 📊 Developer Productivity Summary

### Top Performers (Last 7 Days)
| Developer | Commits | PRs Merged | Tickets Complete | Alignment Score |
|-----------|---------|------------|------------------|-----------------|
| Mohamed Belkahla | 15 | 2 | 2 | ✅ 100% |
| Jason Fry | 8 | 2 | 2 | ✅ 100% |
| Dang Thanh | 6 | 2 | 2 | ✅ 100% |
| [Others] | X | X | X | X% |

### Team Velocity Metrics
- **Total Commits:** X across Y developers
- **PR Success Rate:** X% (Y merged / Z created)
- **Code Quality Score:** X% (pre-commit compliance)
- **Average Code-Ticket Alignment:** X%

---

## 🚨 Code/Ticket Gaps Identified

### HIGH PRIORITY - Immediate Action Required

#### ECD-409: "Install, Authenticate, and Select Project"
**Developer to Contact:** @ASSIGNEE_NAME / @EPIC_OWNER
- **Gap:** In Progress status with no git commits (3+ days)
- **Risk:** Sprint delivery at risk
- **Action:** Verify development progress or reassign
- **Sprint Impact:** High - blocks epic completion

#### ECD-410: "Search Project References"
**Developer to Contact:** @ASSIGNEE_NAME
- **Gap:** In Progress status with no git commits (3+ days)
- **Risk:** Sprint delivery at risk
- **Action:** Check if work is on different branch
- **Sprint Impact:** High - critical story

### MEDIUM PRIORITY - Monitor Closely

#### ECD-XXX: [Ticket Summary]
**Developer to Contact:** @DEVELOPER_NAME
- **Gap:** [Description of gap]
- **Risk:** [Risk assessment]
- **Action:** [Recommended action]

---

## 🎯 Sprint Code-Ticket Health

### Epic Progress via Code Activity
- **Epic ECD-77:** 0 commits despite 2 "In Progress" stories ⚠️
- **Epic ECD-84:** No activity (expected - all Draft) ✅
- **Non-Epic Work:** High activity (bug fixes, features) ✅

### Branch Management Health
- **Naming Convention:** ✅ Excellent ECD-XXX-description format
- **Branch Cleanup:** ✅ Good (25+ merged branches cleaned)
- **Active Branches:** 4 local, appropriate count

### Code Quality Indicators
- **Pre-commit Usage:** ✅ 100% compliance detected
- **Commit Message Quality:** ✅ Descriptive, follows conventions
- **PR Process:** ✅ All changes via pull requests
- **Merge Conflicts:** ✅ Clean resolution patterns

---

## 📈 Productivity Insights

### High-Performing Patterns
- **Consistent Daily Commits:** Mohamed, Jason showing regular activity
- **Quality Over Quantity:** Small, focused commits with clear purposes
- **Excellent PR Hygiene:** All merges via reviewed pull requests
- **Perfect Status Alignment:** Completed tickets match merged code

### Areas for Improvement
- **Silent Development:** Some "In Progress" tickets lack visible commits
- **Status Update Lag:** Consider automating ticket updates on PR merge
- **Assignment Clarity:** Some tickets lack clear developer assignment

### Sprint Delivery Forecast
- **On Track:** 70% of sprint items show appropriate code activity
- **At Risk:** 20% marked "In Progress" without matching development
- **Blocked:** 10% require immediate developer contact/reassignment

---

## 🤖 Automated Actions Taken

### Comments Added to Tickets:
- **ECD-409:** Gap alert comment posted
- **ECD-410:** Developer inquiry comment posted
- **ECD-XXX:** Status verification comment posted

### Developer Notifications:
- **@Mohamed Belkahla:** Productivity recognition comment
- **@Jason Fry:** Excellent alignment acknowledgment
- **@ASSIGNEE_NAME:** Gap resolution request

---

## 📅 Next Sprint Planning Implications

### Developer Capacity Analysis
- **Mohamed:** High velocity, can handle complex features
- **Jason:** Consistent delivery, good for critical bugs
- **Team Gaps:** Need investigation on silent "In Progress" items

### Code-Ticket Process Improvements
1. **Automated Status Updates:** PR merge → ticket complete
2. **Branch Creation Timing:** Create when ticket moves to "In Progress"
3. **Daily Code-Ticket Sync:** Add to standup routine
4. **Developer Assignment:** Ensure clear ownership before "In Progress"

---

**Generated:** [Timestamp]
**Next Analysis:** [Date + 1 day]
**Data Sources:** Git repository, Jira ECD project
**Automation Status:** Gap alerts posted to X tickets
```

## Advanced Analysis Features

### Multi-Sprint Code Velocity Tracking
```python
Velocity Trends:
├── Sprint N-1: X commits/developer/day
├── Sprint N: X commits/developer/day
├── Trend: Increasing/Decreasing/Stable
└── Forecast: Sprint N+1 capacity prediction
```

### Cross-Epic Code Coordination
```python
Epic Code Analysis:
├── Single Epic Focus: Developers working on 1 epic (ideal)
├── Multi-Epic Work: Developers spread across epics (risk)
├── Epic Completion Velocity: Code activity → epic advancement
└── Resource Allocation: Optimal developer→epic mapping
```

### Branch Strategy Health Metrics
```python
Branch Management:
├── Average Branch Lifespan: X days
├── Merge Success Rate: X% clean merges
├── Naming Convention Compliance: X%
├── Cleanup Efficiency: X% merged branches removed
└── Parallel Development: X concurrent feature branches
```

## Automated Alert System

### Daily Automated Checks
```bash
# Morning productivity sweep
python pr_git_analysis.py --daily-gaps --auto-comment

Daily Gap Detection:
├── New "In Progress" tickets without branches
├── 24h+ "In Progress" without commits
├── Merged PRs with incomplete tickets
└── High commit activity without status updates
```

### Weekly Team Analysis
```bash
# Weekly team productivity analysis
python pr_git_analysis.py --weekly-team --productivity-report

Weekly Analysis:
├── Individual developer productivity scores
├── Team velocity trends and forecasting
├── Code quality metric analysis
└── Sprint delivery risk assessment
```

### Automated Comment Templates

#### Gap Detection Comments:
```python
# In Progress without git activity
comment_template = """
🚨 PM Analysis Alert - @{developer_name}

This ticket has been 'In Progress' for {days} days without git activity.

Current Status:
- Ticket: In Progress
- Git Activity: No commits found
- Sprint Deadline: {sprint_end_date}
- Risk Level: HIGH - Sprint delivery at risk

Action Needed:
- Is development happening on a different branch?
- Should ticket status be updated?
- Do you need support or reassignment?

Please update within 24h to avoid sprint impact.

Generated by automated PM analysis on {date}
"""

# Productivity recognition
recognition_template = """
✅ Excellent Code-Ticket Alignment - @{developer_name}

Great work this week:
- {commit_count} commits across {days} days
- {pr_count} PRs merged successfully
- {ticket_count} tickets completed on schedule
- 100% code-status alignment

Keep up the outstanding productivity! 🎉

Team PM Analysis - {date}
"""
```

## Integration with Other PM Capabilities

### Sprint Burndown Integration
- Code velocity data feeds sprint completion forecasts
- Git activity used to validate burndown accuracy
- Developer capacity planning based on commit patterns

### Epic Progress Integration
- Epic advancement correlated with code contribution
- Cross-epic resource allocation optimization
- Epic completion forecasting via development velocity

### Risk Assessment Integration
- Code gaps automatically flagged as sprint risks
- Developer productivity trends inform capacity planning
- Technical debt indicators from commit pattern analysis

## Key Success Metrics

### Code-Ticket Alignment KPIs
- **Perfect Alignment:** % tickets with matching code/status
- **Gap Resolution Time:** Hours from detection to resolution
- **Sprint Delivery Accuracy:** Predicted vs actual based on code activity
- **Developer Productivity Consistency:** Velocity stability over time

### Process Improvement Metrics
- **Automated Gap Detection Rate:** % gaps caught automatically
- **False Positive Rate:** % incorrect gap alerts
- **Developer Response Time:** Hours to respond to gap alerts
- **Status Update Automation:** % tickets auto-updated from code activity

This workflow provides comprehensive visibility into the critical relationship between development work and project management tracking, enabling proactive intervention and team optimization.
