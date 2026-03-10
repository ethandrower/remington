---
name: sla-enforcement
description: Provides knowledge about Service Level Agreement enforcement including SLA definitions, business hours calculations, escalation decision trees, and exception handling. Use when monitoring SLAs, calculating response times, executing escalations, or evaluating SLA violations for Jira comments, PR reviews, blocked tickets, and pending approvals.
---

# SLA Enforcement Skill

## Purpose
This skill provides knowledge about Service Level Agreement (SLA) enforcement, including SLA definitions, business hours calculations, escalation decision trees, and exception handling.

## SLA Philosophy

### Why SLAs Matter

**Team Benefits:**
- Predictable response times build trust
- Clear expectations prevent confusion
- Early warning system for at-risk items
- Systematic accountability (not personal blame)

**Business Benefits:**
- Maintain sprint velocity and commitments
- Prevent work from getting stuck
- Enable reliable planning and forecasting
- Improve stakeholder confidence

**Individual Benefits:**
- Know when your response is truly needed
- Understand priority and urgency
- Protect focus time (no unexpected urgency)
- Fair evaluation based on clear metrics

### SLA Principles

**1. Measure Outcomes, Not Activity**
- SLAs track responsiveness and throughput
- Not surveillance or micromanagement
- Focus on system health, not blame

**2. Business Hours Only**
- Weekends and holidays don't count
- Work-life balance is respected
- Emergencies are separate escalation path

**3. Systematic Escalation**
- Escalations are automatic and evidence-based
- Not personal judgment calls
- Predictable and fair for everyone

**4. Continuous Improvement**
- SLAs should improve team efficiency
- Adjust based on data and feedback
- Celebrate improvements in compliance

## SLA Definitions (CiteMed)

### Communication SLAs

#### 1. Jira Comment Response Time
- **Target:** 2 business days maximum
- **Applies To:** All active tickets in current sprint
- **Measurement:** Time from comment posted to response from assignee/responsible party
- **Exclusions:** Comments marked as "FYI" or informational
- **Owner:** Ticket assignee (if question directed at them) or commenter (if awaiting their follow-up)

**Rationale:**
- Ensures stakeholder questions don't go unanswered
- Prevents communication delays from stalling work
- 2 days provides reasonable time without blocking progress

**Example Scenario:**
```
Timeline:
- Monday 10am: Product Manager asks clarifying question in ECD-123
- SLA Clock Starts: Monday 10am
- SLA Deadline: Wednesday 5pm (2 business days later)
- Developer responds: Tuesday 2pm ✅ COMPLIANT (1.16 days)
```

#### 2. PR Review Turnaround
- **Initial Review:** 24-48 hours from PR submission
- **Re-review:** 24 hours after developer addresses feedback
- **Final Approval:** 24 hours after last code changes
- **Owner:** Assigned reviewers (Tech Lead, Product Manager)

**Rationale:**
- Critical for maintaining sprint velocity
- Prevents PR bottlenecks
- Based on official PR Workflow Policy

**Example Scenario:**
```
Timeline:
- Monday 3pm: PR opened, reviewers assigned
- SLA Clock Starts: Monday 3pm
- SLA Deadline (Initial): Wednesday 5pm (24-48 hour range)
- Reviewer comments: Tuesday 11am ✅ COMPLIANT (20 hours)
- Developer fixes: Tuesday 4pm
- SLA Clock Restarts: Tuesday 4pm
- SLA Deadline (Re-review): Wednesday 4pm (24 hours)
- Final approval: Wednesday 10am ✅ COMPLIANT (18 hours)
```

#### 3. Developer Response to PR Feedback
- **Critical Fixes:** 4 hours
- **Feature Updates:** 24 hours
- **Non-urgent Changes:** 48 hours
- **Owner:** PR author/developer

**Rationale:**
- Keeps review process moving
- Reduces context switching cost
- Maintains reviewer engagement

### Work Progress SLAs

#### 4. PR Staleness (No Code Updates)
- **Target:** 2 business days maximum without new commits
- **Applies To:** All open PRs marked "In Progress"
- **Measurement:** Time since last commit push
- **Exceptions:** PRs awaiting review (different SLA applies)
- **Owner:** PR author

**Rationale:**
- Detects abandoned or stalled work
- Ensures continuous progress
- Prevents zombie PRs

**Example Scenario:**
```
Timeline:
- Monday 2pm: Last commit pushed to PR
- SLA Clock Starts: Monday 2pm
- SLA Deadline: Wednesday 5pm (2 business days)
- No new commits by Thursday → ❌ VIOLATION (2.5 days)
- Action: Escalation to developer (Level 2 - Jira + Slack)
```

