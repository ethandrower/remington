# Project Manager Subagent: Daily Standup Analysis

## Overview
This workflow analyzes current sprint items for daily standup insights, tracking changes, blockers, and progress over time with day-to-day comparison capabilities.

## Prerequisites
- Atlassian MCP connection configured
- Access to ECD project in Jira
- Valid cloudId for Atlassian instance

## Folder Structure
```
.claude/subagents/project-manager/
├── workflows/
│   ├── standup-analysis.md          # This workflow
│   └── jira-sprint-search.md        # Base Jira search capability
├── standups/
│   ├── [SPRINT-NAME]/               # e.g., "CM-Sprint-3"
│   │   ├── 2025-08-21.md           # Daily standup reports
│   │   ├── 2025-08-22.md
│   │   └── sprint-metadata.json     # Sprint details cache
│   └── current-sprint.json          # Active sprint tracking
├── templates/
│   ├── daily-standup-template.md
│   └── sprint-summary-template.md
└── scripts/
    └── standup-generator.py         # Future automation
```

## Daily Standup Analysis Process

### Step 1: Establish MCP Connection
```
Tool: mcp__atlassian__getAccessibleAtlassianResources
Purpose: Verify connection and retrieve cloudId
Expected Result: Get cloudId like "67bbfd03-b309-414f-9640-908213f80628"
```

### Step 2: Get Current Sprint Overview
```
Tool: mcp__atlassian__searchJiraIssuesUsingJql
Parameters:
  - cloudId: "67bbfd03-b309-414f-9640-908213f80628"
  - jql: "project = ECD AND sprint in openSprints()"
  - fields: ["summary", "status", "issuetype", "priority", "updated", "assignee"]
  - maxResults: 25
```

**Key Data Extraction:**
- Total items in current sprint
- Sprint name from `customfield_10020` array (e.g., "CM Sprint 3")
- Status distribution (Draft, In Progress, QA, Complete, etc.)
- Assignment distribution
- Last updated timestamps

**Handle Large Response:** If response exceeds token limit, use pagination:
```
Tool: mcp__atlassian__searchJiraIssuesUsingJql
Parameters:
  - maxResults: 25
  - nextPageToken: [if provided in previous response]
```

### Step 3: Deep Analysis of Individual Issues
For each issue identified in sprint overview:
```
Tool: mcp__atlassian__getJiraIssue
Parameters:
  - cloudId: "67bbfd03-b309-414f-9640-908213f80628"
  - issueIdOrKey: [e.g., "ECD-471"]
  - expand: "comments,changelog"
```

**Extract from Changelog (Last 24-48h):**
- Status transitions: `{"field":"status","from":"10165","fromString":"Draft","to":"3","toString":"In Progress"}`
- Assignment changes: `{"field":"assignee","to":"712020:27a3f2fe-9037-455d-9392-fb80ba1705c0","toString":"Mohamed Belkahla"}`
- Sprint movements: `{"field":"Sprint","to":"298","toString":"CM Sprint 3"}`
- Due date changes: `{"field":"duedate","to":"2025-08-22","toString":"2025-08-22 00:00:00.0"}`

**Extract from Comments:**
- Recent comments with `"created": "2025-08-21T05:24:44.980-0500"`
- Questions containing "@" mentions and "?"
- Blocker language: "need access", "waiting for", "can't proceed"
- Comment author and timestamp for response tracking

**Real Examples Found in Testing:**
- ECD-471: Mohamed asking "@Ethan Drower I don't see this part in the provided design..."
- ECD-340: Jason requesting "Can you send me the test login so I can get into the pages?"
- ECD-410: Status changed Draft → In Progress yesterday, due 8/22

### Step 3: Generate Daily Standup Report
Create: `.claude/subagents/project-manager/standups/[SPRINT-NAME]/[YYYY-MM-DD].md`

#### Report Structure:
```markdown
# Daily Standup - [Date] - [Sprint Name]

## 🚀 Recent Progress (Last 24h)
### Status Changes
- **ECD-XXX** - [Old Status] → [New Status] - [Assignee] ([Time])
- **ECD-XXX** - Added to sprint - [Assignee]

### New Activity
- **ECD-XXX** - [Activity description] - [Person] ([Time])

## 🚧 Active Blockers & Questions
### Needs Immediate Attention
- **ECD-XXX** - [Blocker/Question] - **Action:** [Who needs to respond]
- **ECD-XXX** - Waiting for [resource/access/approval] - **Owner:** [Person]

### Design/Requirements Clarification
- **ECD-XXX** - [Question about requirements] - **PM Action Required**

## ⚠️ At Risk Items
### Due This Week
- **ECD-XXX** - Due [Date] - Status: [Current] - **Risk:** [Description]

### Stalled Items (No movement in 2+ days)
- **ECD-XXX** - Last updated [Date] - **Concern:** [Why stalled]

## 💬 New Comments & Questions (Last 24h)
### Team Communications
- **ECD-XXX** - "@PersonX [comment excerpt]" - **Needs:** [Response/Action]
- **ECD-XXX** - [Comment summary] - **Type:** [Question/Update/Blocker]

## 📊 Sprint Health Summary
- **Total Items:** X
- **In Progress:** X
- **Blocked/Pending:** X
- **QA/Review:** X
- **Complete:** X
- **Due This Week:** X

## 🔍 Day-to-Day Comparison
[Only if previous day's report exists]

### Items That Advanced
- **ECD-XXX** - [Previous Status] → [Current Status]

### Items Still Blocked (Carry-over from yesterday)
- **ECD-XXX** - Still waiting for [same blocker] - **Days blocked:** X

### New Items Entering Sprint/Progress
- **ECD-XXX** - [Just added/started]

### Velocity Insights
- Items completed since yesterday: X
- New blockers introduced: X
- Average time in current statuses: [Analysis]
```

