# Definition of Ready Enforcement Procedure

## Overview

This procedure enforces that all active work meets the Definition of Ready requirements by monitoring three critical compliance areas:

1. **Deadlines (Due Dates)** - All In Progress, Ready for Dev, and Ready for QA tickets must have due dates
2. **Hours Estimates (Original Estimate)** - All active work must have time estimates for capacity planning
3. **Refinement Time Limits** - Tickets in "In Refinement" status must not exceed 2 days without action

**Frequency:** Daily (part of standup workflow Section 7)
**Owner:** Definition of Ready Enforcer subagent
**Actions:** Query violations, post Jira comments, generate standup report section

---

## Enforcement Rules

### Rule 1: Missing Deadlines

**Requirement:** All tickets in active work statuses must have a due date set.

**JQL Query:**
```jql
project = ECD
AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND duedate IS EMPTY
ORDER BY status ASC, updated DESC
```

**Action:**
- Post Jira comment on ticket
- Tag assignee
- Include in daily standup report
- Track compliance rate

**Jira Comment Template:**
```markdown
📅 **MISSING DEADLINE**

This ticket has been **{status}** for **{days}** days without a due date set.

**Required Action:** @{assignee_account_id} - Please set a due date by EOD today for capacity planning and sprint tracking.

**Why this matters:**
- Enables deadline risk monitoring
- Improves sprint forecasting
- Provides visibility to stakeholders

---
*Automated reminder from Definition of Ready Enforcer*
```

**Note:** The @{assignee_account_id} uses Jira's mention format with the user's account ID, which triggers a notification to the assignee.

---

### Rule 2: Missing Hours Estimates

**Requirement:** All tickets in active work statuses must have Original Estimate (timeoriginalestimate) set.

**JQL Query:**
```jql
project = ECD
AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND timeoriginalestimate IS EMPTY
ORDER BY status ASC, updated DESC
```

**Jira Field:** `timeoriginalestimate` (stored in seconds)
- Example: 3600 = 1 hour, 28800 = 8 hours

**Action:**
- Post Jira comment on ticket
- Tag assignee
- Include in daily standup report
- Track compliance rate

**Jira Comment Template:**
```markdown
⏱️ **MISSING HOURS ESTIMATE**

This ticket does not have an **Original Estimate** set.

**Required Action:** @{assignee_account_id} - Please add time estimate in the "Original Estimate" field.

**How to set:**
1. Edit ticket
2. Find "Original Estimate" field
3. Enter estimate (e.g., "4h", "2d", "1w")

**Why this matters:**
- Enables capacity planning
- Improves sprint velocity tracking
- Helps identify workload imbalances

---
*Automated reminder from Definition of Ready Enforcer*
```

**Note:** The @{assignee_account_id} uses Jira's mention format with the user's account ID, which triggers a notification to the assignee.

---

### Rule 3: Stalled Refinement (> 2 Days)

**Requirement:** Tickets in "In Refinement" status must not remain there longer than 2 days without:
- Transitioning to "Ready for Development" or "Ready for Design", OR
- Asking clarifying questions in comments

**JQL Query:**
```jql
project = ECD
AND sprint in openSprints()
AND status = "In Refinement"
AND updated < -2d
ORDER BY updated ASC
```

**Analysis Logic:**
```python
for ticket in refinement_tickets:
    days_in_refinement = (today - ticket.status_entered_date).days

    if days_in_refinement <= 2:
        continue  # Still within acceptable window

    # Check comment activity for questions
    recent_comments = get_comments_since(ticket, days=2)
    has_questions = any(
        comment for comment in recent_comments
        if "?" in comment.body and comment.author != "Remington (PM Agent)"
    )

    if has_questions:
        # Questions asked but still in refinement
        post_refinement_reminder_with_questions(ticket)
    else:
        # No questions asked - should move forward
        post_refinement_completion_reminder(ticket)
```

