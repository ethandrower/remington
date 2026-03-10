# 📋 `/standup` - Daily PM Command Workflow

## Overview
The `/standup` command runs all 5 core project management workflows in sequence to provide a comprehensive daily status report perfect for standup meetings, including SLA compliance monitoring.

## Command Execution Order

### 1. **Sprint Burndown Analysis**
- Analyzes current sprint progress
- Shows epic completion status
- Identifies sprint risks and blockers

### 2. **Code-Ticket Gap Detection**
- Finds tickets marked "In Progress" without git activity
- Flags potential stalled work
- Generates developer alerts

### 3. **Developer Productivity Audit**
- Reviews recent timesheet submissions (last 7 days)
- Validates hours against code complexity
- Recognizes excellent work or flags issues

### 4. **Team Timesheet Analysis**
- Shows team productivity metrics
- Individual developer breakdowns
- Hours correlation with ticket activity

### 5. **SLA Violations & Follow-Up Tracking**
- Monitors Jira comment response times (2 business day SLA)
- Tracks PR review turnaround (24-48 hour SLA per PR policy)
- Detects blocked tickets requiring daily updates
- Flags stale PRs without code updates (2 business day SLA)
- Monitors "Pending Approval" duration (48 hour SLA)
- Categorizes violations (Critical, Warnings, Blocked Items)
- Auto-generates escalation actions (Jira comments, Slack threads)
- Tracks historical compliance trends
- Reports SLA compliance score

## Expected Output Format

```
🏃‍♂️ DAILY STANDUP REPORT - [DATE]
═══════════════════════════════════

📊 1. SPRINT PROGRESS
- Current Sprint: [Name]
- Items Complete: X/Y (Z%)
- Epic Progress: [Epic Name] - X% complete
- Sprint Risk: [HIGH/MEDIUM/LOW]

🚨 2. CODE-TICKET GAPS DETECTED
- [Ticket]: [Status] but no git activity
- [Developer] needs follow-up on [Ticket]
- Total gaps requiring attention: X

🔍 3. PRODUCTIVITY AUDIT (Last 7 Days)
RED FLAGS:
- [Any issues requiring immediate attention]
EXCELLENT WORK:
- [Recognition for high productivity]

📈 4. TEAM PRODUCTIVITY SUMMARY
- Total Team Hours: Xh
- Average Daily Hours: X.Xh per developer
- Most Active: [Developer] (Xh)
- Tickets with Timesheet Activity: X unique tickets

🚨 5. SLA VIOLATIONS & FOLLOW-UP TRACKING

⚠️ CRITICAL (2+ days overdue):
- [Item]: [Type] - @Developer (X days overdue)
  - Action: [Escalation level and actions taken]
  - Links: [Jira/PR/Slack thread links]

⏰ WARNINGS (Approaching SLA):
- [Item]: [Status] (Xh until SLA breach)

🚫 BLOCKED ITEMS (requiring daily updates):
- [Ticket]: Blocked X days - [Action taken]

✅ RECENTLY RESOLVED:
- [Items that were fixed after follow-up]

📊 SLA COMPLIANCE:
- This Sprint: X% on-time (Y violations / Z items)
- 7-Day Trend: X% → Y% (direction)
- Team Avg Response: X.Xh (target: <48h)

💡 ACTION ITEMS:
- [Generated recommendations from analysis]
```

## Usage Triggers

When user types:
- `/standup`
- "Run daily standup analysis"
- "Give me the full PM status"
- "Daily standup report"

## Implementation Notes

- Runs all 5 workflows sequentially
- Combines outputs into single comprehensive report
- Automatically generates action items based on findings
- SLA monitoring includes automated follow-up actions:
  - Posts Jira comments on violations
  - Creates Slack threads for critical items
  - Tags responsible developers
  - Logs violations for historical tracking
- Optimized for standup meeting discussion
- Takes ~45-60 seconds to complete all analysis (including SLA checks)

## Related Documentation

- **SLA Monitoring Workflow:** `.claude/agents/project-manager/workflows/sla-monitoring.md`
- **SLA Follow-Up Actions:** `.claude/agents/project-manager/procedures/sla-follow-up-actions.md`
- **SLA Monitor Script:** `.claude/agents/project-manager/scripts/sla_monitor.py`
