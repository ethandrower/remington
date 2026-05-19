"""
Remington — LangGraph Conversational Agent

Handles @mentions from Slack with a proper ReAct loop and per-thread memory.

LANGGRAPH CONCEPT: THE GRAPH
==============================
A LangGraph graph is a directed graph where:

  - NODES  = Python functions. Each node takes the full AgentState, does
             work (calls an LLM, executes tools, etc.), and returns a dict
             of state updates.

  - EDGES  = Transitions between nodes. Can be fixed ("always go here next")
             or conditional ("look at the state and decide where to go").

  - STATE  = The shared object passed through every node. All communication
             between nodes happens via state — no direct function calls between
             nodes.

THE REACT LOOP (Reason + Act):
-------------------------------
The core pattern for a tool-using agent is:

    START
      │
      ▼
   [agent node] ← LLM reasons: do I need a tool or am I done?
      │
      ├─ has tool_calls? → [tools node] ← executes the requested tools
      │                        │
      │                        └──────────────► back to [agent node]
      │
      └─ no tool_calls? → END ← LLM produced a final answer

This loop continues until the LLM stops requesting tools and produces a
final text response.

CHECKPOINTING (Per-thread memory):
-----------------------------------
The graph is compiled with a SqliteSaver checkpointer. Every time the graph
runs, LangGraph:

  1. Loads the previous state for this thread_id from SQLite (if any)
  2. Runs the graph (appending new messages via the add_messages reducer)
  3. Saves the full updated state back to SQLite

This means each Slack thread has its own persistent conversation history.
A follow-up message in the same thread automatically has full context of
everything said before — without you doing anything.

The thread_id comes from the Slack thread's ts (timestamp), which is stable
across all messages in the same thread.
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

# Project root on path for src.* imports
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.agents.state import AgentState
from src.agents.tools import ALL_TOOLS

# ─── Configuration ────────────────────────────────────────────────────────────

# Handle the ANTRHOPIC_API_KEY typo in the existing .env
_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTRHOPIC_API_KEY")

JIRA_URL = os.getenv("JIRA_INSTANCE_URL", "")
PROJECT_KEY = os.getenv("ATLASSIAN_PROJECT_KEY", "")
BOT_NAME = os.getenv("SERVICE_ACCOUNT_NAME", "Bot")

# Where to persist conversation memory
_DB_PATH = Path(".claude/data/bot-state/agent_memory.db")
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = SystemMessage(content=f"""You are {BOT_NAME}, an autonomous project management \
assistant for a software development team. You respond to @mentions in Slack.

Your capabilities:
- Search and look up Jira tickets (project {PROJECT_KEY})
- Get full ticket details including comments
- Post comments on Jira tickets
- Move tickets to a new status
- Look up team members by name or email

How to respond:
- Be concise and direct — Slack is not a place for long essays
- Use *bold* and bullet points for readability
- Always include ticket links when referencing tickets
- If you take an action (post comment, change status), confirm it clearly
- If you can't do something, say so and suggest what you CAN do

Team context:
- Jira instance: {JIRA_URL}
- Active projects: {PROJECT_KEY}
- You are the service account "{BOT_NAME}" — not a human

