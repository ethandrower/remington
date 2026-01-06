# Standup & SLA Automation - Current Status

**Date:** 2025-10-29
**Priority:** CRITICAL
**Status:** IMPLEMENTATION IN PROGRESS

---

## ✅ COMPLETED

### 1. Standup Workflow Architecture
- **Created:** `scripts/standup_workflow.py` - Complete 5-part standup orchestrator
- **Wired:** `run_agent.py` now calls the working script
- **Command:** `python run_agent.py standup` is now functional

### 2. Run Agent Cleanup
- **Removed:** OAuth environment checks (using MCP connections)
- **Fixed:** Sprint analysis command
- **Working:** SLA check command already functional

### 3. Documentation
- **Agent Definitions:** All 5 subagents documented in `.claude/agents/`
- **Workflows:** Complete workflow docs in `.claude/workflows/`
- **Implementation Plan:** Comprehensive SLA enhancement guide created

---

## ⚠️ CRITICAL GAPS - IMMEDIATE ACTION NEEDED

### **Gap #1: Standup Needs MCP Execution**

**Current State:**
- `standup_workflow.py` detects what needs to be done
- Sections 1-4 require **Claude with MCP** to execute
- Only Section 5 (SLA) is fully automated

**Why:**
- Sections 1-4 need real-time Jira queries via MCP
- Script can't execute MCP tools directly (needs Claude)
- This is **BY DESIGN** - Claude should run the standup, not Python alone

**Solution:**
The standup workflow should be invoked **BY CLAUDE** so it can:
1. Read the standup_workflow.py requirements
2. Execute MCP queries for each section
3. Analyze results using AI
4. Generate comprehensive report

**How to Run:**
```bash
# Option A: Have Claude run it
# In Claude Code chat: "Run the daily standup workflow"

# Option B: Run manually (partial - only SLA section works)
python run_agent.py standup --dry-run
```

### **Gap #2: SLA Monitoring is Passive, Not Proactive**

**Current State:**
- `sla_check_working.py` DETECTS violations ✅
- Outputs to console/Slack summary ✅
- But does NOT:
  - Post Jira comments with @developer tags ❌
  - Create Slack threads for tracking ❌
  - Execute 4-level escalation matrix ❌
  - Persist violations across runs ❌

**Impact:**
- Developers aren't notified directly on their tickets
- No escalation for chronic violations
- No historical tracking of compliance
- **Bot isn't "driving the SLAs" - just reporting them**

**Solution Documented:**
See `.claude/SLA_PROACTIVE_IMPLEMENTATION.md` for complete implementation plan

**Critical Features Needed:**
1. **Jira Comment Posting** with developer tagging (Level 1+)
2. **Slack Thread Creation** for critical violations (Level 2+)
3. **Escalation Matrix** execution (Levels 1-4)
4. **Historical Tracking** (persist violations in JSON)

---

## 🚀 NEXT STEPS (Priority Order)

### Step 1: Get Developer Jira Account IDs ⚡ CRITICAL
**Why:** Required to tag developers in Jira comments
**How:** Use MCP to lookup each developer:

```python
# For each developer:
mcp__atlassian__lookupJiraAccountId(
    cloudId="67bbfd03-b309-414f-9640-908213f80628",
    searchString="Mohamed Belkahla"
)
# Add to .env:
# DEVELOPER_MOHAMED_JIRA=accountid:712020:27a3f2fe-9037-455d-9392-fb80ba1705c0
```

**Needed for:** Mohamed, Ahmed, Thanh, Valentin, Josh

### Step 2: Enhance SLA Check to Post Jira Comments ⚡ CRITICAL
**Task:** Modify `scripts/sla_check_working.py` to:
- Post Jira comment when violation detected
- Tag developer using their account ID
- Follow escalation templates from sla-monitor.md

**Implementation:** See `.claude/SLA_PROACTIVE_IMPLEMENTATION.md` Section 1

### Step 3: Add Slack Thread Creation for Level 2+ Escalations
**Task:** Create dedicated Slack threads for critical violations
- Level 2: Create thread + link to Jira
- Level 3: Update thread + tag tech lead
- Level 4: Escalate to leadership

**Implementation:** See `.claude/SLA_PROACTIVE_IMPLEMENTATION.md` Section 2

