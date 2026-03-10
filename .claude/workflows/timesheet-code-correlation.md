# Project Manager Subagent: Timesheet-Code Correlation Analysis

## Overview
This workflow correlates developer timesheet entries with actual git activity to identify productivity patterns, billing accuracy, and development gaps for comprehensive project management insights.

## Prerequisites
- Slack integration configured (see slack-setup-instructions.md)
- Git repository access with ECD branch naming
- Jira/Atlassian MCP connection active
- Developer timesheet channel in Slack

## Core Analysis Components

### 1. Timesheet Data Collection
- Extract hours logged per developer per ticket
- Parse timesheet formats from Slack messages
- Identify ticket assignments and time allocations

### 2. Git Activity Correlation
- Map commits to tickets via ECD-XXX patterns
- Calculate actual development time via commit timestamps
- Measure code velocity and contribution patterns

### 3. Billing vs Delivery Analysis
- Compare reported hours to actual code output
- Identify over/under-reporting patterns
- Flag potential billing or productivity issues

## Timesheet-Code Correlation Process

### Step 1: Extract Timesheet Data from Slack

```bash
# Get recent timesheet entries
python .claude/subagents/project-manager/scripts/slack_pm_integration.py timesheets dev-timesheets 7 > timesheet_data.json
```

**Data Structure Expected:**
```json
{
  "raw_timesheets": [
    {
      "user_name": "Mohamed Belkahla",
      "hours": 3.5,
      "ticket": "ECD-409",
      "date": "2025-08-21",
      "description": "3.5h on ECD-409 - authentication system"
    }
  ],
  "analysis": {
    "developers": {
      "Mohamed Belkahla": {
        "total_hours": 15.5,
        "tickets": ["ECD-409", "ECD-410"],
        "daily_entries": [...]
      }
    }
  }
}
```

### Step 2: Get Git Activity Data

```bash
# Get recent commits with ticket correlation
git log --oneline --since="1 week ago" --all --grep="ECD-" --pretty=format:"%h|%an|%ad|%s" --date=short
```

**Expected Git Data:**
```
a1b2c3d|Mohamed Belkahla|2025-08-21|ECD-409: Implement OAuth authentication flow
d4e5f6g|Mohamed Belkahla|2025-08-21|ECD-409: Add login validation tests
h7i8j9k|Jason Fry|2025-08-20|ECD-339: Fix missing help button functionality
```

### Step 3: Cross-Reference Analysis

#### A. Hours vs Commits Correlation
```python
Timesheet-Code Analysis:
├── Developer: Mohamed Belkahla
├── Reported Hours: 15.5h across 3 tickets
├── Git Activity: 12 commits across 2 tickets
├── Correlation Score: 85% (good alignment)
└── Gaps: ECD-410 has 4h reported but no commits

├── Developer: Jason Fry
├── Reported Hours: 8h on ECD-339
├── Git Activity: 6 commits on ECD-339
├── Correlation Score: 95% (excellent alignment)
└── Gaps: None detected
```

#### B. Ticket-Level Analysis
```python
Ticket ECD-409: "Install, Authenticate, and Select Project"
├── Total Reported Hours: 12h (Mohamed: 8h, Dang: 4h)
├── Git Activity: 8 commits over 3 days
├── Status: In Progress → Complete (good progression)
├── Delivery Efficiency: 1.5h per meaningful commit
└── Assessment: ✅ Realistic time allocation

Ticket ECD-410: "Search Project References"
├── Total Reported Hours: 6h (Mohamed: 6h)
├── Git Activity: 0 commits detected ⚠️
├── Status: In Progress (concerning)
├── Gap Alert: HIGH - Hours logged but no code delivery
└── Action: Contact Mohamed for status clarification
```

### Step 4: Generate Correlation Report

Create: `.claude/subagents/project-manager/timesheet-reports/[YYYY-MM-DD]-correlation-analysis.md`

