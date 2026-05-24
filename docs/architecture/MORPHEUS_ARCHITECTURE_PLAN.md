# Morpheus — Architecture Plan

**Status:** Planning
**Date:** 2026-03-17
**Author:** Ethan Drower

---

## Overview

Extract the agent runtime from `project-manager` into a new standalone framework called **Morpheus**. The project-manager becomes the *Remington agent's dashboard module*, not the runtime itself. This enables multiple agents, multiple dashboards, and a clean separation between the runtime layer and the data/analytics layer.

### Naming Convention

| Thing | Name | Why |
|---|---|---|
| Agent runtime + shell | **Morpheus** | Shows people the truth |
| Central database | **The Source** | The machine mainframe — origin of all programs |
| PM agent | **Remington** | Stays as is |
| PM dashboard | **Remington Dashboard** | Lives inside Morpheus as a Blueprint |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MORPHEUS                                  │
│                   (Agent Runtime Layer)                          │
│                                                                  │
│  ┌──────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │  Slack       │   │  Agent Registry │   │  Control Panel  │  │
│  │  Webhooks    │──▶│  + Router       │──▶│  (Web UI)       │  │
│  │              │   │                 │   │                 │  │
│  │ /events/     │   │ channel → agent │   │ Sessions panel  │  │
│  │  remington   │   │ config per agent│   │ Agents panel    │  │
│  │ /events/     │   │ tools per agent │   │ Cron jobs panel │  │
│  │  codebot     │   │                 │   │ Goals panel     │  │
│  └──────────────┘   └────────┬────────┘   └─────────────────┘  │
│                               │                                  │
│                    ┌──────────▼────────┐                        │
│                    │  LangGraph        │                        │
│                    │  Executor         │                        │
│                    │  (per-agent graph │                        │
│                    │  + session store) │                        │
│                    └──────────┬────────┘                        │
│                               │                                  │
│              ┌────────────────┼────────────────┐                │
│              ▼                ▼                 ▼                │
│        [remington]       [codebot]       [future agent]         │
│         AGENT.md          AGENT.md          AGENT.md            │
│         tools.py          tools.py          tools.py            │
│         config.yaml       config.yaml       config.yaml         │
│         dashboard/                                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP API calls
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    THE SOURCE (Postgres)                         │
│                  Single unified database                         │
│                                                                  │
│   morpheus_*     │   rem_*           │   mon_*                  │
│   (core runtime) │   (remington)     │   (monitor state)        │
│                  │                   │                           │
│   + langgraph_agent schema (LangGraph checkpointer)             │
└─────────────────────────────────────────────────────────────────┘
```

### Three Distinct UI Layers

```
Morpheus Control Panel     → "Is the runtime healthy?"
  Sessions, agents, cron,    (ops/engineering view)
  goals, channel routing,
  logs, coding agent status

Purpose-Built Dashboards   → "What is this agent telling me?"
  Sprint health, PR          (stakeholder view, per use case)
  velocity, incident
  status, etc.

Slack / Chat Interface     → "Talk to the agent directly"
  @remington blocked?        (everyone, conversational)
  @codebot review PR 47
```

---

## Repo Structure

```
morpheus/                              ← NEW REPO
├── src/
│   ├── runtime/
│   │   ├── agent_registry.py          # loads agents/ configs
│   │   ├── executor.py                # LangGraph factory per agent
│   │   ├── session_store.py           # namespaced checkpointer
│   │   └── router.py                  # channel → agent lookup
│   ├── channels/
│   │   └── slack.py                   # Events API webhook handler
│   ├── web/
│   │   ├── app.py                     # Shell Flask + blueprint autodiscovery
│   │   └── templates/
│   │       └── shell.html             # nav + sidebar + <main>
│   ├── database/
│   │   ├── connection.py              # get_engine() → The Source
│   │   └── schema/
│   │       ├── morpheus.py            # morpheus_* tables
│   │       └── monitors.py            # mon_* tables
│   └── shared_tools/
│       ├── slack_tools.py             # post_message, react
│       └── http_tools.py             # generic API caller
│
├── agents/
│   └── remington/
│       ├── config.yaml
│       ├── AGENT.md
│       ├── tools.py                   # jira tools + sprint_report HTTP call
│       ├── database/
│       │   └── schema/
│       │       └── remington.py       # rem_* tables
│       └── dashboard/
│           ├── blueprint.py           # Flask Blueprint (url_prefix=/agents/remington)
│           ├── routes.py              # all /api/* endpoints (from project-manager)
│           ├── sprint_report.py       # compute module (from project-manager)
│           └── templates/
│               └── dashboard.html     # Vue.js sprint UI (from project-manager)
│
├── coding-agent/                      # Runs on Ubuntu/Tailscale server
│   └── server.py                      # FastAPI, receives tasks, runs claude headless
│
├── Procfile
├── requirements.txt
└── .env.example
```

### Agent Config Format

```yaml
# agents/remington/config.yaml
id: remington
name: Remington
slack_bot_token_env: SLACK_BOT_TOKEN_REMINGTON
slack_bot_user_id_env: SLACK_BOT_USER_ID_REMINGTON
channels: ["*"]           # respond anywhere mentioned
session_namespace: remington
system_prompt: agents/remington/AGENT.md
tools:
  - jira.search
  - jira.get_ticket
  - jira.comment
  - jira.transition
  - jira.lookup_user
  - sprint.get_report       # HTTP GET /api/agent/sprint-report
  - slack.post_message
  - coding_agent            # delegate code changes to Claude Code