#### 5. In-Progress Ticket Without Git Activity
- **Target:** 3 business days maximum
- **Applies To:** Tickets in "In Development" status
- **Measurement:** Time since last commit on related branch
- **Exceptions:** Research/design tasks, external dependencies
- **Owner:** Ticket assignee

**Rationale:**
- Code-ticket gap detection
- Prevents ticket status from being inaccurate
- Identifies hidden blockers

#### 6. Pending Approval Duration
- **Target:** 48 hours maximum in "Pending Approval" status
- **Applies To:** All tickets awaiting PM/CTO sign-off
- **Measurement:** Time since status changed to "Pending Approval"
- **Owner:** Product Manager or CTO

**Rationale:**
- Prevents approval bottlenecks
- Ensures work gets to "Done" promptly
- Maintains team velocity

### Blocker Resolution SLAs

#### 7. Blocked Ticket Communication
- **Target:** Daily status update required
- **Applies To:** All tickets in "Blocked" status
- **Measurement:** Time since last comment/update on blocked ticket
- **Escalation:** Automatic after 2 days blocked
- **Owner:** Ticket assignee

**Rationale:**
- Visibility into blocking issues
- Prevents blockers from being forgotten
- Enables proactive unblocking

**Example Scenario:**
```
Timeline:
- Monday 10am: Ticket moved to "Blocked", comment added explaining blocker
- SLA Clock Starts: Monday 10am
- Daily Update Due: Tuesday 10am
- Developer adds update: Tuesday 9am ✅ COMPLIANT
- Next Update Due: Wednesday 9am
- No update by Wednesday 5pm → ⚠️ WARNING
```

#### 8. Blocked Ticket Resolution
- **Target:** 2 business days maximum in blocked status
- **Critical Escalation:** 5 days triggers leadership involvement
- **Applies To:** All blocked tickets
- **Owner:** Tech Lead (for technical blockers), PM (for business/requirement blockers)

**Rationale:**
- Forces active blocker resolution
- Prevents long-term stagnation
- Escalates systemic issues to leadership

### QA and Testing SLAs

#### 9. QA Turnaround Time
- **Target:** 48 hours from "In QA" status entry
- **Applies To:** All tickets in QA status
- **Measurement:** Time in QA status
- **Owner:** QA Lead (Joshua)

**Rationale:**
- Maintains end-to-end delivery pace
- Prevents QA bottleneck
- Supports sprint completion goals

#### 10. Bug Fix Response Time
- **Critical Bugs:** 1 business day
- **High Priority:** 3 business days
- **Medium/Low:** Sprint-based (no specific SLA)
- **Owner:** Assigned developer

**Rationale:**
- Severity-based prioritization
- Balances urgency with planned work
- Prevents production issues from languishing

## Business Hours Calculation

### Working Hours Definition
```python
BUSINESS_DAYS = [0, 1, 2, 3, 4]  # Monday-Friday (Python weekday)
BUSINESS_START = 9  # 9 AM
BUSINESS_END = 17   # 5 PM
TIMEZONE = "America/New_York"  # Or team's timezone
```

### Holidays
```python
HOLIDAYS_2025 = [
    "2025-01-01",  # New Year's Day
    "2025-05-26",  # Memorial Day
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
    # Add company-specific holidays
]
```

### SLA Clock Behavior

**Clock Starts:**
- When triggering event occurs (comment posted, status changed, etc.)
- Timestamp recorded in SLA tracking system

**Clock Pauses:**
- Outside business hours (before 9am, after 5pm)
- Weekends (Saturday, Sunday)
- Company holidays

**Clock Resumes:**
- Next business day at 9am
- After holiday at 9am

**Clock Resets:**
- When action is taken (response posted, code committed, etc.)
- New SLA clock may start if further action required

### Business Hours Calculation Examples

**Example 1: Simple Calculation**
```
Event: Comment posted Monday 10am
SLA: 2 business days
Calculation:
  - Monday 10am to Monday 5pm = 7 hours (Day 1)
  - Tuesday 9am to Tuesday 5pm = 8 hours (Day 1 cont'd)
  - Tuesday 5pm to Wednesday 5pm = 8 hours (Day 2)
Deadline: Wednesday 2pm (48 business hours after Monday 10am)
```