```markdown
# Timesheet-Code Correlation Analysis - [Date]

## 📊 Developer Productivity Overview

### Overall Team Metrics
- **Total Reported Hours:** 45.5h across 4 developers
- **Total Git Commits:** 32 commits across 8 tickets
- **Average Correlation Score:** 87% (excellent team alignment)
- **Efficiency Ratio:** 1.42h per commit (industry standard: 1-2h)

### Developer Performance Summary
| Developer | Hours | Commits | Tickets | Correlation | Status |
|-----------|-------|---------|---------|-------------|---------|
| Mohamed Belkahla | 15.5h | 12 | 3 | 85% | ✅ Good |
| Jason Fry | 8h | 6 | 1 | 95% | ✅ Excellent |
| Dang Thanh | 12h | 10 | 2 | 90% | ✅ Excellent |
| Other Dev | 10h | 4 | 2 | 60% | ⚠️ Review Needed |

---

## 🔍 Detailed Correlation Analysis

### High-Performing Patterns
✅ **Jason Fry - ECD-339**
- **Hours Logged:** 8h over 2 days
- **Git Activity:** 6 commits, 2 PRs merged
- **Outcome:** Feature completed, ticket closed
- **Efficiency:** 1.3h per commit (excellent)
- **Pattern:** Consistent daily commits matching reported hours

✅ **Dang Thanh - ECD-XXX**
- **Hours Logged:** 6h over 1 day
- **Git Activity:** 5 commits, 1 PR merged
- **Outcome:** Bug fixes completed
- **Efficiency:** 1.2h per commit (excellent)
- **Pattern:** Focused development session with immediate delivery

### Correlation Gaps Identified

🔴 **Mohamed Belkahla - ECD-410**
- **Issue:** 6h reported, 0 commits detected
- **Risk:** High - potential billing/delivery mismatch
- **Possible Causes:**
  - Development on different branch
  - Research/planning phase (no code yet)
  - External dependency blocking
- **Action:** Contact Mohamed for clarification within 24h

🟡 **Other Dev - Multiple Tickets**
- **Issue:** 10h reported, only 4 meaningful commits
- **Risk:** Medium - efficiency concern
- **Pattern:** Large time blocks, infrequent commits
- **Recommendation:** Daily commit encouragement, smaller task breakdown

---

## 📈 Productivity Insights

### Time Allocation Patterns
- **Feature Development:** 65% of hours (appropriate)
- **Bug Fixes:** 20% of hours (normal range)
- **Infrastructure/Setup:** 15% of hours (reasonable)

### Code Delivery Efficiency
- **Best Performers:** 1.2-1.5h per commit
- **Team Average:** 1.42h per commit
- **Industry Benchmark:** 1-2h per commit ✅ Within range

### Timesheet Accuracy Assessment
- **Over-reporting Risk:** 1 instance detected (ECD-410)
- **Under-reporting Risk:** None detected
- **General Accuracy:** 87% correlation suggests good timesheet discipline

---

## 🚨 Action Items & Alerts

### Immediate Actions Required
1. **Contact Mohamed** - Verify ECD-410 development status
2. **Review Other Dev** - Discuss commit frequency and task breakdown
3. **Process Check** - Ensure all developers using correct branch naming

### Process Improvements
1. **Daily Commit Encouragement** - Promote frequent, small commits
2. **Branch Naming Compliance** - Ensure ECD-XXX pattern usage
3. **Timesheet Accuracy** - Brief team on accurate hour reporting

### Automated Alerts Sent
- **Slack Alert:** Mohamed tagged in ECD-410 gap detection
- **Jira Comment:** Added correlation concern to ECD-410
- **Team Notification:** Weekly correlation summary posted

---

## 📊 Historical Trends (if available)

### Week-over-Week Comparison
- **Correlation Score:** 87% (↑3% from last week)
- **Team Velocity:** 32 commits (↑15% from last week)
- **Hour Accuracy:** Improving trend in timesheet-code alignment

### Developer Growth Patterns
- **Mohamed:** Consistent high output, occasional gaps
- **Jason:** Steady excellent correlation, reliable delivery
- **Dang:** High efficiency, great commit-to-hour ratio

---

## 💡 Strategic Recommendations

### Team Optimization
1. **Pair Mohamed with Jason** for ECD-410 knowledge transfer
2. **Standardize branch workflow** to improve tracking accuracy
3. **Daily standup focus** on commit frequency and blockers

### Process Refinement
1. **Automated correlation checks** - Run this analysis daily
2. **Slack integration** - Real-time gap alerts
3. **Developer coaching** - Help low-correlation developers improve

### Business Intelligence
1. **Billing Confidence:** 87% correlation provides good client confidence
2. **Resource Allocation:** Data supports current team assignments
3. **Capacity Planning:** Team can handle current sprint load effectively

---

**Analysis Generated:** [Timestamp]
**Data Sources:** Slack #dev-timesheets, Git repository, Jira ECD project
**Next Analysis:** [Date + 1 day]
**Correlation Threshold:** 80% (team currently at 87% ✅)
```

### Step 5: Automated Gap Detection & Alerts

```python
Gap Detection Workflow:
├── Hours logged but no commits (2+ days) → HIGH priority alert
├── Commits without timesheet entries → Medium priority reminder
├── Correlation score < 70% → Developer coaching conversation
└── Perfect correlation (95%+) → Recognition and team sharing
```

### Step 6: Integration with Other PM Capabilities

#### Sprint Planning Integration
- Use historical timesheet-code correlation for capacity estimation
- Identify which developers provide most accurate estimates
- Adjust sprint commitments based on delivery patterns

#### Epic Progress Integration
- Epic advancement rate vs reported epic-related hours
- Resource allocation optimization using correlation data
- Epic timeline accuracy based on developer efficiency patterns

## Advanced Analysis Features

### Billing Accuracy Scoring
```python
Billing Confidence Metrics:
├── High Confidence (90%+ correlation): Bill with full confidence
├── Medium Confidence (70-89%): Standard review process
├── Low Confidence (<70%): Detailed review required
└── Gap Investigation: Hours without code require explanation
```

### Developer Coaching Insights
```python
Coaching Opportunities:
├── Low correlation developers: Improve timesheet accuracy training
├── High efficiency developers: Mentor others, take on complex tasks
├── Inconsistent patterns: Address workflow or tool issues
└── Perfect correlators: Use as examples, potential tech leads
```

### Project Health Indicators
```python
Project Health Dashboard:
├── Team Correlation Score: 87% ✅
├── Delivery Predictability: High (good hour-to-code ratio)
├── Billing Risk: Low (few unexplained hour gaps)
└── Developer Satisfaction: High (realistic time expectations)
```

## Key Success Metrics

### Correlation Quality KPIs
- **Team Correlation Score:** Target >80%, Current: 87% ✅
- **Gap Resolution Time:** Target <24h, Current: Same day ✅
- **Billing Accuracy:** Target >90%, Current: 93% ✅
- **Developer Satisfaction:** High trust in timesheet process

### Business Impact Measures
- **Client Billing Confidence:** Supported by objective correlation data
- **Resource Planning Accuracy:** Improved sprint estimation
- **Developer Productivity:** Data-driven coaching and optimization
- **Project Delivery:** Better timeline accuracy through realistic estimation

This workflow provides comprehensive visibility into the relationship between reported work and actual code delivery, enabling data-driven project management and team optimization.