```

---

## The Source — Database Schema

### Design Principles
- Single Postgres database, replacing 8 fragmented SQLite files
- Namespaced tables: `morpheus_*` (core), `rem_*` (remington), `mon_*` (monitors)
- LangGraph keeps its own `langgraph_agent` schema (untouched)
- All access via SQLAlchemy Core (same pattern as current codebase)

---

### Core Morpheus Tables

```sql
-- Agent registry
morpheus_agents
  id              VARCHAR(50) PK        -- "remington", "codebot"
  name            VARCHAR(100)
  status          VARCHAR(20)           -- "active", "disabled"
  config_path     VARCHAR(255)
  has_dashboard   BOOLEAN DEFAULT TRUE
  created_at      DATETIME

-- Human-readable session index (LangGraph stores actual messages separately)
morpheus_sessions
  id              VARCHAR(100) PK       -- "remington:1742230000.000001"
  agent_id        VARCHAR(50) FK → morpheus_agents.id
  thread_ts       VARCHAR(50)
  channel_id      VARCHAR(50)
  user_id         VARCHAR(50)
  user_name       VARCHAR(100)
  message_count   INTEGER DEFAULT 0
  last_message_at DATETIME
  last_message    TEXT                  -- preview only
  status          VARCHAR(20)           -- "active", "idle", "error"
  created_at      DATETIME

-- Channel routing
morpheus_channel_bindings
  id              INTEGER PK AUTOINCREMENT
  agent_id        VARCHAR(50) FK → morpheus_agents.id
  channel_id      VARCHAR(50)           -- Slack channel ID, or "*" for default
  channel_name    VARCHAR(100)
  priority        INTEGER DEFAULT 0
  enabled         BOOLEAN DEFAULT TRUE
  UNIQUE(channel_id, agent_id)

-- Scheduled + triggered jobs (replaces check_schedules + clock.py)
morpheus_jobs
  id              INTEGER PK AUTOINCREMENT
  agent_id        VARCHAR(50)
  name            VARCHAR(100)
  job_key         VARCHAR(50) UNIQUE
  trigger_type    VARCHAR(20)           -- "schedule" | "event" | "manual" | "reactive"
  trigger_config  TEXT                  -- JSON per type:
                                        --   schedule: {"cron": "0 9 * * 1-5", "tz": "America/New_York"}
                                        --   event:    {"source": "jira", "event": "status_changed",
                                        --              "filter": {"status": "Blocked"}}
                                        --   reactive: {"on_completion_of": "standup"}
  sop             TEXT                  -- instructions/prompt for what to do
  delivery_channel VARCHAR(50)
  enabled         BOOLEAN DEFAULT TRUE
  last_run_at     DATETIME
  next_run_at     DATETIME
  description     TEXT

-- Job run history (replaces check_runs)
morpheus_job_runs
  id              INTEGER PK AUTOINCREMENT
  job_key         VARCHAR(50) FK → morpheus_jobs.job_key
  agent_id        VARCHAR(50)
  triggered_by    VARCHAR(20)           -- "scheduled" | "manual" | "agent" | "event"
  started_at      DATETIME NOT NULL
  completed_at    DATETIME
  duration_seconds INTEGER
  status          VARCHAR(20)           -- "running" | "success" | "failed"
  violations_found INTEGER DEFAULT 0
  output_json     TEXT
  error_message   TEXT