### Step 4: Cross-Day Comparison Analysis
If previous day's report exists in same sprint folder:

**Compare:**
1. **Status Progress** - Items that moved forward vs. stalled
2. **Blocker Resolution** - Which blockers were resolved vs. new ones
3. **Comment Activity** - Response times to questions
4. **Sprint Additions** - New items pulled into sprint
5. **Risk Escalation** - Items moving closer to due dates

**Generate Insights:**
- Identify patterns (who responds quickly, what types of blockers recur)
- Flag items that have been blocked multiple days
- Track velocity trends (items completed per day)

### Step 5: Cache Sprint Metadata
Update: `.claude/subagents/project-manager/standups/[SPRINT-NAME]/sprint-metadata.json`

```json
{
  "sprint_name": "CM Sprint 3",
  "sprint_id": "298",
  "start_date": "2025-08-15T14:58:42.862Z",
  "end_date": "2025-08-29T12:00:00.000Z",
  "goal": "CiteSource Demo Initiative",
  "last_analyzed": "2025-08-21T12:00:00.000Z",
  "days_analyzed": 5,
  "total_items_tracked": 25,
  "completion_velocity": {
    "daily_average": 2.1,
    "trend": "increasing"
  }
}
```

## Analysis Categories & Detection

### Status Change Detection
- **Advancing:** Draft → In Progress → QA → Complete
- **Regressing:** In Progress → Draft (concerns)
- **Stalled:** No status change in 2+ business days
- **Blocked:** Status indicates waiting (Pending Approval, etc.)

### Comment Analysis Keywords
**Questions (🤔):**
- "@", "?", "unclear", "not sure", "need clarification"
- "I don't see", "where is", "how do I"

**Blockers (🚧):**
- "blocked", "waiting", "need access", "can't proceed"
- "credentials", "permission", "approval"

**Progress Updates (✅):**
- "completed", "finished", "ready", "done"
- "deployed", "merged", "tested"

### Risk Assessment Levels
**🔴 High Risk:**
- Due within 24h with blockers
- Multiple days without progress
- Assignee asking fundamental questions

**🟡 Medium Risk:**
- Due within 72h
- Dependencies on other blocked items
- Recent status regression

**🟢 Low Risk:**
- On track with recent progress
- Clear next steps identified
- No blocking dependencies

## Daily Execution Workflow

### Morning Standup Preparation (Automated)
1. **Get Current Sprint Data**
   ```bash
   jql: "project = ECD AND sprint in openSprints()"
   ```

2. **Analyze Each Item for Recent Activity**
   ```bash
   # Check changelog for last 24h activity
   # Extract new comments since last analysis
   # Identify status transitions
   ```

3. **Compare with Previous Day**
   ```bash
   # Load yesterday's report if exists
   # Generate comparison insights
   # Identify stuck/advancing items
   ```

4. **Generate Report**
   ```bash
   # Create today's markdown report
   # Update sprint metadata cache
   # Generate actionable insights
   ```

### Key Output Files

#### Daily Report: `[SPRINT-NAME]/[DATE].md`
- Ready-to-read standup talking points
- Prioritized action items with owners
- Day-to-day progress tracking
- Risk escalation alerts

#### Sprint Metadata: `[SPRINT-NAME]/sprint-metadata.json`
- Cached sprint information
- Velocity tracking data
- Historical completion patterns

#### Current Sprint Tracker: `current-sprint.json`
```json
{
  "active_sprint": "CM Sprint 3",
  "last_updated": "2025-08-21T12:00:00.000Z",
  "reports_generated": 5,
  "next_sprint_detection": "automatic"
}
```

## Advanced Features

### Blocker Pattern Recognition
- Track recurring blocker types
- Identify team members who frequently get blocked
- Flag infrastructure/access issues that affect multiple items

### Velocity Tracking
- Items completed per day
- Average time in each status
- Sprint burndown prediction
- Historical sprint comparison

### Team Communication Analysis
- Question response time tracking
- Identify bottleneck team members
- Communication effectiveness metrics

### Risk Prediction
- Items likely to miss sprint deadlines
- Dependencies that could cascade delays
- Resource allocation imbalances

## Integration Opportunities
- **Slack notifications** for high-risk items
- **Email summaries** for stakeholders
- **Calendar integration** for due date tracking
- **GitHub correlation** for code activity vs ticket progress

## Usage Examples

### Generate Today's Standup Report
```bash
# Manual execution
python standup_analysis.py --date 2025-08-21

# With comparison to previous day
python standup_analysis.py --date 2025-08-21 --compare-previous

# Focus on specific team member
python standup_analysis.py --assignee "Mohamed Belkahla" --date 2025-08-21
```

### Sprint Summary Generation
```bash
# Generate end-of-sprint retrospective
python standup_analysis.py --sprint "CM Sprint 3" --summary

# Compare multiple sprints
python standup_analysis.py --compare-sprints "CM Sprint 2,CM Sprint 3"
```

This workflow provides comprehensive daily standup insights while building historical knowledge for sprint retrospectives and team performance analysis.
