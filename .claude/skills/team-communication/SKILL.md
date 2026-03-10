---
name: team-communication
description: Provides knowledge about effective team communication including Slack messaging strategies, escalation protocols, stakeholder updates, remote collaboration, recognition, and meeting facilitation. Use when posting to Slack, escalating issues, sending standup reports, recognizing team members, or communicating with stakeholders.
---

# Team Communication Skill

## Purpose
This skill provides knowledge about effective team communication, including Slack messaging strategies, escalation protocols, stakeholder updates, and remote collaboration best practices.

## Slack Communication Best Practices

### Channel Organization

**Development Channels:**
- `#engineering` - General engineering discussions
- `#sprint-updates` - Daily standup reports, sprint progress
- `#pull-requests` - PR notifications and reviews
- `#deployments` - Deployment notifications
- `#bugs` - Bug reports and hotfixes

**Project Channels:**
- `#project-evidence-cloud` - CiteMed project-specific
- `#word-addon` - Microsoft Word integration work
- Feature-specific channels for large initiatives

**Support Channels:**
- `#devops` - Infrastructure and deployment help
- `#qa` - Testing and quality questions
- `#product` - Product requirements and clarifications

### Message Formatting

**Status Updates:**
```markdown
📊 **Daily Standup Report** - Oct 19, 2025

**Sprint Progress:** 28% complete (14/50 items)
**Blocked Items:** 5 tickets need attention
**SLA Violations:** 3 critical, 5 warnings

Full report: [Thread link]
```

**Blocker Alerts:**
```markdown
🚨 **BLOCKER** - ECD-123

@developer This ticket has been blocked for 3 days. Can you provide status update?

**Impact:** Sprint timeline at risk
**Jira:** [link]
**Required:** API endpoint from backend team
```

**PR Review Requests:**
```markdown
📝 **PR Ready for Review** - ECD-456

@reviewer Can you review this PR when you have a moment?

**Changes:** Word add-in authentication flow
**PR:** [link]
**Jira:** [link]
**Complexity:** Medium (200 lines, 3 files)
```

**Recognition:**
```markdown
✨ **Excellent Work!**

Shoutout to @developer for exceptional productivity this week:
- 3 complex features delivered
- High code quality (0 review iterations)
- Helped unblock 2 teammates

Keep up the great work! 🎉
```

### Threading Best Practices

**When to Use Threads:**
- ✅ Detailed discussions on specific topic
- ✅ Escalations requiring back-and-forth
- ✅ Follow-up on automated alerts
- ✅ Technical troubleshooting

**When NOT to Use Threads:**
- ❌ Urgent announcements (use channel)
- ❌ Simple questions with quick answers
- ❌ Information many people need to see

**Thread Etiquette:**
- Summarize resolution in thread
- Tag people when you need their input
- Keep threads focused on one topic
- Close loops (confirm resolution)

### @Mention Etiquette

**When to @mention:**
- Direct question requiring their response
- Blocking their work or need their help
- They specifically requested updates
- Escalating issue to them

**When NOT to @mention:**
- FYI information
- General team updates
- Questions for "anyone"
- Tagging everyone repeatedly

**Format:**
- One person: `@jane can you review this?`
- Multiple specific people: `@jane @john Can one of you help?`
- Role-based: `@channel` (use sparingly!) or `@here` (only online members)

## Escalation Communication

### Escalation Levels

**Level 1: Soft Reminder**
- Channel: Jira comment only
- Tone: Friendly, helpful
- Timing: 0-1 days overdue
- Example:
  > "Hi @dev, just a gentle reminder that ECD-123 has been waiting for 1 day. Can you provide a quick update when you have a moment? Thanks!"

**Level 2: Jira + Slack Thread**
- Channel: Jira comment + Slack DM or thread
- Tone: Professional, firmer
- Timing: 1-2 days overdue
- Example (Slack):
  > "Hi @dev, ECD-123 is now 2 days overdue (SLA: 2 business days). Could you please prioritize this or let me know if there are blockers? I've also commented in Jira for visibility."

