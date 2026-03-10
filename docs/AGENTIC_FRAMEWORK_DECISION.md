

# Agentic Frammework conversion

## Purpose
We are moving away from claude code calls completely, and instead will manage requests via a langgraph agent that has the ability to call all our API based tools we ahve built. 

Assumptions:
- we no longer will call claude code in the project
- we will no longer use any MCP connections to Atlassian, Jira, Confluence, or Bitbucket
- have robust and capable API clis that our new agent can access via tools.


### Phase 1.  Langgraph Agent (Reactive)

The reactive langgraph agent is almost built. Located in ./src/agents it's goal is to:
- respond to direct tags and requests across our environemtn (slack, jira, confluence, bitbucket) The polling scripts that check jira, slack, confluence and bitbucket shoudl be passing their messages directly to invoke this agent.  And should keep track of threads by using the database***
- use tools as needed
- maintain conversational awareness (checkpointing).


### Phase 2. Proactive Langgraph Agent (Proactive)

PREREQUISITES: we wonly ONLY work on this after Phase 1. is complete, and fully integration tested for verification. STOP HERE. until this is confirmed and do not go any further.

The proactive agent will either be a separate agent, or a modification of our current langgraph agent (looking for a recommendation here.)

It's goals are:
- keep track of long-running tasks (like a deep agent) 
- have a system for follow-up and escalation to mimic that of a human employee
- use of same tools to conduct it's work
- conversational abilities via slack/bitbucket/jira and email to resolve tasks. 
- maintain long-term learning based on feedbacak and conversations from peole while conducting it's tasks. Long term memory needed, so our 'employee' improves over time and understands how to accomplish things. 

We will call this an employee agent. 

### Architecture of an Employee agent. 

The agentic loop of our employee should be as follows:

entry_node = receives message and processes via LLM OR every 1 hour check database for Tasks to work on. 

condiional_edge = determines if message is in reference to a Task, or is simply a question merting a normal one shot response.

if Task, we go to a task node. 

task_node = this node keeps track of the Task the agent is focused on.  it needs to:

1. pull the Task and relevant inforomation/context from our database. 

2. decide what to do next (possible another conditional edge?)

option a. - based on the task context dtermine if the Task has been completed or it needs additional follow-up.  If follow-up needed, check the SLA to determine when follow-up is appropriate.  If too soon, snooze the Task.   If ready, initiate the follow-up messages in the aprpopriate channel.

option b. - if there is work to be done that the employee can carry out themselves (without message follow-up), use enter a task 'work loop' where it can carry out the work itself. 

The work loop for a task should basically be an interative loop where the agent uses tools and decides when it's work is done, and then notifies and sends appropriate follow-up messages in the correct channel.  In here we should build a tool or ability to search confluence for specific SOPs and documentation relating to the task that was requested. Ideally we are able to write SOPs for each employee to carry out step by step. 

3. then we need a node to update the status of the Task,  update the timestamp and notes on follow-up (like if we sent a reminder and now should wait 1 day). We also should determine here if an 'escalation' is needed, or if the agent has gotten stuck. 

4. after we have updated the task, we should reflect on all that was done, and any messages sent from the team to determine if any knowledge has been accrued. If internal knowledge/insights store them in persistent knowledge, if any process updates requested update the appropriate SOP and get confirmation. 


A note on confirmation loops:
I feel like we should also have an agentic loop that iterates until approval is given on a particular task. The agent will do the work (via work loop), and then seek approval by the correct approver.  It will then continue to remind the approver until they approve the work (thus completing the task), or give feedback (creating more work/revisions and giving us the opportunity to learn something, or improve SOPs)



So what makes a good employee for our deep agent.

- has skills (can access all the platforms and tools)
- can communicate and ilicit and receive feedback
- keeps track of their tasks in a public task management way (jira)
- follows up on tasks and workso n them until they are complete
- speaks to whoever is necessary in order to collaborate and achieve their Tasks (while minimizing the reliance on others)
- learns from teh feedback given on each task overtime and constantly updates his internal knowledge of the company in terms of philosophy (maxims), and values, and of course specific SOPs he should be executing. 

