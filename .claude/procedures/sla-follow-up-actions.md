# SLA Follow-Up Actions and Escalation Procedures

## Overview
This document defines the automated actions taken when SLA violations are detected. Actions are escalated through four levels based on violation severity and duration.

## Escalation Philosophy
- **Start Gentle:** First violations receive friendly reminders
- **Increase Visibility:** Repeated violations get team attention
- **Escalate Appropriately:** Persistent issues involve leadership
- **Always Professional:** Automated messages maintain supportive tone

## Four-Level Escalation Matrix

### Level 1: Soft Reminder (First SLA Breach)

**Triggers:**
- First time item breaches SLA (0-2 hours overdue)
- No previous reminder sent in last 48 hours

**Actions:**
1. Post friendly reminder comment in Jira
2. Tag responsible developer using bold format
3. Include in standup report under "Warnings" section
4. NO separate Slack thread yet

**Tone:** Helpful, non-urgent, assumes good intent

**Frequency:** Once per violation

---

### Level 2: Direct Alert (2+ Days Overdue)

**Triggers:**
- Item is 2+ business days overdue
- Level 1 reminder was sent but no response
- Approaching sprint risk threshold

**Actions:**
1. Post "OVERDUE" flagged comment in Jira
2. Tag responsible developer with @mention
3. Create dedicated Slack thread tagging developer
4. Include in standup report under "Critical Follow-Ups"
5. Log violation in tracking system

**Tone:** Urgent but professional, clear action required

**Frequency:** Daily reminders until resolved

---

### Level 3: Team Escalation (4+ Days Overdue)

**Triggers:**
- Item is 4+ business days overdue
- Level 2 alerts haven't resolved issue
- Blocking sprint progress or affecting other work

**Actions:**
1. Post escalation notice in Jira tagging developer + tech lead
2. Create/update Slack thread adding tech lead to conversation
3. Include in standup report under "Escalated Items"
4. Notify PM in private Slack DM
5. Flag as "At Risk" in sprint tracking

**Tone:** Serious concern, team support offered

**Frequency:** Every other day until resolved

---

### Level 4: Leadership Escalation (7+ Days Overdue)

**Triggers:**
- Item is 7+ business days overdue
- All previous escalations failed
- Critical sprint risk or customer impact

**Actions:**
1. Post leadership notification in Jira tagging CTO/PM
2. Send direct Slack DM to CTO with summary
3. Include in standup report as "Sprint Risk"
4. Schedule intervention meeting
5. Consider sprint re-planning

**Tone:** Critical situation, immediate action required

**Frequency:** Continuous daily tracking until resolved

---

## Action Templates by Scenario

### Jira Comment Response Overdue

#### Level 1 Template:
```markdown
📅 **Friendly Reminder** - @{developer_name}

There's a comment from {commenter_name} from {days_ago} days ago that hasn't received a response yet.

**SLA Target:** 2 business days for comment responses
**Current Status:** {days_overdue} days without response

When you get a chance, could you please provide an update? Thanks!

---
*Automated PM SLA tracking*
```

#### Level 2 Template:
```markdown
⚠️ **OVERDUE: Action Required** - @{developer_name}

This comment thread is now {days_overdue} days overdue for follow-up.

**Comment From:** {commenter_name}
**Posted:** {comment_date}
**SLA Target:** 2 business days
**Current Status:** {days_overdue} days overdue

**Required Action:** Please respond to the comment or update the ticket status if this is no longer relevant.

A Slack thread has been created for visibility.

---
*Automated PM escalation - Level 2*
```

#### Level 3 Template:
```markdown
🚨 **ESCALATION: Team Support Needed** - @{developer_name} @{tech_lead_name}

This comment thread has been overdue for {days_overdue} days and requires immediate attention.

**Comment From:** {commenter_name}
**Posted:** {comment_date}
**Days Overdue:** {days_overdue}
**Sprint Impact:** {impact_description}

**Action Required:**
- Developer: Provide response or update status
- Tech Lead: Review if reassignment or support needed

This is now flagged in our sprint risk assessment.

---
*Automated PM escalation - Level 3*
```

### PR Review Overdue