-- Skill registry
morpheus_skills
  id              VARCHAR(50) PK        -- "jira_search", "post_slack", "coding_agent"
  agent_id        VARCHAR(50)           -- NULL = shared across all agents
  name            VARCHAR(100)
  description     TEXT                  -- what the LLM reads to decide when to use it
  skill_type      VARCHAR(20)           -- "tool" | "script" | "api" | "coding_agent"
  implementation  TEXT                  -- JSON: {path, function, endpoint}
  parameters      TEXT                  -- JSON Schema
  enabled         BOOLEAN DEFAULT TRUE
  use_count       INTEGER DEFAULT 0
  last_used_at    DATETIME

-- Event stream / audit log (replaces activities table)
morpheus_events
  id              INTEGER PK AUTOINCREMENT
  agent_id        VARCHAR(50)
  session_id      VARCHAR(100)
  event_type      VARCHAR(50)           -- "mention_received" | "tool_called" |
                                        -- "job_started" | "slack_sent" | "goal_updated"
  payload         TEXT                  -- JSON
  created_at      DATETIME NOT NULL
```

---

### Goals — The New Agentic Primitive

Goals represent long-term or multi-step agent initiatives. They have a state machine, step decomposition, and human approval checkpoints.

```
State machine:
  new → planning → in_progress ⇄ awaiting_approval
                       ↕
                    blocked → in_progress (when unblocked)
                       ↓
                complete / failed / cancelled
```

```sql
-- Goal definition
morpheus_goals
  id              UUID PK
  agent_id        VARCHAR(50)
  title           VARCHAR(255)          -- "Book Q2 customer meetings"
  description     TEXT
  created_by      VARCHAR(100)          -- Slack user ID
  created_via     VARCHAR(20)           -- "slack" | "api" | "cron" | "agent"
  status          VARCHAR(20)           -- state machine above
  priority        INTEGER DEFAULT 3     -- 1=urgent, 5=low
  due_date        DATE
  plan            TEXT                  -- Claude's decomposition into steps
  progress_log    TEXT                  -- append-only journal
  context         TEXT                  -- JSON: original request, linked tickets
  session_id      VARCHAR(100)          -- linked morpheus_sessions.id
  parent_goal_id  UUID                  -- for sub-goals (self-referential FK)
  created_at      DATETIME
  updated_at      DATETIME
  completed_at    DATETIME

-- Steps decomposed from goal
morpheus_goal_steps
  id              UUID PK
  goal_id         UUID FK → morpheus_goals.id
  step_number     INTEGER
  description     TEXT
  status          VARCHAR(20)           -- "pending" | "active" | "complete" | "skipped" | "failed"
  skill_id        VARCHAR(50)           -- which skill to use
  input           TEXT                  -- JSON inputs for the skill
  output          TEXT                  -- result from execution
  requires_human  BOOLEAN DEFAULT FALSE -- pause here for approval?
  created_at      DATETIME
  completed_at    DATETIME

-- Human approval / communication checkpoints
morpheus_goal_checkpoints
  id              UUID PK
  goal_id         UUID FK → morpheus_goals.id
  step_id         UUID
  checkpoint_type VARCHAR(30)           -- "approval_needed" | "progress_update" |
                                        -- "blocked_on_human" | "clarification_needed"
  message         TEXT                  -- what the agent is asking/reporting
  slack_thread_ts VARCHAR(50)
  response        TEXT                  -- human's reply
  status          VARCHAR(20)           -- "pending" | "approved" | "rejected" | "noted"
  created_at      DATETIME
  responded_at    DATETIME