### Step 4: Implement Historical Violation Tracking
**Task:** Persist violations to `.claude/data/sla-tracking/active-violations.json`
- Track escalation level over time
- Only escalate when needed (don't duplicate)
- Mark violations resolved when fixed

**Implementation:** See `.claude/SLA_PROACTIVE_IMPLEMENTATION.md` Section 4

### Step 5: Set Up Automated Scheduling
**Options:**

**Option A: Cron (Simplest)**
```bash
# Daily standup at 9am (needs Claude running as service)
0 9 * * 1-5 cd /path/to/project-manager && python run_agent.py standup

# Hourly SLA checks
0 * * * * cd /path/to/project-manager && python run_agent.py sla-check
```

**Option B: Heroku Scheduler (Recommended)**
```yaml
# Procfile
clock: python clock.py

# clock.py
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(run_sla_check, 'cron', hour='9-17', day_of_week='mon-fri')
scheduler.add_job(run_standup, 'cron', hour=9, day_of_week='mon-fri')
scheduler.start()
```

**Option C: GitHub Actions (Free)**
```yaml
# .github/workflows/daily-standup.yml
on:
  schedule:
    - cron: '0 14 * * 1-5'  # 9am ET = 2pm UTC
jobs:
  standup:
    runs-on: ubuntu-latest
    steps:
      - run: python run_agent.py standup
```

### Step 6: Test End-to-End
1. Manually trigger standup via Claude
2. Verify SLA violations are detected
3. Verify Jira comments are posted
4. Verify Slack threads are created
5. Verify violations persist across runs
6. Test full escalation matrix (Levels 1-4)

---

## 📊 WHAT WORKS RIGHT NOW

### Commands Available
```bash
# Run daily standup (partial - needs Claude for full execution)
python run_agent.py standup

# Run SLA check (fully working, but passive)
python run_agent.py sla-check

# Run sprint analysis (partial)
python run_agent.py sprint-analysis
```

### SLA Detection (Working)
- ✅ Detects stale PRs (no commits in 2+ days)
- ✅ Calculates business hours
- ✅ Categorizes by severity (warning/critical)
- ✅ Posts summary to Slack
- ❌ Does NOT post to Jira tickets
- ❌ Does NOT create Slack threads
- ❌ Does NOT execute escalations

### Bot Integration (Working)
- ✅ 4-platform monitoring (Slack, Jira, Bitbucket, Confluence)
- ✅ Event classification and routing
- ✅ Responds to @mentions
- ⚠️ Not yet integrated with standup workflow

---

## 🎯 GOAL STATE

### Daily Standup (Automated)
**When:** Every weekday at 9am ET
**What:**
1. Sprint progress analysis (real-time Jira data)
2. Code-ticket gap detection (git + Jira)
3. Developer productivity audit
4. Team timesheet analysis
5. SLA violations with automatic escalations

**Output:**
- Comprehensive markdown report saved to `.claude/data/standups/`
- Posted to Slack with actionable insights
- All SLA violations automatically escalated

### SLA Enforcement (Continuous)
**When:** Hourly checks during business hours
**What:**
- Detect all SLA violations (Jira, PRs, blockers)
- **Post Jira comments** tagging developers
- **Create Slack threads** for critical items
- **Execute escalation matrix** (4 levels)
- **Track compliance** over time

**Result:**
- Team stays on top of commitments
- No manual PM chasing needed
- Transparent, systematic enforcement
- Data-driven compliance trends

---

## 📁 KEY FILES

### Working Scripts
- `scripts/sla_check_working.py` - SLA detection (needs enhancement)
- `scripts/standup_workflow.py` - Standup orchestrator (needs MCP execution)
- `run_agent.py` - Command entrypoint (working)

### Documentation
- `.claude/CLAUDE.md` - Main agent instructions
- `.claude/agents/` - 5 subagent definitions
- `.claude/workflows/` - Workflow procedures
- `.claude/SLA_PROACTIVE_IMPLEMENTATION.md` - Enhancement roadmap (NEW)

### Data Directories
- `.claude/data/standups/` - Standup reports
- `.claude/data/sla-tracking/` - Violation tracking (needs creation)
- `.claude/data/bot-state/` - Bot monitor databases

---

## 💡 RECOMMENDATION

**IMMEDIATE (Today):**
1. Lookup all developer Jira account IDs via MCP
2. Add to `.env` file
3. Enhance `sla_check_working.py` to post Jira comments

**SHORT-TERM (This Week):**
4. Add Slack thread creation for escalations
5. Implement historical violation tracking
6. Test full escalation matrix

**MEDIUM-TERM (Next Week):**
7. Set up Heroku deployment or cron scheduling
8. Run standup via Claude daily
9. Monitor SLA compliance trends

---

## ❓ QUESTIONS FOR YOU

1. **Scheduling:** Heroku, cron, or GitHub Actions?
2. **Standup:** Should Claude run it daily via automation, or just on-demand?
3. **Escalations:** Tech lead and leadership Slack/Jira IDs?
4. **Notifications:** Where should Level 3/4 escalations go?

---

**Next Action:** I can start implementing the SLA enhancements right now. Should I:
- **Option A:** Lookup developer Jira account IDs via MCP
- **Option B:** Enhance sla_check_working.py to post Jira comments
- **Option C:** Create the scheduling setup (Heroku/cron)
- **Option D:** Test the standup workflow end-to-end with you

Let me know which is most critical!