#### Level 1 Template:
```markdown
📋 **Review Reminder**

This PR has been waiting for initial review for {hours_elapsed} hours.

**PR:** #{pr_number} - {pr_title}
**Author:** @{author_name}
**Requested Reviewers:** @{reviewer1} @{reviewer2}
**SLA Target:** 24-48 hours for initial review

Per our [PR Workflow Policy](https://citemed.atlassian.net/wiki/spaces/Engineerin/pages/87031809), reviews should begin within 48 hours.

---
*Automated PM SLA tracking*
```

#### Level 2 Template:
```markdown
⚠️ **OVERDUE: PR Review Needed**

This PR is now {hours_overdue} hours overdue for review.

**PR:** #{pr_number} - {pr_title}
**Author:** @{author_name}
**Awaiting Review From:** @{reviewer_names}
**Hours Overdue:** {hours_overdue}

**Required Action:** Reviewers, please begin review or reassign if unavailable.

A Slack alert has been sent to #dev-team.

---
*Automated PM escalation - Level 2*
```

### PR Code Updates Stalled

#### Level 1 Template:
```markdown
💻 **PR Activity Check**

This PR hasn't had new commits in {days_elapsed} days.

**PR:** #{pr_number} - {pr_title}
**Author:** @{author_name}
**Last Commit:** {last_commit_date}
**SLA Target:** Code updates within 2 business days

**Status Check:**
- Are you waiting on feedback?
- Should this PR be marked as draft?
- Is there a blocker we should know about?

---
*Automated PM SLA tracking*
```

#### Level 2 Template:
```markdown
⚠️ **OVERDUE: PR Needs Updates**

This PR has been stalled for {days_overdue} days without new commits.

**PR:** #{pr_number} - {pr_title}
**Author:** @{author_name}
**Last Commit:** {last_commit_date}
**Days Overdue:** {days_overdue}
**Linked Ticket:** {jira_ticket}

**Required Action:** Please push updates or communicate blockers/timeline.

Per our PR policy, stalled PRs impact sprint velocity and should be updated or closed.

---
*Automated PM escalation - Level 2*
```

### Blocked Ticket - No Updates

#### Level 1 Template:
```markdown
🚫 **Blocked Ticket Status Check** - @{developer_name}

This ticket has been in "Blocked" status for {days_blocked} days.

**SLA Requirement:** Daily status updates on blocked tickets
**Last Update:** {last_update_date}

**Please provide:**
- Current blocker status
- Steps being taken to resolve
- Estimated time to unblock
- Any help needed from team

---
*Automated PM SLA tracking*
```

#### Level 2 Template:
```markdown
⚠️ **OVERDUE: Blocked Ticket Update Required** - @{developer_name}

This ticket has been blocked for {days_blocked} days without updates.

**Ticket:** {ticket_key}
**Days Blocked:** {days_blocked}
**Last Update:** {last_update_date}
**Sprint Impact:** At risk for delivery

**Required Action:**
1. Provide immediate status update
2. Identify if escalation needed
3. Update daily until unblocked

Per our SDLC policy, blocked tickets require daily communication.

---
*Automated PM escalation - Level 2*
```

#### Level 3 Template:
```markdown
🚨 **ESCALATION: Blocked Ticket Intervention** - @{developer_name} @{tech_lead_name}

This ticket has been blocked for {days_blocked} days and requires team intervention.

**Ticket:** {ticket_key}
**Days Blocked:** {days_blocked}
**Sprint Deadline:** {deadline_date}
**Impact:** {impact_description}

**Action Required:**
- Developer: Clarify blocker details
- Tech Lead: Assess if re-assignment or resources needed
- Team: Identify solutions or workarounds

This is now flagged as a critical sprint risk.

---
*Automated PM escalation - Level 3*
```

### Pending Approval Stuck

#### Level 1 Template:
```markdown
✅ **Approval Pending** - @{approver_name}

This ticket has been in "Pending Approval" status for {hours_elapsed} hours.

**Ticket:** {ticket_key}
**Assignee:** @{developer_name}
**Awaiting Approval From:** @{approver_name}
**SLA Target:** 48 hours

Per our SDLC workflow, approvals should be completed within 2 business days.

---
*Automated PM SLA tracking*
```