```

**Goal complexity examples:**

| Goal | Steps | Checkpoints |
|---|---|---|
| "Update ECD-1234 with Figma URL" | 1 (jira.edit) | 0 — done instantly |
| "Write V6 release notes to Confluence" | 3 (get_report → draft → post) | 1 (approve draft) |
| "Book Q2 customer check-ins" | N steps per contact | Multiple over weeks |
| "Add teams tab to burndown chart" | plan → code → PR → review → merge | 2 (approve plan, approve PR) |

---

### Remington Agent Tables (`rem_*`)

Existing tables, renamed and consolidated into The Source.

| New Name | Old Name | Change |
|---|---|---|
| `rem_team_members` | `team_members` | Rename only |
| `rem_active_violations` | `active_violations` | Rename only |
| `rem_blocked_analyses` | `blocked_ticket_analyses` | Rename only |
| `rem_blocked_alerts` | `blocked_sent_alerts` | Rename only |
| `rem_timesheet_weeks` | `timesheet_weeks` | Rename only |
| `rem_timesheet_entries` | `timesheet_entries` | Rename only |
| `rem_pm_requests` | `pending_pm_requests` | Rename only |
| `rem_pm_revisions` | `pm_request_revisions` | Rename only |
| `rem_channel_config` | `channel_config` | Rename only |
| `rem_system_config` | `system_config` | Rename only |
| `rem_sla_alerts` | `slack_sla_alerts` | Rename only |

---

### Monitor State Tables (`mon_*`)

Polling dedup tables for Jira, Bitbucket, Confluence monitors. Slack polling tables are deleted (replaced by webhook).

| New Name | Old Name |
|---|---|
| `mon_jira_processed_mentions` | `jira_processed_mentions` |
| `mon_jira_last_check` | `jira_last_check` |
| `mon_bb_pr_comments` | `bb_processed_pr_comments` |
| `mon_bb_last_check` | `bb_last_check_per_repo` |
| `mon_bb_reviewed_commits` | `bb_reviewed_pr_commits` |
| `mon_bb_last_pr_commit` | `bb_last_pr_commit` |
| `mon_confluence_comments` | `confluence_processed_comments` |
| `mon_confluence_last_check` | `confluence_last_check` |

---

### Tables to Delete

```
slack_processed_messages    ← replaced by Slack Events API (webhook dedup via event_id)
slack_tracked_threads       ← replaced by morpheus_sessions + LangGraph checkpointer
agent_cycles                ← dead code, never used
webhook_events              ← dead code, never used
```

---

### Table Count Summary

| | Before | After |
|---|---|---|
| DB files | 8 separate SQLite files | 1 Postgres (The Source) + `langgraph_agent` schema |
| Total tables | 26 (+ 2 dead) | 22 |
| Deleted | — | 4 |
| New | — | 10 (morpheus_* core + goals) |
| Renamed | — | 19 |

---

## The Coding Agent

Claude Code running headlessly on an Ubuntu server (Tailscale-connected). No custom coding agent needed — Claude Code IS the coding agent.

```
Ubuntu Server (Tailscale: 100.x.x.x)
├── /srv/morpheus/             ← repo checked out
├── /srv/project-manager/      ← repo checked out
└── coding-agent/
    └── server.py              ← FastAPI wrapper (~50 lines)
```

```python
# coding-agent/server.py
@app.post("/task")
async def run_task(repo: str, task: str):
    result = subprocess.run(
        ["claude", "-p", task, "--output-format", "json",
         "--allowedTools", "Edit,Write,Bash,Glob,Grep,Read"],
        cwd=REPOS[repo],
        timeout=600
    )
    return {"result": result.stdout, "success": result.returncode == 0}
```

Morpheus registers `coding_agent` as a skill. Any goal or job that requires code changes calls it. The `CLAUDE.md` in each repo handles context, constraints, and coding standards.

**Why Tailscale:** No public port exposure, no auth headers, only reachable from your tailnet.

---

## Agent Memory Model

```
┌─────────────────────────────────────────────────────────┐
│              AGENT MEMORY ARCHITECTURE                   │
│                                                          │
│  Episodic    → Conversations        LangGraph            │
│               "what was said"       checkpointer ✅      │
│                                                          │
│  Semantic    → Knowledge/facts      MEMORY.md now        │
│               "what I know"         pgvector later       │
│                                                          │
│  Procedural  → Skills               morpheus_skills      │
│               "what I can do"       + @tool definitions  │
│                                                          │
│  Declarative → Jobs                 morpheus_jobs        │
│               "what I do routinely" + event triggers     │
│                                                          │
│  Working     → Goals                morpheus_goals       │
│               "what I'm pursuing"   + goal_steps         │
│                                     + checkpoints        │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1 — Foundation (new morpheus repo + The Source DB)
- [ ] Create `morpheus` GitHub repo
- [ ] Set up `get_engine()` pointing at The Source (new Postgres on Heroku)
- [ ] Create `morpheus_*` schema tables (agents, sessions, channel_bindings, jobs, job_runs, skills, events)
- [ ] Flask shell app — nav renders from agent registry, placeholder main area
- [ ] Create `agents/remington/config.yaml`