When someone asks about tickets or asks you to take action on Jira, use your
tools. Don't guess at ticket details — look them up.
""")


# ─── LANGGRAPH CONCEPT: NODES ────────────────────────────────────────────────
#
# A node is just a function: (state: AgentState) -> dict
# The dict contains ONLY the fields you want to update.
# LangGraph merges the dict back into state using each field's reducer.
#
# The agent node calls the LLM. The LLM either:
#   a) Returns a final AIMessage with text → we're done
#   b) Returns an AIMessage with tool_calls → the tools node runs next


def agent_node(state: AgentState) -> dict:
    """
    The reasoning node — calls the LLM with the current conversation history.

    On first turn: prepends the system prompt.
    On subsequent turns: system prompt is already in history (checkpointed).
    """
    messages = state["messages"]

    # Prepend system prompt if not already there (first turn in this thread)
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM_PROMPT] + messages

    response = model.invoke(messages)

    # Return only the new message — add_messages reducer appends it
    return {"messages": [response]}


# ─── LANGGRAPH CONCEPT: CONDITIONAL EDGES ────────────────────────────────────
#
# Conditional edges are routing functions: (state) -> str
# The returned string names the next node (or END).
#
# This is the "should I keep looping or am I done?" decision.
# We check if the LLM's last message contains tool_calls.
# If yes → run the tools. If no → the LLM has a final answer → END.

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """
    Route: did the LLM call a tool, or is it done?

    LangGraph calls this after every agent_node run. The return value
    is the name of the next node to execute.
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"  # → ToolNode executes the requested tools

    return END  # → graph exits, response is the last AIMessage


# ─── LANGGRAPH CONCEPT: TOOL NODE ────────────────────────────────────────────
#
# ToolNode is a built-in LangGraph node. It:
#   1. Reads tool_calls from the last AIMessage in state
#   2. Looks up each tool by name in the tools list
#   3. Calls the tool with the provided arguments
#   4. Wraps each result in a ToolMessage
#   5. Returns {"messages": [ToolMessage, ...]} which gets appended to state
#
# After ToolNode runs, the edge sends us back to agent_node, where the LLM
# sees the ToolMessages and decides what to do next.


# ─── Model Setup ─────────────────────────────────────────────────────────────
#
# bind_tools() attaches the tool schemas to the model. When the model is
# invoked, it receives the list of available tools and can choose to call
# any of them. The actual execution happens in ToolNode, not here.

model = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=_api_key,
    temperature=0,          # Deterministic for PM tasks
    max_tokens=2048,
).bind_tools(ALL_TOOLS)


# ─── Build the Graph ─────────────────────────────────────────────────────────
#
# StateGraph(AgentState) creates a graph whose nodes all share AgentState.
# We add nodes by name, then wire them with edges.

_builder = StateGraph(AgentState)

# Add nodes
_builder.add_node("agent", agent_node)
_builder.add_node("tools", ToolNode(ALL_TOOLS))

# Fixed edge: always start at agent
_builder.add_edge(START, "agent")

# Conditional edge: after agent, route to tools OR end
_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",   # if tool_calls → run tools
        END: END,            # if no tool_calls → done
    },
)

# Fixed edge: after tools, always go back to agent
# (agent sees ToolMessages and decides next step)
_builder.add_edge("tools", "agent")


# ─── Compile with Checkpointer ───────────────────────────────────────────────
#
# LANGGRAPH CONCEPT: CHECKPOINTING
#
# compile(checkpointer=...) adds persistence to the graph.
# Every graph run is tied to a "thread" via config["configurable"]["thread_id"].
#
# LangGraph automatically:
#   - Loads prior state for this thread_id before running
#   - Saves updated state after running
#
# For us: thread_id = Slack thread ts → each Slack thread is its own
# conversation with full persistent history. No manual context building.
#
# SQLITE vs POSTGRES:
# We detect DATABASE_URL at startup (Heroku sets this automatically).
# - Local dev: SQLite, zero config, file on disk
# - Heroku:    PostgreSQL, same instance as the app but a dedicated schema
#              "langgraph" so LangGraph's internal tables never touch yours.
#
# The two checkpointers have identical interfaces — the graph code above
# is completely unaffected by which one is used.