**Level 3: Team Escalation**
- Channel: Jira + Slack thread + Team channel mention
- Tone: Urgent but professional
- Timing: 2-3 days overdue
- Example (Slack #engineering):
  > "🚨 Escalation: ECD-123 requires immediate attention (3 days overdue).
  > @dev, can you provide status update?
  > @tech-lead, please advise if re-prioritization is needed.
  > This may impact sprint goals. Thread: [link]"

**Level 4: Leadership Notification**
- Channel: All of above + Leadership Slack/email
- Tone: Formal, escalation to executive level
- Timing: 3+ days overdue
- Example (Slack to leadership):
  > "⚠️ CRITICAL ESCALATION
  >
  > ECD-123 has exceeded SLA threshold (4 days overdue).
  > Sprint goals are at risk.
  >
  > **Item:** [Summary]
  > **Assigned:** @developer
  > **Tech Lead:** @tech-lead
  > **Impact:** Blocking epic ECD-77 progress, affects 3 downstream tickets
  >
  > Immediate action required.
  > Jira: [link] | Thread: [link]"

### Escalation Templates

**Blocked Ticket Escalation:**
```markdown
🚫 **Blocked Ticket Requires Attention**

**Ticket:** ECD-123 - [Summary]
**Blocked Duration:** X days
**Blocker:** [Description]
**Assigned:** @developer
**Impact:** [Sprint/Epic impact]

**Action Needed:**
- [ ] @developer: Provide status update
- [ ] @blocker-owner: Resolve dependency
- [ ] @tech-lead: Re-prioritize if needed

**Jira:** [link]
**SLA Status:** Violation (daily updates required for blocked items)
```

**Stale PR Escalation:**
```markdown
⏰ **PR Review Overdue**

**PR:** #123 - [Title]
**Author:** @developer
**Requested:** X days ago
**SLA:** 24-48 hours

**Reviewers:** @reviewer1, @reviewer2
Can one of you review this PR today? It's blocking ECD-456.

**PR Link:** [link]
**Jira:** [link]
```

**Code-Ticket Gap Alert:**
```markdown
⚠️ **Potential Stalled Work Detected**

**Ticket:** ECD-123 - [Summary]
**Status:** In Progress
**Last Git Activity:** X days ago
**Assigned:** @developer

@developer, can you provide a status update? If you're blocked or need help, please let us know!

**Jira:** [link]
```

## Daily Standup Communication

### Automated Standup Report (Posted to Slack)

```markdown
🏃‍♂️ **DAILY STANDUP REPORT** - Oct 19, 2025
═══════════════════════════════════

📊 **SPRINT PROGRESS**
- Current Sprint: Sprint 5
- Items Complete: 14/50 (28%)
- Epic Progress: ECD-77 (Word Add-in) - 40% complete
- Sprint Risk: 🟡 MEDIUM - 5 blocked items

🚨 **CODE-TICKET GAPS** (3)
- ECD-410: @mohamed - In Progress for 3 days, no git activity
- ECD-398: @thanh - In Progress for 2 days, no commits
- ECD-487: @valentin - In Progress for 5 days, branch exists but stale

ACTION: Please update ticket status or report blockers

📊 **SLA VIOLATIONS** (8 total)

⚠️ **CRITICAL** (3):
- ECD-516: @ahmed - Comment response 3 days overdue → Escalation Level 3
- PR #234: @mohamed - Review overdue 2 days → Created reviewer thread
- ECD-504: BLOCKED for 3 days without update → Escalation to tech lead

⏰ **WARNINGS** (5):
- ECD-398: Approaching 2-day comment SLA (6h remaining)
- PR #235: Approaching review SLA (4h remaining)
- [3 more...]

✅ **RECENTLY RESOLVED** (2):
- ECD-450: Unblocked after escalation yesterday
- PR #230: Review completed after follow-up

📈 **TEAM PRODUCTIVITY** (Last 7 Days)
- Total Hours: 280h
- Avg Daily Hours: 8h/developer
- Most Active: @thanh (45h)
- Tickets Active: 12 unique tickets

💡 **ACTION ITEMS**
- [ ] @tech-lead: Unblock 5 tickets (priority: ECD-516, ECD-487)
- [ ] @mohamed: Update git activity on ECD-410 or adjust status
- [ ] @reviewer-team: Prioritize PR #234 review (3 days overdue)
- [ ] @team: Review SLA compliance (88%, below 90% target)

Full analysis available in thread 🧵
```

### Thread Follow-Up Structure

**Main Thread Reply (Detail Sections):**
1. Sprint burndown details (epic breakdown)
2. Blocked items with specific actions
3. SLA violation details with escalation history
4. Productivity insights and recognition
5. Historical trends and recommendations

## Stakeholder Communication

### Weekly Stakeholder Update

**Template:**
```markdown
📊 **Weekly Progress Update** - Week of Oct 13-19, 2025

**Sprint Status:**
- Sprint 5: 28% complete, on track for Oct 30 delivery
- Epic ECD-77 (Word Add-in): 40% complete, 2 stories delivered this week

**Key Achievements:**
✅ Word add-in authentication flow complete
✅ Reference search functionality implemented
✅ 8 bugs resolved

**Upcoming Milestones:**
📅 Oct 22: Word add-in beta testing begins
📅 Oct 30: Sprint 5 completion and demo

**Risks & Mitigations:**
⚠️ 5 blocked items - working with backend team to resolve
⚠️ SLA compliance below target - implementing process improvements

**Next Week Focus:**
- Complete word add-in reference insertion
- Address blocked items
- Begin Epic ECD-78 planning

Questions? Let's discuss in standup or async in #project-evidence-cloud
```

### Incident Communication

**Template:**
```markdown
🚨 **INCIDENT NOTIFICATION**

**Severity:** [Critical / High / Medium]
**Status:** [Investigating / Identified / Resolved]
**Impact:** [User-facing description]

**Timeline:**
- 10:30 AM: Issue detected
- 10:35 AM: Team notified, investigation started
- 10:45 AM: Root cause identified
- 11:00 AM: Fix deployed
- 11:15 AM: Verified resolved

**Root Cause:**
[Technical description]

**Resolution:**
[What was done to fix]

**Prevention:**
[Steps to prevent recurrence]

**Jira:** [link to incident ticket]
```

## Remote Team Communication

### Async Communication Best Practices

**Written Updates:**
- Post daily progress in dedicated thread
- Include blockers and next steps
- Link to Jira tickets and PRs
- Be specific about timelines

**Video/Voice Standups:**
- Record for team members in other timezones
- Post summary in Slack after meeting
- Share decisions and action items
- Upload recording to shared drive

**Time Zone Considerations:**
- Use world clock for scheduling
- Rotate meeting times for fairness
- Record all important meetings
- Document decisions asynchronously

### Over-Communication vs. Noise

**When to Over-Communicate:**
- ✅ Blockers affecting others
- ✅ Timeline changes or delays
- ✅ Breaking changes to shared code
- ✅ Important decisions or pivots

**When to Reduce Noise:**
- ❌ Every minor code change
- ❌ Work-in-progress updates
- ❌ Internal refactoring (no external impact)
- ❌ "Thanks" and "+1" messages (use emoji reactions)

## Recognition and Feedback

### Public Recognition

**When to Recognize:**
- Exceptional productivity or quality
- Going above and beyond
- Helping teammates
- Solving difficult technical challenges
- Consistent high performance

**Format:**
```markdown
🌟 **Weekly Highlight**

Huge shoutout to @developer for:
- Delivering 3 complex features ahead of schedule
- Mentoring junior developer on authentication patterns
- Zero bugs introduced (high code quality)
- Helping unblock 2 teammates

This is the kind of teamwork that makes us successful! 🎉
```

### Constructive Feedback

**Private Channels Only:**
- Use DMs for individual feedback
- Be specific and actionable
- Focus on behavior, not person
- Provide examples
- Offer support and resources

**Template (DM):**
```markdown
Hi @developer,

I wanted to chat about [specific behavior/pattern]. I noticed [specific examples].

This is affecting [impact on team/sprint/project].

Can we discuss how to [improvement suggestion]? I'm happy to help with [resources/support].

Let me know if you'd like to chat synchronously or async.
```

## Meeting Communication

### Meeting Preparation

**Before Meeting:**
- Post agenda 24 hours in advance
- Share relevant docs/links
- Tag attendees with prep work
- Set clear objectives

**Agenda Template:**
```markdown
📅 **Sprint Planning Meeting** - Oct 20, 2025, 2:00 PM

**Objectives:**
- Review Sprint 4 outcomes
- Plan Sprint 5 scope
- Identify dependencies

**Agenda:**
1. Sprint 4 review (15 min)
2. Velocity and capacity planning (10 min)
3. Backlog review and prioritization (30 min)
4. Sprint 5 commitment (15 min)
5. Q&A and parking lot (10 min)

**Prep Work:**
- [ ] Review sprint 4 burndown
- [ ] Read epic ECD-77 requirements
- [ ] Estimate assigned stories

**Attendees:** @team @product-manager
**Link:** [meeting link]
```

### Meeting Notes

**Post-Meeting Summary:**
```markdown
📝 **Meeting Notes** - Sprint Planning (Oct 20, 2025)

**Decisions:**
- Sprint 5 will focus on Epic ECD-77 (Word Add-in)
- Committing to 25 story points (avg velocity)
- Reserved 20% capacity for bugs

**Action Items:**
- [ ] @tech-lead: Break down ECD-410 into subtasks (by EOD Oct 21)
- [ ] @product-manager: Clarify acceptance criteria for ECD-398 (by Oct 21)
- [ ] @developer: Investigate OAuth library options (by Oct 22)

**Parking Lot:**
- Epic ECD-78 planning → defer to Sprint 6
- Performance optimization → add to tech debt backlog

**Next Sprint Planning:** Oct 30, 2025
```

## Communication Anti-Patterns

### What to Avoid

❌ **"Let me know if you have questions"** → Instead: "Do you have questions about X or Y specifically?"

❌ **Tagging @channel for non-urgent items** → Use @here or schedule for working hours

❌ **Vague status updates** "Making progress" → Be specific: "Completed auth flow, working on token refresh"

❌ **Passive-aggressive tone** "As I already mentioned..." → Be direct and professional

❌ **Long messages without formatting** → Use headers, bullets, bold for skimability

❌ **Responding with "👍" to important questions** → Provide clear written confirmation

❌ **Discussing controversial topics in public channels** → Take to DMs or private calls

---

**This skill enables the PM agent to communicate effectively with the team through Slack, execute escalations professionally, recognize excellent work, and maintain positive team dynamics.**