#### Level 2 Template:
```markdown
⚠️ **OVERDUE: Approval Required** - @{approver_name}

This ticket approval is now {hours_overdue} hours overdue.

**Ticket:** {ticket_key}
**Developer:** @{developer_name}
**Awaiting Approval From:** @{approver_name}
**Hours Overdue:** {hours_overdue}
**Demo/Staging Link:** {staging_link}

**Required Action:** Please review and approve/request changes so development can proceed.

---
*Automated PM escalation - Level 2*
```

---

## Slack Message Templates

### Slack Thread for Level 2 Escalation

```
🚨 @{developer_name} - Follow-up needed

**Item:** {item_type} - {item_id}
**Link:** {item_url}

**Status:** {days_hours_overdue} overdue
**SLA:** {sla_threshold}
**Required:** {specific_action}

Please update when you have a moment - thanks! 🙏

**Context:** {brief_summary}
```

### Slack DM to Tech Lead (Level 3)

```
Hi @{tech_lead_name},

Heads up - we have an escalated SLA violation that may need your attention:

**Item:** {item_description}
**Developer:** @{developer_name}
**Days Overdue:** {days_overdue}
**Sprint Impact:** {impact_level}

I've posted in Jira and created a Slack thread. Can you check if developer needs support or if reassignment should be considered?

Jira: {jira_link}
Slack Thread: {slack_thread_link}

Thanks!
```

### Slack DM to CTO (Level 4)

```
@{cto_name} - Critical SLA escalation

We have a Level 4 SLA violation that requires leadership intervention:

**Summary:** {item_description}
**Developer:** @{developer_name}
**Days Overdue:** {days_overdue}
**Previous Escalations:** Levels 1-3 completed
**Sprint Risk:** {risk_assessment}
**Customer Impact:** {customer_impact}

**Recommendation:** {recommended_action}

This may require:
- Direct conversation with team member
- Sprint scope adjustment
- Resource reallocation

Details:
- Jira: {jira_link}
- Slack Thread: {slack_thread_link}
- Standup Report: {report_link}
```

---

## When NOT to Escalate

### Exceptions:
- **Holidays/PTO:** Developer is out of office (check Slack status)
- **Recent Communication:** Developer commented within last 4 hours
- **External Dependency:** Clearly documented external blocker
- **After Hours:** Violation occurred outside business hours only
- **Weekend Activity:** SLA breach happened over weekend

### De-escalation:
- Once developer responds/acts, reset escalation level
- Send acknowledgment: "Thanks for the update! Marking this as addressed."
- Remove from critical tracking lists
- Log resolution time for metrics

---

## Escalation Decision Tree

```
SLA Violation Detected
    ↓
Is this first occurrence?
    YES → Level 1 (Soft Reminder)
    NO → Check days overdue
        ↓
    0-2 days → Level 1
    2-4 days → Level 2 (Direct Alert)
    4-7 days → Level 3 (Team Escalation)
    7+ days → Level 4 (Leadership)
    ↓
Check for exceptions:
    - Developer on PTO? → Skip escalation
    - External blocker? → Adjust timeline
    - Recent response? → Reset clock
    ↓
Execute escalation actions:
    - Post Jira comment
    - Create/update Slack thread
    - Notify stakeholders
    - Log in tracking system
```

---

## Success Metrics for Escalations

### Target Resolution Rates:
- **Level 1:** 80% resolved without further escalation
- **Level 2:** 15% require this level
- **Level 3:** <5% reach team escalation
- **Level 4:** <1% require leadership

### Response Time Improvements:
- Average resolution time decreasing monthly
- Escalation rate decreasing sprint-over-sprint
- Developer response time improving

### Team Health:
- No individual with >3 escalations per sprint
- Recognition for consistent on-time performance
- Positive team feedback on reminder helpfulness

---

## Continuous Improvement

### Weekly Review:
- Analyze escalation patterns
- Identify systemic issues (not individual blame)
- Adjust templates if tone issues arise
- Celebrate improvements

### Monthly Tuning:
- Review SLA thresholds with team
- Update templates based on feedback
- Recognize teams with excellent compliance
- Share learnings across organization

---

**Document Owner:** Project Management
**Last Updated:** 2025-10-19
**Next Review:** Monthly
**Related Documents:**
- [SLA Monitoring Workflow](../workflows/sla-monitoring.md)
- [Developer Lookup and Tagging](./developer-lookup-tagging.md)
- [Slack Integration Setup](./slack-setup-instructions.md)
