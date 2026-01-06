# CiteMed PM Bot - Future Enhancements & Ideas

## 🚀 Scheduled Jobs & Automation

### 1. Daily SLA Monitoring Jobs

**Description**: Create recurring jobs (similar to `/standup`) that automatically monitor and enforce SLAs across all platforms.

**Implementation Ideas**:
- **Schedule**: Run via cron job or systemd timer (daily at 9 AM)
- **Command**: `python run_agent.py "sla-check"` (already exists in architecture)
- **What to Monitor**:
  - ❌ **Jira Comment Response Times**
    - Find comments from stakeholders/PMs with no developer response after 2 business days
    - Post escalation reminders in Slack + Jira comment
  - ❌ **PR Review Turnaround**
    - Find PRs marked "Ready for Review" with no review after 24-48 hours
    - Escalate to reviewers via Slack + PR comment
  - ❌ **Blocked Ticket Updates**
    - Find tickets in "Blocked" status with no update for 2+ days
    - Require daily updates or escalate
  - ❌ **PR Staleness (Code Updates)**
    - Find PRs "In Progress" with no commits for 2+ business days
    - Remind developers to push updates or mark as blocked
  - ❌ **Pending Approval Duration**
    - Find tickets in "Pending Approval" for 48+ hours
    - Escalate to approver

**Technical Approach**:
```bash
# Crontab entry example
0 9 * * 1-5 cd /path/to/project-manager && python run_agent.py "sla-check" >> /var/log/pm-bot-sla.log 2>&1
```

**Files to Create**:
- `.claude/workflows/sla-monitoring.md` (already exists, needs implementation)
- `scripts/daily_sla_check.py` - Standalone script that can be cron-scheduled
- Integration with bot_service.py for real-time monitoring

**SLA Escalation Levels** (already documented):
- Level 1: Soft reminder (just notification)
- Level 2: Jira + Slack notification
- Level 3: Team escalation (tag tech lead)
- Level 4: Leadership escalation (tag manager)

---

### 2. Weekly Developer Summary Job

**Description**: Automatically aggregate individual developer daily updates from #citemed-development and post weekly summaries to #weekly-standup channel.