**Action (No Questions Asked):**
- Post Jira comment with urgency
- Tag assignee + PM
- Mark as HIGH priority in standup report

**Jira Comment Template (No Questions):**
```markdown
🚨 **COMPLETE REFINEMENT**

This ticket has been in **In Refinement** status for **{days} days** without any questions asked.

**Required Action:** @{assignee_account_id} - Please choose one:
1. **Transition to "Ready for Development"** if refinement is complete
2. **Transition to "Ready for Design"** if design is needed
3. **Ask clarifying questions** if more information is required

**Why this matters:**
- Prevents bottlenecks in refinement phase
- Keeps sprint velocity healthy
- Ensures work doesn't stall

---
*Automated reminder from Definition of Ready Enforcer (2-day limit)*
```

**Note:** The @{assignee_account_id} uses Jira's mention format with the user's account ID, which triggers a notification to the assignee.

**Action (Questions Asked):**
- Post Jira comment as reminder
- Tag assignee
- Mark as MEDIUM priority in standup report

**Jira Comment Template (With Questions):**
```markdown
⏰ **REFINEMENT REMINDER**

This ticket has been in **In Refinement** status for **{days} days** with pending questions.

**Last Comment:** {last_comment_author} asked a question {hours_ago} hours ago

**Required Action:** @{assignee_account_id} - Please clarify the pending questions and move this ticket forward.

**Status Check:**
- Are questions answered? → Transition to "Ready for Development" or "Ready for Design"
- Need more info? → Follow up with stakeholders

---
*Automated reminder from Definition of Ready Enforcer*
```

**Note:** The @{assignee_account_id} uses Jira's mention format with the user's account ID, which triggers a notification to the assignee.

---

## Implementation

### Daily Execution Process

**Step 1: Query Violations**
```python
# Query all three violation types
missing_deadlines = search_jira_issues(jql_missing_deadlines)
missing_estimates = search_jira_issues(jql_missing_estimates)
stalled_refinement = search_jira_issues(jql_stalled_refinement)
```

**Step 2: Analyze Refinement Tickets**
```python
refinement_violations = []

for ticket in stalled_refinement:
    # Calculate days in refinement
    status_history = get_status_history(ticket)
    entered_refinement = find_status_entry(status_history, "In Refinement")
    days_in_refinement = (today - entered_refinement).days

    # Check for questions
    comments = get_comments_since(ticket, days=2)
    has_questions = check_for_questions(comments)

    refinement_violations.append({
        "key": ticket.key,
        "summary": ticket.summary,
        "assignee": ticket.assignee,
        "days": days_in_refinement,
        "has_questions": has_questions,
        "last_updated": ticket.updated
    })
```

**Step 3: Post Jira Comments**
```python
# Post comments for each violation type
for ticket in missing_deadlines:
    post_jira_comment(ticket.key, generate_missing_deadline_comment(ticket))

for ticket in missing_estimates:
    post_jira_comment(ticket.key, generate_missing_estimate_comment(ticket))

for ticket in refinement_violations:
    if ticket["has_questions"]:
        post_jira_comment(ticket["key"], generate_refinement_reminder_questions(ticket))
    else:
        post_jira_comment(ticket["key"], generate_refinement_completion_reminder(ticket))
```

**Step 4: Generate Standup Report Section**
```python
report_section = generate_dor_enforcement_report({
    "missing_deadlines": missing_deadlines,
    "missing_estimates": missing_estimates,
    "stalled_refinement": refinement_violations
})

return report_section
```

---

## Standup Report Output Format