**Example 2: Weekend Crossing**
```
Event: Comment posted Friday 3pm
SLA: 2 business days
Calculation:
  - Friday 3pm to Friday 5pm = 2 hours (Day 1 start)
  - Weekend: PAUSED
  - Monday 9am to Monday 5pm = 8 hours (Day 1 cont'd, total 10h)
  - Tuesday 9am to Tuesday 5pm = 8 hours (Day 2, total 18h)
  - Wednesday 9am to Wednesday 5pm = 8 hours (Day 2 cont'd)
Deadline: Tuesday 4pm (48 business hours after Friday 3pm)
```

**Example 3: Holiday Impact**
```
Event: Comment posted Wednesday 2pm (Thanksgiving week)
SLA: 2 business days
Holidays: Thursday (Thanksgiving), Friday (company holiday)
Calculation:
  - Wednesday 2pm to Wednesday 5pm = 3 hours (Day 1 start)
  - Thursday: HOLIDAY, PAUSED
  - Friday: HOLIDAY, PAUSED
  - Weekend: PAUSED
  - Monday 9am to Monday 5pm = 8 hours (Day 1 cont'd, total 11h)
  - Tuesday 9am to Tuesday 5pm = 8 hours (Day 2, total 19h)
  - Wednesday 9am to ... = remaining hours
Deadline: Tuesday 4pm (48 business hours after Wednesday 2pm, excluding holidays)
```

### Python Implementation Reference
```python
import datetime
from typing import List

def calculate_sla_deadline(
    start_time: datetime.datetime,
    business_hours_required: float,
    holidays: List[str]
) -> datetime.datetime:
    """
    Calculate SLA deadline accounting for business hours only.

    Args:
        start_time: When SLA clock started
        business_hours_required: Hours until SLA breach (e.g., 48 for 2 days)
        holidays: List of holiday dates in "YYYY-MM-DD" format

    Returns:
        datetime of SLA deadline
    """
    current_time = start_time
    hours_accumulated = 0.0

    while hours_accumulated < business_hours_required:
        # Skip weekends
        if current_time.weekday() >= 5:  # Saturday or Sunday
            current_time += datetime.timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=0)
            continue

        # Skip holidays
        if current_time.strftime("%Y-%m-%d") in holidays:
            current_time += datetime.timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=0)
            continue

        # If before business hours, jump to 9am
        if current_time.hour < 9:
            current_time = current_time.replace(hour=9, minute=0)

        # If after business hours, jump to next day 9am
        if current_time.hour >= 17:
            current_time += datetime.timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=0)
            continue

        # Calculate hours available today
        hours_left_today = 17 - current_time.hour - (current_time.minute / 60.0)
        hours_needed = business_hours_required - hours_accumulated

        if hours_needed <= hours_left_today:
            # SLA deadline is today
            hours_to_add = hours_needed
            current_time += datetime.timedelta(hours=hours_to_add)
            hours_accumulated = business_hours_required
        else:
            # Move to next business day
            hours_accumulated += hours_left_today
            current_time += datetime.timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=0)

    return current_time
```

## Escalation Decision Trees

### Decision Tree: Jira Comment Response

```
Is there a new comment on ticket?
│
├─ YES → Is comment from stakeholder/PM?
│        │
│        ├─ YES → Is assignee different from commenter?
│        │        │
│        │        ├─ YES → Start SLA clock for assignee
│        │        │        │
│        │        │        └─ Track time until response
│        │        │                │
│        │        │                ├─ Response < 2 days → ✅ COMPLIANT
│        │        │                │
│        │        │                ├─ 0-1 days overdue → ⚠️ Level 1: Soft reminder in Jira
│        │        │                │
│        │        │                ├─ 1-2 days overdue → ⚠️⚠️ Level 2: Jira + Slack thread
│        │        │                │
│        │        │                ├─ 2-3 days overdue → 🚨 Level 3: Team escalation
│        │        │                │
│        │        │                └─ 3+ days overdue → 🚨🚨 Level 4: Leadership notification
│        │        │
│        │        └─ NO → Self-comment, no SLA
│        │
│        └─ NO → Is comment from developer (FYI)?
│                 │
│                 ├─ YES → No SLA (informational)
│                 │
│                 └─ NO → Evaluate case-by-case
│
└─ NO → Continue monitoring
```

### Decision Tree: Blocked Tickets