**Requirements**:
- **Source Channel**: `C02NW7QN1RN` (#citemed-development) - already configured
- **Target Channel**: TBD - need channel ID for #weekly-standup
- **Schedule**: Run every Friday at 5 PM or Monday at 9 AM
- **Time Range**: Current calendar week (Monday-Friday)

**What to Extract**:
- Individual developer daily update messages
- Pattern match typical standup format:
  - "Yesterday: ..."
  - "Today: ..."
  - "Blockers: ..."
  - Or freeform daily updates from specific developers

**Output Format** (example):
```
📊 Weekly Summary - Week of Jan 15-19, 2025

**Mohamed:**
Monday: Worked on ECD-789 authentication refactor, fixed 3 bugs
Tuesday: Completed PR #85 review, started ECD-791
Wednesday: Deployed hotfix for production issue
Thursday: Code review for Ahmed, refactored auth middleware
Friday: Sprint planning, ECD-791 70% complete

**Ahmed:**
Monday: Started ECD-788 database migration
...

**Thanh:**
...

[Full details in thread]
```

**Implementation Ideas**:

1. **Slack Message Aggregation**:
```python
# Pseudo-code
def aggregate_weekly_updates():
    # Get current week Monday-Friday timestamps
    week_start = get_monday_timestamp()
    week_end = get_friday_timestamp()

    # Fetch all messages from #citemed-development
    messages = slack_api.conversations_history(
        channel="C02NW7QN1RN",
        oldest=week_start,
        latest=week_end
    )

    # Group by developer
    developer_updates = {}
    for msg in messages:
        user = msg['user']
        # Pattern match daily update format
        if is_daily_update(msg['text']):
            developer_updates[user].append(parse_update(msg))

    # Format weekly summary
    summary = format_weekly_summary(developer_updates)

    # Post to #weekly-standup
    slack_api.post_message(
        channel="WEEKLY_STANDUP_CHANNEL_ID",  # Need to get this
        text=summary
    )
```

2. **Developer Detection**:
   - Hardcode known developer user IDs (from .env: `DEVELOPER_*` variables)
   - Or auto-detect based on message patterns
   - Track per-developer contributions

3. **Update Pattern Recognition**:
   - Regex patterns for typical standup formats
   - Date detection ("Today", "Yesterday", day of week)
   - Bullet points or numbered lists
   - Task/ticket references (ECD-XXX)

**Files to Create**:
- `bots/weekly_summary.py` - Aggregation logic
- `scripts/generate_weekly_summary.py` - Standalone cron job
- `.claude/workflows/weekly-summary.md` - Workflow documentation

**Cron Schedule**:
```bash
# Every Friday at 5 PM
0 17 * * 5 cd /path/to/project-manager && python scripts/generate_weekly_summary.py

# Or Monday at 9 AM (for previous week)
0 9 * * 1 cd /path/to/project-manager && python scripts/generate_weekly_summary.py --previous-week
```

---

### 3. Thread/Comment Context Loading

**Description**: When the bot is tagged in Slack, Jira, or Bitbucket, automatically fetch and include the full thread/conversation context in the prompt sent to Claude.

**Current Limitation**: Bot only sees the single message where it's tagged, missing critical context from earlier messages in the conversation.

**Proposed Enhancement**: Load entire thread history and pass to Claude for context-aware responses.

**Implementation by Platform**:

#### Slack Thread Context
```python
def get_slack_thread_context(channel: str, thread_ts: str) -> str:
    """Fetch all messages in a Slack thread"""
    headers = {"Authorization": f"Bearer {self.slack_token}"}

    response = requests.get(
        "https://slack.com/api/conversations.replies",
        headers=headers,
        params={"channel": channel, "ts": thread_ts}
    )

    messages = response.json().get("messages", [])

    # Format thread for Claude
    context = "THREAD CONTEXT:\n"
    for msg in messages:
        user = msg.get("user", "unknown")
        timestamp = datetime.fromtimestamp(float(msg["ts"])).strftime("%Y-%m-%d %H:%M:%S")
        text = msg.get("text", "")
        context += f"\n[{timestamp}] @{user}: {text}\n"

    return context
```

**Enhanced Prompt Format**:
```python
prompt = f"""You are the CiteMed AI assistant responding to a Slack message.

{get_slack_thread_context(channel, thread_ts)}

CURRENT MESSAGE (where you were tagged):
- User: {user}
- Message: {text}
- Time: {timestamp}

[Rest of prompt with instructions...]
"""
```

#### Jira Issue Context
```python
def get_jira_issue_context(issue_key: str) -> str:
    """Fetch issue details and all comments"""
    headers = {"Authorization": f"Bearer {self.api_token}"}

    # Get issue details
    issue_response = requests.get(
        f"{self.base_url}/rest/api/3/issue/{issue_key}",
        headers=headers
    )

    issue = issue_response.json()

    context = f"""JIRA ISSUE CONTEXT:
Issue: {issue_key}
Title: {issue['fields']['summary']}
Status: {issue['fields']['status']['name']}
Description:
{issue['fields']['description']}

COMMENT HISTORY:
"""

    # Get all comments
    for comment in issue['fields']['comment']['comments']:
        author = comment['author']['displayName']
        created = comment['created']
        body = comment['body']
        context += f"\n[{created}] {author}:\n{body}\n"

    return context
```

#### Bitbucket PR Context
```python
def get_pr_context(repo: str, pr_id: int) -> str:
    """Fetch PR details, description, and all comments"""

    # Get PR details
    pr = self.api.get_pr(repo, pr_id)

    context = f"""BITBUCKET PR CONTEXT:
PR #{pr_id}: {pr['title']}
Author: {pr['author']['display_name']}
Status: {pr['state']}
Description:
{pr['description']}

COMMENT HISTORY:
"""

    # Get all PR comments
    comments = self.api.get_pr_comments(repo, pr_id)
    for comment in comments:
        author = comment['user']['display_name']
        created = comment['created_on']
        text = comment['content']['raw']
        context += f"\n[{created}] {author}:\n{text}\n"

    # Also include inline code comments
    inline_comments = self.api.get_pr_inline_comments(repo, pr_id)
    if inline_comments:
        context += "\n\nINLINE CODE COMMENTS:\n"
        for comment in inline_comments:
            file_path = comment['inline']['path']
            line = comment['inline'].get('to', 'N/A')
            author = comment['user']['display_name']
            text = comment['content']['raw']
            context += f"\n[{file_path}:{line}] {author}:\n{text}\n"

    return context
```

**Files to Modify**:
- `bots/slack_monitor.py` - Add `get_thread_context()` method
- `bots/jira_monitor.py` - Add `get_issue_context()` method
- `bots/bitbucket_monitor.py` - Add `get_pr_context()` method
- `bots/confluence_monitor.py` - Add `get_page_context()` method (when enabled)

**Benefits**:
- Claude can reference earlier messages in the conversation
- Better understanding of ongoing discussions
- More relevant and contextual responses
- Can track conversation flow and decision history
- Reduces need for users to repeat context

**Implementation Notes**:
- Cache thread context to avoid redundant API calls
- Set reasonable limits (e.g., last 50 messages in thread)
- Include timestamps for temporal context
- Format code snippets properly for Claude to read
- Handle very long threads with truncation + summary

**Priority**: HIGH - Directly improves core bot response quality

---

## 🔮 Additional Future Ideas

### 4. Sprint Rolling Procedure

**Description**: Automated end-of-sprint cleanup that rolls incomplete work to the next sprint, ensuring continuity and accurate sprint tracking.

**Problem Statement**: At sprint end, incomplete tickets need to be moved to the next sprint with updated fix versions. This is currently a manual, error-prone process.

**Workflow**:
1. Get all tickets assigned to current sprint
2. Filter for tickets NOT in final statuses:
   - Exclude: "Pending Approval", "Done", "Closed"
   - Include: "To Do", "In Progress", "In Review", "Blocked"
3. Move filtered tickets to next sprint
4. Update fix version to match next sprint name (fix version = sprint name)
5. Generate summary report of rolled tickets

**Implementation**:

```python
def roll_sprint(current_sprint_name: str, next_sprint_name: str, dry_run: bool = True):
    """
    Roll incomplete tickets from current sprint to next sprint
    """
    # JQL to find incomplete tickets in current sprint
    jql = f"""
        sprint = "{current_sprint_name}"
        AND status NOT IN ("Pending Approval", "Done", "Closed")
        ORDER BY priority DESC, updated DESC
    """

    # Search for tickets
    tickets = jira_api.search_issues_using_jql(jql=jql)

    rolled_tickets = []
    errors = []

    for ticket in tickets:
        try:
            issue_key = ticket['key']
            summary = ticket['fields']['summary']
            status = ticket['fields']['status']['name']
            assignee = ticket['fields'].get('assignee', {}).get('displayName', 'Unassigned')

            if not dry_run:
                # Update sprint field
                jira_api.edit_jira_issue(
                    issue_key=issue_key,
                    fields={
                        'sprint': next_sprint_name,  # Move to next sprint
                        'fixVersions': [{'name': next_sprint_name}]  # Update fix version
                    }
                )

            rolled_tickets.append({
                'key': issue_key,
                'summary': summary,
                'status': status,
                'assignee': assignee
            })

        except Exception as e:
            errors.append({'key': issue_key, 'error': str(e)})

    # Generate summary report
    report = generate_sprint_rollover_report(
        current_sprint=current_sprint_name,
        next_sprint=next_sprint_name,
        rolled_tickets=rolled_tickets,
        errors=errors,
        dry_run=dry_run
    )

    return report


def generate_sprint_rollover_report(current_sprint, next_sprint, rolled_tickets, errors, dry_run):
    """Generate human-readable rollover report"""

    mode = "DRY RUN" if dry_run else "EXECUTED"

    report = f"""
🔄 **Sprint Rollover Report** [{mode}]

**From Sprint**: {current_sprint}
**To Sprint**: {next_sprint}
**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

📊 **Summary**:
- Total tickets rolled: {len(rolled_tickets)}
- Errors: {len(errors)}

---

📋 **Rolled Tickets** ({len(rolled_tickets)}):
"""

    # Group by status
    by_status = {}
    for ticket in rolled_tickets:
        status = ticket['status']
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(ticket)

    for status, tickets in sorted(by_status.items()):
        report += f"\n**{status}** ({len(tickets)}):\n"
        for ticket in tickets:
            report += f"- [{ticket['key']}] {ticket['summary']} (Assignee: {ticket['assignee']})\n"

    if errors:
        report += f"\n\n❌ **Errors** ({len(errors)}):\n"
        for error in errors:
            report += f"- [{error['key']}]: {error['error']}\n"

    report += f"""

---

💡 **Recommendations**:
"""

    # Analyze rolled tickets
    blocked_count = len([t for t in rolled_tickets if 'blocked' in t['status'].lower()])
    in_progress_count = len([t for t in rolled_tickets if t['status'] == 'In Progress'])

    if blocked_count > 0:
        report += f"\n- ⚠️ {blocked_count} blocked tickets rolled - resolve blockers ASAP"

    if in_progress_count > 3:
        report += f"\n- ⚠️ {in_progress_count} in-progress tickets rolled - sprint may have been overcommitted"

    unassigned = len([t for t in rolled_tickets if t['assignee'] == 'Unassigned'])
    if unassigned > 0:
        report += f"\n- 📌 {unassigned} unassigned tickets - assign during sprint planning"

    report += f"\n- ✅ Review rolled tickets in sprint planning for re-estimation"

    return report
```

**Usage**:

```bash
# Dry run (preview only, no changes)
python run_agent.py "sprint-rollover --current 'Sprint 42' --next 'Sprint 43' --dry-run"

# Execute rollover
python run_agent.py "sprint-rollover --current 'Sprint 42' --next 'Sprint 43'"
```

**Slack/Jira Integration**:
- Post rollover report to #citemed-development
- Comment on each rolled ticket explaining the rollover
- Tag assignees for visibility

**Automation Options**:
- **Manual Trigger**: Run as command at sprint end
- **Semi-Automated**: Remind PM to run rollover on last day of sprint
- **Fully Automated**: Run automatically on sprint end date (requires sprint calendar integration)

**Safety Features**:
- Always default to dry-run mode
- Require confirmation for bulk updates
- Log all changes for audit trail
- Rollback mechanism if needed

**Files to Create**:
- `scripts/sprint_rollover.py` - Standalone rollover script
- `.claude/workflows/sprint-rollover.md` - Detailed workflow documentation
- `.claude/templates/sprint-rollover-report.md` - Report template

**Configuration Needed**:
- [ ] Sprint naming convention validation
- [ ] Confirmation that fix version always equals sprint name
- [ ] Define "incomplete" status list (currently: To Do, In Progress, In Review, Blocked)
- [ ] Escalation if > X tickets rolled (indicates sprint health issue)

**Priority**: MEDIUM - Important sprint management task, but not daily/continuous

---

### 5. Automated Sprint Health Reports

**Description**: Daily or twice-weekly automated sprint health check that analyzes:
- Burndown chart trajectory
- Ticket velocity
- At-risk tickets (not started, blocked, etc.)
- Workload distribution across team

**Output**: Slack message to #citemed-development with:
- Sprint completion percentage
- Tickets at risk
- Recommendations (e.g., "Need to address 3 blocked tickets")

---

### 6. Code Complexity vs. Time Logged Audit

**Description**: Automated audit comparing:
- Actual code complexity (LOC, cyclomatic complexity)
- Time logged in timesheets
- Jira ticket estimates vs. actuals

**Use Case**: Flag potential productivity gaps or exceptional work for recognition

**Output**: Weekly report identifying:
- Under-logged work (simple tasks taking too long)
- Over-delivering developers (complex work completed quickly)
- Timesheet accuracy trends

---

### 7. Proactive PR Review Assignment

**Description**: When PRs are created, automatically:
- Analyze code changes (files, complexity)
- Suggest optimal reviewers based on:
  - File ownership history
  - Expertise in changed components
  - Current review workload
- Auto-assign reviewers via Bitbucket API

---

### 8. Automated Test Coverage Enforcement

**Description**: Monitor PRs for test coverage requirements:
- Fail PRs below 80% coverage threshold
- Post coverage report as PR comment
- Track coverage trends over time

---

### 9. Sprint Retrospective Automation

**Description**: At sprint end, automatically:
- Gather all sprint tickets (completed, incomplete, blocked)
- Analyze velocity and completion rate
- Identify common blockers
- Generate retrospective discussion points
- Post to Confluence + Slack

---

### 10. Developer Performance Dashboard

**Description**: Real-time dashboard showing:
- Tickets completed this sprint
- PRs merged
- Code review participation
- SLA compliance rate
- Timesheet submission status

**Tech**: Could be Grafana + custom metrics, or Confluence page auto-updated

---

### 11. Intelligent Blocker Detection

**Description**: Use Claude AI to:
- Monitor Slack/Jira for implicit blockers (developers mentioning issues)
- Automatically create blocker tickets
- Suggest solutions based on historical similar issues
- Connect developers with blockers to those who've solved similar issues

---

### 12. Automated Meeting Notes & Action Items

**Description**: Post-meeting workflow:
- Developers post meeting notes to Slack
- Bot extracts action items
- Creates Jira tickets for action items
- Assigns to mentioned developers
- Tracks completion

---

## 📋 Implementation Priority

### High Priority (Next Sprint)
1. ✅ **Daily SLA Monitoring Jobs** - Core PM agent functionality *(COMPLETED)*
2. ✅ **Weekly Developer Summary Job** - High value, low complexity
3. ✅ **Thread/Comment Context Loading** - Dramatically improves bot response quality
4. 🤖 **Automated PR Review System** - Track PRs, detect new commits, perform AI code reviews

### Medium Priority (Next Quarter)
4. Sprint Rolling Procedure
5. Sprint Health Reports
6. Proactive PR Review Assignment
7. Code Complexity Audits

### Low Priority (Future)
8. Test Coverage Enforcement
9. Sprint Retrospective Automation
10. Developer Dashboard
11. Intelligent Blocker Detection
12. Meeting Notes Automation

---

## 📝 Configuration Needed

### For Weekly Summary Job:
- [ ] Get #weekly-standup channel ID
  ```bash
  # Run in Slack workspace:
  /invite @Remington (CiteMed AI Manager) #weekly-standup
  # Then check channel info to get ID
  ```
- [ ] Add to `.env`:
  ```bash
  SLACK_CHANNEL_WEEKLY_STANDUP=C0XXXXXXXXX
  ```

### For SLA Monitoring:
- [ ] Define exact business hours in `.env` (already exists):
  ```bash
  BUSINESS_HOURS_START=9
  BUSINESS_HOURS_END=17
  BUSINESS_TIMEZONE=America/New_York
  ```
- [ ] Define company holidays (already exists):
  ```bash
  COMPANY_HOLIDAYS=2025-01-01,2025-05-26,2025-07-04...
  ```

### For Developer Tracking:
- [ ] Get developer Jira account IDs and Slack user IDs
- [ ] Map them in `.env`:
  ```bash
  DEVELOPER_MOHAMED_JIRA=accountid:...
  DEVELOPER_MOHAMED_SLACK=U...
  DEVELOPER_AHMED_JIRA=accountid:...
  DEVELOPER_AHMED_SLACK=U...
  # etc.
  ```

---

## 🔧 Technical Implementation Notes

### Job Scheduler Options:

**Option 1: Cron Jobs** (simplest)
```bash
# /etc/cron.d/citemed-pm-bot
0 9 * * 1-5 botuser python /path/to/project-manager/scripts/daily_sla_check.py
0 17 * * 5 botuser python /path/to/project-manager/scripts/weekly_summary.py
```

**Option 2: Systemd Timers** (more robust)
```ini
# /etc/systemd/system/pm-bot-sla.timer
[Unit]
Description=PM Bot Daily SLA Check

[Timer]
OnCalendar=Mon-Fri 9:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Option 3: Python Scheduler** (APScheduler in bot_service.py)
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(run_sla_check, 'cron', hour=9, day_of_week='mon-fri')
scheduler.add_job(run_weekly_summary, 'cron', hour=17, day_of_week='fri')
scheduler.start()
```

**Recommendation**: Start with cron jobs (simple), migrate to systemd timers for production.

---

## 💡 Additional Considerations

### Notifications:
- Should summaries @mention developers?
- Should SLA violations be public or DM?
- Escalation paths for each SLA type

### Data Storage:
- Store historical SLA compliance data (SQLite or PostgreSQL)
- Track trends over time
- Generate monthly compliance reports

### Testing:
- Dry-run mode for all jobs
- Test data generators
- Rollback/undo mechanisms for incorrect escalations

### Monitoring:
- Job success/failure logging
- Alert on job failures
- Metrics (jobs run, SLA violations found, escalations sent)

---

## 📅 Next Steps

1. **Tomorrow**: Review this document and prioritize
2. **Get missing config**: #weekly-standup channel ID
3. **Design**: Create detailed workflow docs in `.claude/workflows/`
4. **Implement**: Start with whichever job provides most immediate value
5. **Test**: Dry-run mode with real data
6. **Deploy**: Schedule as cron job
7. **Monitor**: Verify effectiveness and iterate

---

**Last Updated**: 2025-10-20
**Status**: Planning / Ideas Phase
**Owner**: PM Agent Development
