"""
AgentState — the shared state that flows through every node in the graph.

LANGGRAPH CONCEPT: STATE & REDUCERS
====================================
LangGraph passes a single State object through every node. Each node receives
the full state, does its work, and returns a *dict of updates* — only the fields
it changed. LangGraph merges those updates back into the state.

The critical concept is REDUCERS. A reducer defines what "update" means for a
field:

  - No reducer (default):  new value REPLACES the old value entirely
  - add_messages reducer:  new messages are APPENDED to the existing list

Without reducers you'd have to return the full message history every time.
With add_messages, a node just returns [new_message] and LangGraph handles
appending it — conversation history accumulates naturally.

Example:
    State before node: messages = [HumanMessage("hi"), AIMessage("hello")]
    Node returns:      {"messages": [AIMessage("how can I help?")]}
    State after node:  messages = [HumanMessage("hi"), AIMessage("hello"), AIMessage("how can I help?")]
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The complete state for a single conversation thread.

    One AgentState instance exists per Slack thread. When a new message
    arrives in the same thread, LangGraph loads the checkpointed state
    (all prior messages) and the agent picks up mid-conversation.

    Fields:
        messages:   Full conversation history. The add_messages reducer
                    means nodes only need to return NEW messages — LangGraph
                    appends them automatically.

        channel:    Slack channel ID (e.g. "C02NW7QN1RN"). Stored in state
                    so tool nodes can post back to the right place without
                    needing it passed as a parameter.

        thread_ts:  Slack thread timestamp. This doubles as the LangGraph
                    thread_id for checkpointing — every message in the same
                    Slack thread maps to the same agent state.

        author:     Display name of the person who sent the current message.
                    Included so the agent can address them by name.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    channel: str
    thread_ts: str
    author: str