This employee will be a high level employee and more of a manager first. In Phase 3, we will create additional specifialized employees that the manager can manage and assign tasks too in order to complete.

Ideas for sub-employees:
- developer employee (works on bug fixes, writes features, reviews pull requests)
- QA testing employee (writes tests for new features, checks in browser actual implementations, provides feedback on pull-requests that have stagign environment and links)
- accountant/HR employee (managing timesheets, cehcsk for weekly updates, reconciles employee invoices/payments with their reported time)
- project/product manager (runs release cycles, works to unblock tickets in current sprint,  does planning and refinement for follow-up sprints, writes release notes based on delivered features)

So maybe we call our top level agent the COO agent, and it's job is to monitor all channels for new data and responses, and identify new tasks to decide who to distribute too.

The employees, simply in a loop monitor the database for tasks assigned them, start work on new ones, and follow-up and work on old ones, always ilicitiing sign-off/approval until their tasks are complete. 

---

## Phase 2 Architecture Decision: LangGraph Subgraph Pattern

**Decision Date:** February 2026  
**Status:** Approved

### Summary

Phase 2 will be built as a **single LangGraph graph with subgraphs** — not separate agents or services. The reactive agent from Phase 1 will be extended with new nodes and subgraphs to support long-running task management, approval loops, and learning/reflection. Phase 3 (specialized employee agents) will introduce separate agents, each as their own subgraph invoked by a COO-level parent graph.

### Why Subgraphs

A subgraph is a compiled LangGraph graph used as a node inside a parent graph. It runs its own internal node/edge cycle, then returns control and state to the parent. From the parent's perspective, it's a single node — but internally it can loop, branch, and checkpoint independently.

Benefits over a flat graph:
- **Isolation** — the work loop's plan→execute→evaluate cycle doesn't pollute parent routing logic
- **Reusability** — the approval loop subgraph can be invoked from multiple contexts (task completion, SOP updates, PR reviews)
- **Testability** — compile and invoke any subgraph independently for unit testing
- **Phase 3 readiness** — specialized employee agents become subgraphs with different tool sets, invoked by the COO parent graph

### Graph Structure

```
Parent Graph (single deployed agent)
├── entry_node                        ← message received OR cron trigger
├── route_edge (conditional)
│   ├── "simple" → simple_response_node → END
│   └── "task"   → load_task_context
├── load_task_context                 ← pulls task + context from Postgres
├── decide_action (conditional edge)
│   ├── "do_work"    → work_loop_subgraph
│   ├── "follow_up"  → follow_up_node
│   └── "snooze"     → snooze_node → END
├── work_loop_subgraph               ← compiled subgraph as node
│   ├── plan_step
│   ├── execute_tool
│   ├── evaluate_result
│   └── (loops back to plan or exits)
├── approval_loop_subgraph           ← compiled subgraph as node
│   ├── request_approval
│   ├── wait_for_response            ← uses interrupt, resumes on message
│   ├── process_feedback
│   └── (loops back to work_loop or exits on approval)
├── update_task_state                ← writes status, timestamps, notes to Postgres
├── reflect_node                     ← extracts learnings, updates episodic memory
└── END
```

### State Passing Between Parent and Subgraphs

The parent graph passes its `AgentState` into subgraphs. Each subgraph operates on that state and returns modified state that merges back via reducers defined in the state schema. Key state fields:

- `task_id` — current task being worked on
- `task_status` — FSM state (new, in_progress, awaiting_approval, feedback, revision, complete)
- `messages` — conversation history (append reducer)
- `work_loop_iterations` — counter to prevent infinite loops
- `escalation_needed` — flag set by subgraphs when stuck

### Task State Management

Task lifecycle state lives in **Postgres** (source of truth), not Jira. Jira is the public interface — task status syncs to Jira for team visibility, but the agent's own DB has richer metadata:

| Field | Purpose |
|-------|---------|
| `task_id` | Primary key |
| `jira_key` | Synced Jira issue key (e.g., ECD-518) |
| `status` | FSM state: new → in_progress → awaiting_approval → feedback → revision → complete |
| `assigned_agent` | For Phase 3: which employee agent owns this |
| `sla_deadline` | When follow-up becomes appropriate |
| `snooze_until` | Timestamp to suppress polling |
| `follow_up_count` | Escalation counter |
| `follow_up_history` | JSON log of messages sent, channels used, timestamps |
| `context_snapshot` | Serialized context for resuming work |
| `approver` | Who needs to sign off |
| `notes` | Running log of actions taken |

### Cron / Polling

The "every 1 hour check database for tasks" pattern is implemented as a **separate Celery Beat task** that queries the task table and enqueues messages into the same `entry_node`. This keeps the graph pure (always message-triggered) and avoids mixing scheduling logic into graph nodes.

```python
# Celery beat schedule
@app.task
def poll_active_tasks():
    tasks = Task.objects.filter(
        status__in=["in_progress", "awaiting_approval"],
        snooze_until__lte=now()
    )
    for task in tasks:
        send_to_agent(thread_id=task.thread_id, message={
            "type": "cron_trigger",
            "task_id": task.id
        })
```

### Memory Architecture

Three distinct memory layers:

| Layer | What | Storage | Example |
|-------|------|---------|---------|
| **Working memory** | Current task context, conversation thread | LangGraph checkpointer (Postgres-backed) | "Waiting on Ed's approval for ECD-518" |
| **Episodic memory** | Task history, outcomes, feedback received | Postgres + pgvector embeddings | "Last time I wrote a Literature story, Ed asked for more technical notes" |
| **Procedural memory** | SOPs, company maxims, learned patterns | Confluence (source of truth) + vector index for RAG retrieval | "When writing Jira stories, follow the template in project instructions" |

The `reflect_node` updates episodic and procedural memory after each task interaction. Procedural memory updates (SOP changes) require human approval before being committed.

### Approval / Confirmation Loop

The approval loop is a subgraph that cycles: `do_work → request_approval → wait → (approved | feedback)`.

The "wait" state uses LangGraph's `interrupt_before` mechanism:
1. Graph checkpoints with a `waiting_for` field
2. Approval message arrives via Slack/Jira webhook → hits `entry_node` → `route_edge` matches it to the existing task's checkpoint thread
3. Graph resumes from the interrupt point
4. If feedback received → routes back to work_loop_subgraph for revisions
5. If approved → routes to update_task_state with status=complete
6. Escalation triggers when `follow_up_count` exceeds threshold defined in SLA

### Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Agent framework | LangGraph | Already in use from Phase 1 |
| Checkpointing | LangGraph PostgresSaver | Persists graph state for resume |
| Task state DB | Postgres | New `agent_tasks` table |
| Semantic search | pgvector | Already deployed for Evidence Cloud |
| SOP retrieval | RAG over Confluence | New — vector index over Confluence pages |
| Cron/polling | Celery Beat | Already in infrastructure |
| Message queue | Redis | Webhook → agent message passing |
| CLI tools | Existing API CLIs | No changes — registered as LangGraph tools |

### Phase 3 Extension Point

When Phase 3 begins, the single graph becomes the COO agent. Specialized employee agents (developer, QA, PM, etc.) are each their own compiled subgraph with role-specific tools. The COO's `decide_action` edge gains a new option: `"delegate"` → which invokes the appropriate employee subgraph and creates a task record assigned to that agent type.

Each employee agent follows the same internal pattern (work_loop + approval_loop) but with different tool registrations and SOP retrieval scopes.

### Implementation Priority

1. Task state Postgres table schema + CRUD operations
2. Approval/feedback loop subgraph (core interaction pattern everything else builds on)
3. Confluence RAG for SOP retrieval
4. Cron-based task polling via Celery Beat
5. Reflect/learning node (start simple — log insights, don't auto-update SOPs until trusted)
6. Work loop subgraph with tool execution cycle