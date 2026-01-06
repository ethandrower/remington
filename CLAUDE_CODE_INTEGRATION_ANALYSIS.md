# Claude Code Integration Analysis

## The Problem: We're Throwing Away Valuable Context!

You're absolutely right. The current implementation uses **direct Anthropic API calls** with a generic prompt, completely bypassing the rich business context in `.claude/`.

### What We Have Now (Generic API Call)

**Current Orchestrator** (`src/orchestration/simple_orchestrator.py:187-217`):
```python
prompt = f"""You are a PM agent monitoring a software development project.

CONTEXT:
- Issue: {issue_data.get('key')} - {issue_data.get('summary')}
- Status: {issue_data.get('status')}
- Assignee: {issue_data.get('assignee')}

NEW COMMENT (from {commenter}):
"{comment}"

TASK:
Analyze this comment and decide if the PM agent should respond.
...
```

**Problems:**
- ❌ No SLA knowledge (2 business days, escalation levels, etc.)
- ❌ No team context (who are the developers? their roles?)
- ❌ No project-specific rules (CiteMed workflows, priorities)
- ❌ No access to codebase (can't analyze code complexity)
- ❌ Generic "PM agent" - not specialized (SLA monitor vs Sprint analyzer)

---

## What We're Missing: The Full Claude Code Architecture

### 1. Agent Specialization (`.claude/agents/`)

You defined **5 specialized agents**, each with detailed knowledge:

#### SLA Monitor (`sla-monitor.md`)
```markdown
## SLA Definitions

**Jira Comment Response Time**
- Target: 2 business days maximum
- Applies To: All active tickets in current sprint
- Escalation Levels:
  - Level 1 (1-2 days): Soft reminder in Jira
  - Level 2 (3-4 days): Jira + Slack notification
  - Level 3 (5-6 days): Tag team lead
  - Level 4 (7+ days): Escalate to leadership
...
```

#### Developer Auditor (`developer-auditor.md`)
```markdown
## Audit Methodology

1. Read timesheet entries from `.claude/data/timesheets/`
2. Analyze actual code using Filesystem MCP
3. Cross-reference with Jira tickets
4. Calculate complexity scores
5. Flag discrepancies (logged 8hrs, committed trivial changes)
...
```

#### Jira Manager (`jira-manager.md`)
```markdown
## MCP Tool Usage Examples

### Tagging Developers
# Step 1: Lookup account ID
accountId = mcp__atlassian__lookupJiraAccountId(
    cloudId="67bbfd03-b309-414f-9640-908213f80628",
    displayName="Mohamed"
)

# Step 2: Tag in comment
mcp__atlassian__addCommentToJiraIssue(
    cloudId="...",
    issueIdOrKey="ECD-123",
    body={
        "type": "doc",
        "content": [{
            "type": "paragraph",
            "content": [
                {"type": "mention", "attrs": {"id": accountId}},
                {"type": "text", "text": " - please review"}
            ]
        }]
    }
)
```

**This is DETAILED, ACTIONABLE knowledge that took time to build!**

### 2. Skills Library (`.claude/skills/`)

#### Jira Best Practices (`skills/jira-best-practices/SKILL.md`)
```markdown
---
name: jira-best-practices
description: Provides knowledge about effective Jira usage...
---

## Ticket Formatting Standards

### Summary Format
- ✅ Good: "Add OAuth2 authentication to API endpoints"
- ❌ Bad: "Fix login stuff"

### Description Template
## Problem/Goal
[What needs to be done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Technical Notes
[Implementation details]
...
```

#### SLA Enforcement (`skills/sla-enforcement/SKILL.md`)
```markdown
## Business Hours Calculation
- Business Days: Monday-Friday
- Working Hours: 9am-5pm
- Holidays: [list of company holidays]

## Escalation Decision Tree
1. Check hours since last update
2. Convert to business hours only
3. Apply escalation matrix
4. Consider ticket priority (High = stricter SLA)
...
```

### 3. Team & Project Context (`.claude/CLAUDE.md`)

```markdown
### Team Members
- **Mohamed** - Developer (Jira ID: 712020:27a3f2fe-9037-455d-9392-fb80ba1705c0)
- **Ahmed** - Developer
- **Thanh** - Developer
- **Josh** - Developer

### Technology Stack
- Backend: Django, Python 3.11+
- Frontend: Vue.js, TypeScript
- Repositories: citemed_web (main), word_addon

### Sprint Workflow
- Sprint Length: 2 weeks
- Status flow: To Do → In Progress → Pending Approval → Done
- Branch naming: ECD-XXX-description
```

### 4. MCP Integration

**Atlassian MCP** (`.mcp.json`):
```json
{
  "atlassian": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
  },
  "filesystem": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-filesystem",
      "/Users/ethand320/code/citemed/citemed_web",  // READ codebase!
      "/Users/ethand320/code/citemed/project-manager"
    ]
  }
}
```

**Capabilities:**
- ✅ Query Jira with JQL (complex queries)
- ✅ Post comments with proper user tagging
- ✅ Read citemed_web codebase for complexity analysis
- ✅ Track historical data in `.claude/data/`

---

## The Correct Architecture: Claude Code as the Reasoning Engine

### How It Should Work

```
Webhook/Poll → Event → Invoke Claude Code → MCP Tools → Action
                             ▲
                             │
                    Loads rich context:
                    - Agent persona
                    - Skills knowledge
                    - Team data
                    - SLA rules
```

### Example: SLA Monitor Flow

**Step 1: Detect Event**
```python
# In pm_agent_service.py
events = jira_monitor.poll_for_mentions()

for event in events:
    # Don't call generic orchestrator!
    # Instead: invoke Claude Code with SLA Monitor context
    invoke_claude_code_agent("sla-monitor", event)
```

**Step 2: Invoke Claude Code with Context**
```python
def invoke_claude_code_agent(agent_type, event_data):
    """
    Invoke Claude Code with specialized agent context

    Claude Code will:
    1. Read `.claude/CLAUDE.md` (project context)
    2. Read `.claude/agents/{agent_type}.md` (agent instructions)
    3. Load relevant skills from `.claude/skills/`
    4. Use MCP tools (atlassian, filesystem)
    5. Make intelligent decisions based on ALL this context
    6. Execute actions (post Jira comments, create tickets)
    7. Log to `.claude/data/`
    """

    # Build prompt that references the agent file
    prompt = f"""
    You are acting as the {agent_type} subagent.

    Read your instructions from `.claude/agents/{agent_type}.md`

    Event: {json.dumps(event_data)}

    Follow your documented procedures to:
    1. Analyze the event
    2. Apply SLA rules
    3. Determine escalation level
    4. Execute appropriate actions
    5. Log the decision
    """

    # This would need to be a subprocess call to Claude Code CLI
    # OR use MCP client to call Claude Code's reasoning
    result = subprocess.run([
        "claude-code",
        "--prompt", prompt,
        "--workspace", str(PROJECT_ROOT)
    ], capture_output=True)
```

**Step 3: Claude Code Reasoning (with full context)**
```
I am the SLA Monitor agent. Let me read my instructions...

[Reads .claude/agents/sla-monitor.md]
- I see: Jira comment SLA is 2 business days
- Escalation Level 2 at 3-4 days overdue
- I should tag the developer + post to Slack

[Checks event]
- Issue: ECD-123
- Comment from: Sarah (3 days ago)
- Assignee: Mohamed
- No response yet

[Uses MCP to gather more context]
mcp__atlassian__getJiraIssue("ECD-123")
- Priority: High (stricter SLA applies!)
- Sprint: Current sprint
- Status: In Progress

[Calculates business hours]
3 calendar days - 1 weekend = ~1.5 business days
Still within SLA (under 2 days) ✅

[Decision]
No escalation needed yet. Will recheck tomorrow.

[Logs decision]
Write to .claude/data/sla-tracking/daily-snapshots/2025-11-06.json
```

---

## What We Built vs What We Need

### Current (API-only)
```
Event → SimpleOrchestrator → Claude API (generic prompt) → Response
        ├── No SLA knowledge
        ├── No team context
        ├── No code access
        └── No specialized agents
```

### Needed (Claude Code Integration)
```
Event → Claude Code Agent → [Reads .claude/ context] → MCP Tools → Action
        ├── SLA Monitor (detailed rules)
        ├── Developer Auditor (code analysis)
        ├── Sprint Analyzer (metrics)
        ├── Jira Manager (proper tagging)
        └── Uses MCP (Jira, Filesystem, etc.)
```

---

## Integration Options

### Option 1: Hybrid - Use Claude Code for Complex Workflows

**Keep current setup for simple responses:**
```python
# Simple comment response (fast, low complexity)
if event_type == "comment_created":
    # Use current API-based orchestrator
    result = simple_orchestrator.process_jira_comment(...)
```

**Invoke Claude Code for complex workflows:**
```python
# Complex SLA analysis (needs business context)
if workflow_type == "sla-check":
    # Invoke Claude Code with full context
    result = invoke_claude_code_agent("sla-monitor", event_data)

# Developer productivity audit (needs code access)
if workflow_type == "productivity-audit":
    result = invoke_claude_code_agent("developer-auditor", event_data)
```

### Option 2: Full Migration - Make Claude Code the Primary Engine

**All events go through Claude Code:**
```python
# Webhook received
def process_webhook(payload):
    # Determine agent type
    agent = determine_agent(payload)  # "sla-monitor", "jira-manager", etc.

    # Invoke Claude Code
    result = invoke_claude_code_with_context(
        agent_file=f".claude/agents/{agent}.md",
        event=payload,
        tools=["mcp__atlassian__*", "mcp__filesystem__*"]
    )

    return result
```

### Option 3: MCP Client Integration (Most Sophisticated)

**Use MCP protocol to call Claude Code programmatically:**
```python
from mcp import MCPClient

class ClaudeCodeOrchestrator:
    def __init__(self):
        self.client = MCPClient()
        self.client.connect_to_claude_code()

    async def process_with_agent(self, agent_type, event_data):
        # Load agent context
        agent_md = Path(f".claude/agents/{agent_type}.md").read_text()

        # Build prompt with full context
        prompt = f"""
        {agent_md}

        NEW EVENT:
        {json.dumps(event_data)}

        Follow your documented procedures.
        """

        # Call Claude Code with MCP tools available
        response = await self.client.chat_with_tools(
            prompt=prompt,
            tools=["mcp__atlassian__*", "mcp__filesystem__*"],
            workspace=PROJECT_ROOT
        )

        return response
```

---

## What You Should Do

### Immediate (Before Deployment)

1. **Don't throw away the `.claude/` context!**
   - Keep `.claude/agents/` - Detailed agent instructions
   - Keep `.claude/skills/` - Business knowledge
   - Keep `.claude/CLAUDE.md` - Project context

2. **Test current setup first**
   - Deploy hybrid webhook + polling
   - Validate it works with generic Claude API

3. **Then enhance with Claude Code**
   - Add Claude Code integration for complex workflows
   - Keep simple API for fast responses

### Short-term Enhancement

**Add a "smart mode" for complex decisions:**
```python
class SmartOrchestrator:
    def process_event(self, event):
        # Quick decision: use API
        if self.is_simple_response(event):
            return self.simple_orchestrator.process(event)

        # Complex decision: use Claude Code with full context
        else:
            return self.invoke_claude_code_agent(
                agent=self.determine_agent(event),
                context=event
            )
```

### Long-term (Full Integration)

**Make Claude Code the primary reasoning engine:**
- All events invoke Claude Code
- Claude Code reads `.claude/` for context
- Uses MCP tools for actions
- Your webhook/polling just delivers events

---

## Recommendation

**Phase 1 (Now):** Deploy hybrid architecture with API-only
- ✅ Get webhooks + polling working
- ✅ Validate event flow
- ✅ Test database logging

**Phase 2 (Next Week):** Add Claude Code for scheduled workflows
- ✅ `run_agent.py standup` → Invokes Claude Code with standup-orchestrator.md
- ✅ `run_agent.py sla-check` → Invokes Claude Code with sla-monitor.md
- ✅ Uses MCP tools for Jira/codebase access

**Phase 3 (Future):** Full Claude Code integration
- ✅ Webhooks trigger Claude Code reasoning
- ✅ All agent context loaded automatically
- ✅ MCP tools used for all actions

---

**Bottom Line:** You're right to be concerned! The `.claude/` context is VALUABLE and we should use it. But we can do this incrementally:
1. Deploy current setup (works, but generic)
2. Add Claude Code for complex workflows (gets smarter)
3. Full migration (maximum intelligence)

Let me know which approach you prefer!