```
Is ticket in "Blocked" status?
│
├─ YES → How long has it been blocked?
│        │
│        ├─ < 1 day → ✅ Monitor, daily update required
│        │
│        ├─ 1 day, no update → ⚠️ Soft reminder: Request daily status update
│        │
│        ├─ 2 days blocked → ⚠️⚠️ Level 2: Escalate to blocker owner
│        │                    Action: Tag person who can unblock
│        │                    Create Slack thread for visibility
│        │
│        ├─ 3 days blocked → 🚨 Level 3: Team escalation
│        │                    Action: Notify tech lead
│        │                    Sprint risk assessment
│        │                    Consider re-prioritization
│        │
│        └─ 5+ days blocked → 🚨🚨 Level 4: Leadership escalation
│                              Action: Notify leadership
│                              Systemic issue likely
│                              Immediate unblocking required
│
└─ NO → Continue monitoring
```

### Decision Tree: PR Review

```
Is PR opened and ready for review?
│
├─ YES → Are reviewers assigned?
│        │
│        ├─ YES → Track time since PR opened
│        │        │
│        │        ├─ < 24h → ✅ Within SLA
│        │        │
│        │        ├─ 24-48h → ⚠️ Approaching SLA
│        │        │           Send friendly reminder to reviewers
│        │        │
│        │        ├─ 48h-3d → ⚠️⚠️ Level 2: SLA violation
│        │        │           Tag reviewers in Slack
│        │        │           Create thread for visibility
│        │        │
│        │        └─ 3+ days → 🚨 Level 3: Escalate to tech lead
│        │                     Sprint timeline at risk
│        │                     Reassign reviewers if needed
│        │
│        └─ NO → Auto-assign reviewers based on code ownership
│                 Then start SLA tracking
│
└─ NO → Continue monitoring
```

## Exception Handling

### When to Pause SLA

**Legitimate Exceptions:**
- ✅ Waiting on external vendor response
- ✅ Blocked by dependency outside team's control
- ✅ Research/design task (no code expected)
- ✅ Developer is on approved PTO (pause clock)
- ✅ Critical production incident (all hands on deck)

**How to Document Exception:**
```markdown
📌 **SLA EXCEPTION** - ECD-123

**Reason:** Waiting on vendor API documentation
**Expected Resolution:** Oct 25, 2025
**Workaround:** Progressing on other aspects in parallel

SLA clock paused until dependency resolved.
Will resume daily updates when unblocked.
```

### When NOT to Pause SLA

**Invalid Exceptions:**
- ❌ "Too busy with other work" → Prioritization issue, not exception
- ❌ "Forgot to respond" → Human error, not systemic issue
- ❌ "Didn't see the comment" → Notification setup issue, not exception
- ❌ "Waiting for meeting" → Async response expected in meantime

### Handling Edge Cases

**Case: Multiple Reviewers, One Responds**
- SLA is met if ANY assigned reviewer responds within SLA
- If first review is incomplete, re-review SLA applies

**Case: Comment Thread with Multiple Questions**
- SLA resets with each new question from stakeholder
- Batch responses acceptable if all addressed within SLA

**Case: Developer on PTO When Comment Posted**
- SLA clock starts when developer returns
- OR reassign ticket to available developer
- Document in ticket who will respond

**Case: Comment Posted After Hours or on Weekend**
- SLA clock doesn't start until next business day 9am
- Example: Comment Friday 6pm → Clock starts Monday 9am

## SLA Monitoring Best Practices

### Automation is Key

**Automated Detection:**
- Hourly scan for SLA violations
- Automatic escalation execution (no manual intervention)
- Historical tracking for trend analysis
- Alert PM agent when manual review needed

**Manual Review Reserved For:**
- Disputed violations (rare)
- Exception requests
- SLA threshold adjustments
- Process improvement discussions

### Data-Driven Insights

**Track Metrics:**
- Overall compliance rate (target: ≥ 90%)
- Compliance by SLA type (comment response, PR review, etc.)
- Compliance by developer (identify coaching opportunities)
- Trend over time (improving or declining?)
- Escalation rate (how often reaching Level 3/4?)

**Monthly Review:**
- Analyze violation patterns
- Identify systemic bottlenecks
- Adjust SLA thresholds if needed (with team input)
- Celebrate improvements

### Balanced Enforcement

**Not a Gotcha System:**
- SLAs are for team health, not punishment
- Focus on patterns, not individual violations
- Recognize consistent compliance
- Coach for improvement, don't blame

**Escalations Are Information:**
- Level 1-2: Friendly reminders (normal operations)
- Level 3: Process issue, needs team discussion
- Level 4: Systemic problem, leadership action required

---

**This skill enables the PM agent to enforce SLAs systematically, calculate business hours accurately, execute escalations appropriately, and handle exceptions fairly while maintaining team productivity and sprint health.**