"""
Unit tests for the LangGraph agent graph routing and run_agent() interface.

Strategy:
  - Test should_continue() directly with mock AgentState — no LLM needed.
  - Test run_agent() with model.invoke patched to return predefined AIMessages
    and agent_app replaced with a MemorySaver-backed graph for in-memory isolation.
  - No real LLM API calls. No SQLite files created on disk.

LANGGRAPH CONCEPT: Why MemorySaver?
  The production graph uses SqliteSaver which writes to disk. In tests we
  swap it for MemorySaver (in-memory dict) so:
    1. Tests are isolated — no shared state between runs
    2. No files created in the project directory
    3. Tests are fast — no I/O
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END


# ---------------------------------------------------------------------------
# should_continue routing
# ---------------------------------------------------------------------------

class TestShouldContinueRouting:
    """
    Test the conditional edge function in complete isolation.

    should_continue() only looks at the last message in state — it doesn't
    call the LLM, make API calls, or touch the checkpointer. Pure logic test.
    """

    def _make_state(self, messages):
        return {
            "messages": messages,
            "channel": "C_TEST",
            "thread_ts": "1234.000",
            "author": "Test User",
        }

    def test_routes_to_tools_when_tool_calls_present(self):
        from src.agents.conversation_agent import should_continue

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search_jira", "args": {"jql": "project = ECD"}, "id": "call_001"}],
        )
        state = self._make_state([HumanMessage(content="find blocked tickets"), ai_msg])
        assert should_continue(state) == "tools"

    def test_routes_to_end_when_no_tool_calls(self):
        from src.agents.conversation_agent import should_continue

        ai_msg = AIMessage(content="There are 5 blocked tickets.")
        state = self._make_state([HumanMessage(content="hi"), ai_msg])
        assert should_continue(state) == END

    def test_routes_to_end_when_tool_calls_is_empty_list(self):
        from src.agents.conversation_agent import should_continue

        ai_msg = AIMessage(content="Done.", tool_calls=[])
        state = self._make_state([HumanMessage(content="hi"), ai_msg])
        assert should_continue(state) == END

    def test_routes_to_tools_with_multiple_tool_calls(self):
        from src.agents.conversation_agent import should_continue

        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "search_jira", "args": {"jql": "..."}, "id": "call_001"},
                {"name": "get_jira_ticket", "args": {"issue_key": "ECD-1"}, "id": "call_002"},
            ],
        )
        state = self._make_state([HumanMessage(content="hi"), ai_msg])
        assert should_continue(state) == "tools"


# ---------------------------------------------------------------------------
# run_agent() — model mocked, MemorySaver checkpointer
# ---------------------------------------------------------------------------

class TestRunAgent:
    """
    Test run_agent() end-to-end with the LLM replaced by a mock.

    We rebuild the graph with MemorySaver and patch it onto the module so
    run_agent() uses in-memory state instead of SQLite.
    """

    @pytest.fixture(autouse=True)
    def use_memory_checkpointer(self, monkeypatch):
        """
        Replace agent_app with a fresh MemorySaver-backed graph for each test.

        Since conversation_agent.py compiles the graph at import time, we
        monkeypatch the module-level agent_app after import. run_agent()
        looks up agent_app at call time, so this replacement takes effect.
        """
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.graph import START, StateGraph
        from langgraph.prebuilt import ToolNode
        from src.agents.state import AgentState
        from src.agents.tools import ALL_TOOLS
        import src.agents.conversation_agent as mod

        builder = StateGraph(AgentState)
        builder.add_node("agent", mod.agent_node)
        builder.add_node("tools", ToolNode(ALL_TOOLS))
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", mod.should_continue, {"tools": "tools", END: END})
        builder.add_edge("tools", "agent")

        monkeypatch.setattr(mod, "agent_app", builder.compile(checkpointer=MemorySaver()))

    def _mock_model(self, *responses):
        """
        Return a MagicMock that replaces the module-level `model` object.

        model is a RunnableBinding (Pydantic, frozen), so we can't patch
        model.invoke directly. Instead we replace the whole model object
        with a MagicMock whose .invoke() returns the given responses in order.
        """
        mock = MagicMock()
        mock.invoke.side_effect = list(responses)
        return mock

    def test_returns_string(self):
        """Basic sanity: run_agent() returns a plain string."""
        fake_ai = AIMessage(content="There are 5 blocked tickets.")
        mock_model = self._mock_model(fake_ai)

        with patch("src.agents.conversation_agent.model", mock_model):
            from src.agents.conversation_agent import run_agent
            result = run_agent(
                thread_ts="thread-basic-001",
                channel="C_TEST",
                author="Alice",
                message="how many blocked tickets?",
            )

        assert isinstance(result, str)
        assert "5 blocked tickets" in result

    def test_author_and_message_are_passed_to_model(self):
        """The HumanMessage sent to the model should contain the author name and message text."""
        fake_ai = AIMessage(content="Got it.")
        mock_model = self._mock_model(fake_ai)

        with patch("src.agents.conversation_agent.model", mock_model):
            from src.agents.conversation_agent import run_agent
            run_agent("thread-author-002", "C_TEST", "Bob", "what's ECD-100?")

        call_args = mock_model.invoke.call_args_list[0]
        messages_passed = call_args[0][0]  # first positional arg
        human_msgs = [m for m in messages_passed if isinstance(m, HumanMessage)]
        assert len(human_msgs) == 1
        assert "Bob" in human_msgs[0].content
        assert "ECD-100" in human_msgs[0].content

    def test_system_prompt_prepended_on_first_turn(self):
        """System prompt should be injected before first model call."""
        fake_ai = AIMessage(content="Hello.")
        mock_model = self._mock_model(fake_ai)

        with patch("src.agents.conversation_agent.model", mock_model):
            from src.agents.conversation_agent import run_agent
            run_agent("thread-sys-003", "C_TEST", "Alice", "hi")

        call_args = mock_model.invoke.call_args_list[0]
        messages_passed = call_args[0][0]
        system_msgs = [m for m in messages_passed if isinstance(m, SystemMessage)]
        assert len(system_msgs) == 1

    def test_different_threads_are_independent(self):
        """Two different thread_ts values get separate conversation histories."""
        response_a = AIMessage(content="Response for Alice's thread.")
        response_b = AIMessage(content="Response for Bob's thread.")
        mock_model = self._mock_model(response_a, response_b)

        with patch("src.agents.conversation_agent.model", mock_model):
            from src.agents.conversation_agent import run_agent
            result_a = run_agent("thread-indep-A", "C_TEST", "Alice", "message A")
            result_b = run_agent("thread-indep-B", "C_TEST", "Bob", "message B")

        assert "Alice's thread" in result_a
        assert "Bob's thread" in result_b

    def test_same_thread_accumulates_history(self):
        """
        Second message in same thread should be sent to the model with the full
        prior conversation included (first human message + first AI response).
        """
        first_ai = AIMessage(content="ECD-100 is a login bug.")
        second_ai = AIMessage(content="As I mentioned, ECD-100 is a login bug.")
        mock_model = self._mock_model(first_ai, second_ai)

        with patch("src.agents.conversation_agent.model", mock_model):
            from src.agents.conversation_agent import run_agent
            run_agent("thread-memory-004", "C_TEST", "Alice", "what is ECD-100?")
            run_agent("thread-memory-004", "C_TEST", "Alice", "tell me more")

        first_call_msgs = mock_model.invoke.call_args_list[0][0][0]
        second_call_msgs = mock_model.invoke.call_args_list[1][0][0]

        assert len(second_call_msgs) > len(first_call_msgs), (
            f"Expected second call to receive more messages ({len(second_call_msgs)}) "
            f"than first ({len(first_call_msgs)}) — memory not accumulating"
        )
