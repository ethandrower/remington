# SLA Monitoring Workflow

## Overview
This workflow defines Service Level Agreements (SLAs) for development processes and automated monitoring/follow-up procedures. These SLAs are derived from our official SDLC and Pull Request Workflow Policy.

## Purpose
- Ensure timely responses to comments, reviews, and blockers
- Prevent work from getting stuck in any workflow stage
- Maintain sprint velocity and delivery commitments
- Provide early warning system for at-risk items

## SLA Definitions

### 1. Communication SLAs

#### Jira Comment Response Time
- **Target:** 2 business days maximum
- **Applies To:** All active tickets in current sprint
- **Measurement:** Time from comment posted to response from assignee/responsible party
- **Exclusions:** Comments marked as "FYI" or informational
- **Owner:** Ticket assignee (if question directed at them) or commenter (if awaiting their follow-up)

#### PR Review SLAs (from PR Workflow Policy)
- **Initial Review:** 24-48 hours from PR submission
- **Re-review:** 24 hours after developer addresses feedback
- **Final Approval:** 24 hours after last code changes
- **Owner:** Assigned reviewers (Tech Lead, Product Manager)

#### Developer Response to PR Feedback
- **Critical Fixes:** 4 hours
- **Feature Updates:** 24 hours
- **Non-urgent Changes:** 48 hours
- **Owner:** PR author/developer

### 2. Work Progress SLAs

#### PR Staleness (No Code Updates)
- **Target:** 2 business days maximum without new commits
- **Applies To:** All open PRs marked "In Progress"
- **Measurement:** Time since last commit push
- **Exceptions:** PRs awaiting review (different SLA applies)
- **Owner:** PR author

#### In-Progress Ticket Without Git Activity
- **Target:** 3 business days maximum
- **Applies To:** Tickets in "In Development" status
- **Measurement:** Time since last commit on related branch
- **Exceptions:** Research/design tasks, external dependencies
- **Owner:** Ticket assignee

#### Pending Approval Duration
- **Target:** 48 hours maximum in "Pending Approval" status
- **Applies To:** All tickets awaiting PM/CTO sign-off
- **Measurement:** Time since status changed to "Pending Approval"
- **Owner:** Product Manager or CTO (per ticket assignment)

### 3. Blocker Resolution SLAs

#### Blocked Ticket Communication
- **Target:** Daily status update required
- **Applies To:** All tickets in "Blocked" status
- **Measurement:** Time since last comment/update on blocked ticket
- **Escalation:** Automatic after 2 days blocked
- **Owner:** Ticket assignee

#### Blocked Ticket Resolution
- **Target:** 2 business days maximum in blocked status
- **Critical Escalation:** 5 days triggers leadership involvement
- **Applies To:** All blocked tickets
- **Owner:** Tech Lead (for technical blockers), PM (for business/requirement blockers)

### 4. QA and Testing SLAs

#### QA Turnaround Time
- **Target:** 48 hours from "In QA" status entry
- **Applies To:** All tickets in QA status
- **Measurement:** Time in QA status
- **Owner:** QA Lead (Joshua)

#### Bug Fix Response Time (from submission)
- **Critical Bugs:** 1 business day
- **High Priority:** 3 business days
- **Medium/Low:** Sprint-based (no specific SLA)
- **Owner:** Assigned developer

## Business Hours & Exclusions

### Working Hours Calculation
- **Business Days:** Monday-Friday
- **Business Hours:** 9am-5pm local time
- **Holidays:** Excluded from SLA calculation
- **Weekends:** Excluded from SLA calculation

### SLA Clock Behavior
- **Starts:** When triggering event occurs (comment posted, status changed, etc.)
- **Pauses:** Outside business hours, on weekends, company holidays
- **Resumes:** Next business day 9am
- **Resets:** When action taken (response posted, code committed, etc.)

## Monitoring Strategy

### Data Collection Points

#### From Jira (via Atlassian MCP):
```jql
# Get all active tickets for SLA monitoring
project = ECD AND sprint in openSprints()
AND status NOT IN (Complete, Cancelled)
```

**Extract:**
- Last comment timestamp and author
- Current assignee
- Status and status change timestamp
- Related PR links
- Blocker flag and duration

#### From Bitbucket (via CLI/API):
```bash
# Get all open PRs
bb pr list --state OPEN

# For each PR, get:
- Last commit timestamp
- Review request timestamp
- First review timestamp
- Unresolved comment threads
- Linked Jira tickets
```

#### From Git (local repositories):
```bash
# Check branch activity for "In Progress" tickets
git log origin/ECD-XXX-* --since="3 days ago" --oneline
```

### Monitoring Frequency

**Continuous Monitoring (via webhooks - Phase 2):**
- Jira comment posted → Immediate SLA tracking start
- PR opened → Immediate review SLA tracking
- Status changed → Immediate new SLA rules apply

**Scheduled Checks (Phase 1):**
- **Hourly:** Critical SLA checks (blocked tickets, overdue reviews)
- **Every 4 hours:** Full SLA scan of all active items
- **Daily 9am:** Comprehensive standup report generation
- **Weekly:** Trend analysis and compliance reporting

## Integration with Standup Workflow

This SLA monitoring runs as **Section 5** of the daily `/standup` command:

```
/standup execution order:
1. Sprint Burndown Analysis
2. Code-Ticket Gap Detection
3. Developer Productivity Audit
4. Team Timesheet Analysis
5. SLA Violations & Follow-Up Tracking  ← NEW
```

See `standup-command.md` for complete workflow integration.

## Output Format

### For Standup Report
- Categorized violations (Critical, Warning, Info)
- Responsible party identification
- Days/hours overdue
- Actions automatically taken
- Links to Jira/PR/Slack threads

### For Historical Tracking
- Daily compliance snapshot saved to `data/sla-tracking/daily-snapshots/YYYY-MM-DD.json`
- Violation history for trending
- Team and individual metrics

## Success Metrics

### Target Compliance Rates:
- **Overall SLA Compliance:** ≥ 90%
- **Jira Comment Response:** ≥ 95%
- **PR Review Turnaround:** ≥ 85%
- **Blocked Ticket Resolution:** ≥ 90%
- **Communication Timeliness:** ≥ 95%

### Team Health Indicators:
- Decreasing violation count week-over-week
- Average response time trending down
- Blocked ticket duration trending down
- Escalation rate < 5% of total items

## Continuous Improvement

### Monthly SLA Review:
- Analyze violation patterns
- Identify systemic bottlenecks
- Adjust thresholds if needed (with team agreement)
- Update escalation procedures
- Recognize teams/individuals with excellent compliance

### Quarterly Process Updates:
- Review SLA definitions for relevance
- Update based on team growth/changes
- Incorporate lessons learned
- Align with any SDLC updates

---

**Document Owner:** Project Management
**Last Updated:** 2025-10-19
**Next Review:** Monthly (3rd week of each month)
**Related Documents:**
- [SDLC](https://citemed.atlassian.net/wiki/spaces/Engineerin/pages/31031298/SDLC)
- [Pull Request Workflow Policy](https://citemed.atlassian.net/wiki/spaces/Engineerin/pages/87031809/Pull+Request+Workflow+Policy)
- [SLA Follow-Up Actions](../procedures/sla-follow-up-actions.md)