```markdown
📋 7. MISSING ESTIMATES, DEADLINES & STALLED REFINEMENT

🚫 IN PROGRESS WITHOUT DUE DATES (X tickets)
- **ECD-123**: "Feature implementation" - In Progress for 3 days
  - Assignee: @Mohamed | Priority: High
  - ACTION: 📅 Set due date by EOD today
  - Link: https://citemed.atlassian.net/browse/ECD-123

⏱️ IN PROGRESS WITHOUT HOURS ESTIMATE (X tickets)
- **ECD-456**: "API integration" - In Progress for 2 days
  - Assignee: @Ahmed | Priority: High
  - ACTION: ⏱️ Add Original Estimate for capacity planning
  - Link: https://citemed.atlassian.net/browse/ECD-456

🔄 STALLED IN REFINEMENT (> 2 days) (X tickets)

WITHOUT QUESTIONS ASKED:
- **ECD-789**: "Dashboard redesign" - In Refinement for 4 days
  - Assignee: @Thanh | Last Updated: 4 days ago
  - ACTION: 🚨 COMPLETE REFINEMENT NOW - Transition to "Ready for Development" or "Ready for Design" OR ask clarifying questions
  - Link: https://citemed.atlassian.net/browse/ECD-789

WITH QUESTIONS ASKED:
- **ECD-234**: "Report generation" - In Refinement for 3 days
  - Assignee: @Valentin | Last Comment: @Valentin asked question 1 day ago
  - ACTION: ⏰ REMINDER: Awaiting clarification - still in refinement
  - Link: https://citemed.atlassian.net/browse/ECD-234

---

📊 COMPLIANCE SUMMARY

| Requirement | Compliant | Total | Rate |
|-------------|-----------|-------|------|
| Due Dates Set | 18 | 20 | 90% |
| Hours Estimates | 15 | 20 | 75% |
| Refinement < 2d | 8 | 10 | 80% |

**Target:** 100% compliance for In Progress, Ready for Dev, Ready for QA
**Overall Health:** 🟠 NEEDS IMPROVEMENT

**Actions Taken:**
- Posted 2 Jira comments for missing deadlines
- Posted 5 Jira comments for missing estimates
- Posted 2 Jira comments for stalled refinement
```

---

## Success Metrics

### Compliance Targets
- **Due Dates:** ≥ 95% of active work has deadlines set
- **Hours Estimates:** ≥ 90% of active work has time estimates
- **Refinement Time:** ≥ 95% of tickets exit refinement within 2 days

### Trend Tracking
- Weekly compliance rate changes
- Average time to resolution after reminder
- Number of repeat offenders

### Enforcement Effectiveness
- % of violations resolved within 24 hours of comment
- % of violations resolved within 48 hours
- % requiring escalation to PM/Tech Lead

---

## Escalation Path

### Tier 1: Automated Jira Comment (Day 1)
- Post reminder comment
- Tag assignee
- Include in daily standup report

### Tier 2: Slack Notification (Day 2)
If violation persists for 2+ days:
- Post Slack message in dev channel
- Tag assignee + PM
- Include urgency indicator

### Tier 3: PM/Tech Lead Escalation (Day 3)
If violation persists for 3+ days:
- Create escalation ticket
- Tag PM + Tech Lead + CTO
- Review in standup meeting

---

## Configuration

**CloudId:** `67bbfd03-b309-414f-9640-908213f80628`
**Project:** ECD (Evidence Cloud Development)

**Monitored Statuses:**
- In Progress
- Ready for Development
- Ready for QA
- In Refinement (for Rule 3 only)

**Refinement Time Limit:** 2 business days

**Required Fields:**
- `duedate` (Due Date)
- `timeoriginalestimate` (Original Estimate in seconds)

---

## Integration Points

**Called By:**
- Standup Orchestrator (Section 7 of daily standup)

**Uses:**
- Jira Manager (for JQL queries and comment posting)
- Atlassian MCP (`mcp__atlassian__searchJiraIssuesUsingJql`)
- Atlassian MCP (`mcp__atlassian__addCommentToJiraIssue`)

**Outputs:**
- Section in daily standup report
- Jira comments on violating tickets
- Compliance metrics for tracking

---

**Last Updated:** 2025-11-26
**Maintained By:** Project Manager Agent