def _build_checkpointer():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Production: PostgreSQL via langgraph-checkpoint-postgres
        # Uses psycopg3 (not psycopg2) — install: pip install psycopg[binary,pool]
        # LangGraph creates its tables in the "langgraph" schema, separate from
        # your app's tables. Call .setup() once to create those tables.
        try:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver

            # Heroku gives DATABASE_URL as postgres:// — psycopg3 needs postgresql://
            conn_str = database_url.replace("postgres://", "postgresql://", 1)

            # Use a dedicated schema so we don't need CREATE on public (PG15+)
            schema = "langgraph_agent"
            conn_str_with_schema = f"{conn_str}?options=-c%20search_path%3D{schema}"

            # Create the schema if it doesn't exist (users can create schemas even
            # without CREATE on public schema in PostgreSQL 15+)
            import psycopg
            with psycopg.connect(conn_str, autocommit=True) as _c:
                _c.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

            pool = ConnectionPool(
                conninfo=conn_str_with_schema,
                max_size=10,
                kwargs={"autocommit": True},
            )
            checkpointer = PostgresSaver(pool)
            checkpointer.setup()
            print(f"✅ Agent checkpointer: PostgreSQL (schema: {schema})")
            return checkpointer

        except ImportError:
            print("⚠️  DATABASE_URL set but psycopg/langgraph-checkpoint-postgres not installed.")
            print("   Falling back to SQLite. Run: pip install 'psycopg[binary,pool]' langgraph-checkpoint-postgres")
        except Exception as e:
            print(f"⚠️  PostgreSQL checkpointer failed ({e}). Falling back to SQLite.")
            print("   Conversation state will not persist across dyno restarts.")

    # Development: SQLite, file on disk, zero config
    # check_same_thread=False — the polling thread and graph thread differ
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    from langgraph.checkpoint.sqlite import SqliteSaver
    print(f"✅ Agent checkpointer: SQLite ({_DB_PATH})")
    return SqliteSaver(conn)


agent_app = _builder.compile(checkpointer=_build_checkpointer())


# ─── Oneshot Graph (no persistence) ──────────────────────────────────────────
#
# A second compiled graph that does NOT use a checkpointer. State only exists
# in memory for the duration of a single .invoke() call and is GCed after.
#
# Use this for stateless agent calls — PR reviews, Jira/Bitbucket webhook
# responses, etc. — where each invocation already gets the full context it
# needs (PR diff + comments fetched fresh) and there is no benefit to keeping
# a persistent transcript per resource. Persisting these was the root cause
# of unbounded `langgraph_agent.checkpoint_blobs` growth.

agent_app_oneshot = _builder.compile()


# ─── Public Interface ─────────────────────────────────────────────────────────

def run_agent(
    thread_ts: str,
    channel: str,
    author: str,
    message: str,
) -> str:
    """
    Process a Slack @mention and return the agent's text response.

    Args:
        thread_ts:  Slack thread timestamp — used as the LangGraph thread_id.
                    All messages in the same thread share conversation history.
        channel:    Slack channel ID (stored in state for context).
        author:     Display name of the person who sent the message.
        message:    The message text (bot mention already stripped).

    Returns:
        The agent's final text response to post back to Slack.
    """
    # thread_id ties this invocation to a persistent conversation.
    # LangGraph loads any prior messages for this thread automatically.
    config = {"configurable": {"thread_id": thread_ts}}

    # The input only contains NEW information for this turn.
    # Prior turns are loaded from the checkpointer automatically.
    result = agent_app.invoke(
        {
            "messages": [HumanMessage(content=f"{author}: {message}")],
            "channel": channel,
            "thread_ts": thread_ts,
            "author": author,
        },
        config=config,
    )

    # Last message is the final AIMessage (no tool_calls → exited loop)
    final = result["messages"][-1]
    return final.content


def run_agent_oneshot(
    message: str,
    author: str = "system",
    channel: str = "oneshot",
) -> str:
    """
    Stateless one-shot agent invocation — no persisted conversation history.

    Identical ReAct loop behavior to run_agent(), but compiled without a
    checkpointer, so nothing is written to the langgraph_agent.* tables. Use
    this for fire-and-forget tasks like PR reviews where the caller already
    provides full context (PR diff, comments) in the message itself.
    """
    result = agent_app_oneshot.invoke(
        {
            "messages": [HumanMessage(content=f"{author}: {message}")],
            "channel": channel,
            "thread_ts": "oneshot",
            "author": author,
        }
    )
    return result["messages"][-1].content