### Phase 2 — Migrate Remington Dashboard
- [ ] Move `src/dashboard/app.py` routes → `agents/remington/dashboard/routes.py`
- [ ] Move `src/dashboard/sprint_report.py` → `agents/remington/dashboard/`
- [ ] Move `templates/dashboard.html` → `agents/remington/dashboard/templates/`
- [ ] Register as Flask Blueprint at `/agents/remington`
- [ ] Rename `team_members` → `rem_team_members`, update all references
- [ ] Rename remaining `rem_*` tables in batches
- [ ] Verify sprint dashboard loads identically inside the shell

### Phase 3 — Webhook Switch (Slack)
- [ ] Add `/slack/events` endpoint to `src/channels/slack.py`
- [ ] Configure Slack app — Events API, `app_mention` + `message.im`
- [ ] Wire to `run_agent()` via background thread + immediate 200 ack
- [ ] Enable DM support (`message.im` event type)
- [ ] Delete `slack_processed_messages`, `slack_tracked_threads` tables
- [ ] Delete `SlackMonitor` polling code
- [ ] Test: mention in channel, DM, thread reply — all instant

### Phase 4 — Migrate Agent Runtime
- [ ] Move `src/agents/` → `morpheus/src/runtime/executor.py` (LangGraph factory)
- [ ] Move `src/agents/tools/` → `agents/remington/tools.py`
- [ ] Add `get_sprint_report` tool (HTTP call to Remington dashboard API)
- [ ] Wire `morpheus_sessions` table — updated on each `run_agent()` call
- [ ] Wire `morpheus_events` table — replaces `activities`
- [ ] Register skills in `morpheus_skills`

### Phase 5 — Control Panel UI
- [ ] Sessions tab — list from `morpheus_sessions`, click to see thread
- [ ] Cron Jobs tab — from `morpheus_jobs`, run-now button, history
- [ ] Agents tab — from `morpheus_agents`, enable/disable
- [ ] Channel Routing tab — manage `morpheus_channel_bindings`
- [ ] Goals tab — from `morpheus_goals`, status board, checkpoint approvals

### Phase 6 — Goals Engine
- [ ] `morpheus_goals` + `morpheus_goal_steps` + `morpheus_goal_checkpoints` schema
- [ ] Goal creation via Slack: "@remington goal: do X by Y date"
- [ ] Planning node: Claude decomposes goal into steps, posts plan for approval
- [ ] Execution loop: work through steps, call skills, pause at `requires_human` steps
- [ ] Checkpoint posting to Slack: wait for approval before continuing
- [ ] Goals tab in control panel

### Phase 7 — Coding Agent + Triggers
- [ ] `coding-agent/server.py` on Ubuntu + Tailscale
- [ ] Register `coding_agent` as a skill in Morpheus
- [ ] Event triggers in `morpheus_jobs` (`trigger_type = "event"`)
- [ ] Event sources: Jira status change, PR opened, Slack keyword
- [ ] Example reactive job: "When ticket moves to Blocked → run blocked analysis"

### Phase 8 — Semantic Memory (pgvector)
- [ ] Add `pgvector` extension to The Source
- [ ] `morpheus_memory` table: `(id, agent_id, content, embedding vector(1536), created_at, tags)`
- [ ] `memory_search` skill: semantic search over agent memories
- [ ] `memory_save` skill: agent can write to its own memory
- [ ] Auto-save important conversation turns to memory

---

## Heroku After Migration

| App | Dynos | Role |
|---|---|---|
| `morpheus` (new) | web 1x | Shell + agent runtime + all agent dashboards |
| `remington-project-manager` | decommission | Fully absorbed into Morpheus |

One app. One DB. One login. All dashboards. All agents.

---

## Key Design Decisions

1. **Webhooks over polling for Slack** — instant delivery, no dedup table, enables DMs
2. **Flask Blueprints for dashboards** — each agent's dashboard is fully self-contained, Claude Code can modify one without touching others
3. **LangGraph checkpointer unchanged** — keeps the per-thread memory that already works
4. **`morpheus_sessions` is an index, not a store** — LangGraph owns the actual message history; sessions table is just the human-readable panel data
5. **Goals are optional complexity** — phases 1-4 give a fully working system; goals are additive
6. **Claude Code headless = coding agent** — no custom coding framework needed, CLAUDE.md handles context/constraints
7. **Single DB (The Source)** — eliminates 8-file fragmentation, enables FK relationships, simpler ops
