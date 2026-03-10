"""
Jira tools for the LangGraph agent.

LANGGRAPH CONCEPT: TOOLS
=========================
A tool is just a Python function decorated with @tool. LangGraph/LangChain
uses two things from the function to teach the LLM about it:

1. DOCSTRING → tool description
   The LLM reads this to decide WHEN to use the tool. Write it like you're
   explaining to a smart person what the function does and when to use it.
   Be specific — vague docstrings lead to wrong tool selection.

2. TYPE ANNOTATIONS → input schema (JSON Schema)
   LangChain inspects the function signature and builds a JSON Schema from it.
   This is what the LLM fills in when it decides to call the tool.
   Always annotate every parameter — unannotated params get ignored.

3. RETURN VALUE → what the LLM sees after execution
   Tools should return a STRING (or something JSON-serializable). The LLM
   receives this as a ToolMessage and uses it for its next reasoning step.
   Format it clearly — the LLM will quote from it in its response.

These tools wrap the existing src/tools/jira/ functions so we don't duplicate
any API logic. The @tool layer just handles the LLM interface (schema +
description) and formats the output for readability.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

# Ensure project root is on the path so src.tools.jira.* imports work
_root = Path(__file__).parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.tools.jira.search import search_jira as _search_jira
from src.tools.jira.get_issue import get_jira_issue as _get_issue
from src.tools.jira.add_comment import add_jira_comment as _add_comment
from src.tools.jira.lookup_user import lookup_jira_user as _lookup_user

# Jira web URL for building ticket links in responses
JIRA_WEB_URL = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")


# ─── Tool 1: Search ─────────────────────────────────────────────────────────

@tool
def search_jira(jql: str, max_results: int = 10) -> str:
    """
    Search Jira tickets using JQL (Jira Query Language).

    Use this to find tickets by any criteria: status, assignee, sprint,
    priority, label, date range, etc.

    Common JQL patterns:
    - 'project = ECD AND sprint in openSprints() AND status = "In Progress"'
    - 'project = ECD AND assignee = "Mohamed Belkahla" AND status != Done'
    - 'project = ECD AND status = "Blocked" AND resolution is EMPTY'
    - 'project = ECD AND priority = High AND updated >= -7d'

    Args:
        jql: A valid JQL query string.
        max_results: Max tickets to return (default 10, max 50).

    Returns:
        Formatted list of matching tickets with key, summary, status, assignee.
    """
    result = _search_jira(jql, max_results=min(max_results, 50))

    if result.get("error"):
        return f"Jira search failed: {result.get('message', 'Unknown error')}"

    issues = result.get("issues", [])
    total = result.get("total", 0)

    if not issues:
        return f"No tickets found matching: {jql}"

    lines = [f"Found {total} tickets (showing {len(issues)}):"]
    for issue in issues:
        link = f"{JIRA_WEB_URL}/browse/{issue['key']}"
        assignee = issue.get("assignee") or "Unassigned"
        status = issue.get("status") or "Unknown"
        lines.append(
            f"• {issue['key']}: {issue.get('summary', '')[:70]}\n"
            f"  Status: {status} | Assignee: {assignee} | {link}"
        )

    return "\n".join(lines)


# ─── Tool 2: Get Ticket Details ──────────────────────────────────────────────

@tool
def get_jira_ticket(issue_key: str, include_comments: bool = False) -> str:
    """
    Get full details of a specific Jira ticket by its key (e.g. ECD-123).

    Use this when you need to know everything about a specific ticket:
    description, current status, assignee, priority, sprint, recent comments.
    Use search_jira first to find the key if you don't already have it.

    Args:
        issue_key: The Jira ticket key, e.g. "ECD-123" or "MDP-45".
        include_comments: Set True to also fetch recent comments (default False).

    Returns:
        Full ticket details including description, status, assignee, and
        optionally recent comments.
    """
    result = _get_issue(issue_key, include_comments=include_comments)

    if result.get("error"):
        return f"Could not fetch {issue_key}: {result.get('message', 'Unknown error')}"

    link = f"{JIRA_WEB_URL}/browse/{issue_key}"
    lines = [
        f"*{issue_key}*: {result.get('summary', 'No summary')}",
        f"Link: {link}",
        f"Status: {result.get('status')} | Priority: {result.get('priority')} | Type: {result.get('type')}",
        f"Assignee: {result.get('assignee', 'Unassigned')} | Reporter: {result.get('reporter', 'Unknown')}",
    ]

    if result.get("sprint"):
        lines.append(f"Sprint: {result.get('sprint')}")

    if result.get("description"):
        desc = result["description"][:500]
        lines.append(f"\nDescription:\n{desc}{'...' if len(result['description']) > 500 else ''}")

    if include_comments and result.get("comments"):
        lines.append(f"\nRecent comments ({len(result['comments'])}):")
        for c in result["comments"][-5:]:
            lines.append(f"  [{c.get('author', '?')} @ {c.get('created', '')[:10]}]: {c.get('text', '')[:200]}")

    return "\n".join(lines)


# ─── Tool 3: Add Comment ─────────────────────────────────────────────────────

@tool
def add_jira_comment(issue_key: str, comment: str) -> str:
    """
    Post a comment on a Jira ticket.

    Use this to respond to questions, provide status updates, flag blockers,
    or communicate with the team directly on a ticket. The comment will appear
    as posted by the Remington service account.

    To @mention someone, include their name in the comment text like "@Mohamed"
    and also pass their account_id via the mentions parameter. If you don't
    know the account ID, use lookup_jira_user first.

    Args:
        issue_key: The Jira ticket key, e.g. "ECD-123".
        comment: The comment text to post. Plain text or markdown.

    Returns:
        Confirmation with the comment ID, or an error message.
    """
    result = _add_comment(issue_key, comment)

    if result.get("error"):
        return f"Failed to post comment on {issue_key}: {result.get('message', 'Unknown error')}"

    return (
        f"Comment posted on {issue_key} (ID: {result.get('comment_id', '?')}).\n"
        f"Text: {comment[:150]}{'...' if len(comment) > 150 else ''}"
    )


# ─── Tool 4: Transition (change status) ──────────────────────────────────────

@tool
def transition_jira_ticket(issue_key: str, new_status: str) -> str:
    """
    Change the status of a Jira ticket (e.g. move it to "In Progress" or "Done").

    Use this when someone asks you to move a ticket, mark it complete, put it
    In Progress, send it to QA, etc.

    Common statuses: "To Do", "In Progress", "In Development", "Ready For QA",
    "In QA", "Done", "Blocked", "Cancelled", "Pending Approval"

    The status name must match an available transition from the ticket's current
    state. If the transition fails, try a slightly different status name.

    Args:
        issue_key: The Jira ticket key, e.g. "ECD-123".
        new_status: The target status name (case-insensitive).

    Returns:
        Confirmation that the transition succeeded, or an error with available
        transitions if the requested status is not reachable.
    """
    # Import here to avoid circular issues at module load
    from src.tools.jira.transition_issue import transition_jira_issue

    result = transition_jira_issue(issue_key, new_status)

    if result.get("error"):
        # Try to include available transitions if the API returns them
        available = result.get("available_transitions", [])
        msg = f"Could not transition {issue_key} to '{new_status}': {result.get('message', 'Unknown error')}"
        if available:
            msg += f"\nAvailable transitions: {', '.join(available)}"
        return msg

    return (
        f"Moved {issue_key} to '{result.get('new_status', new_status)}'.\n"
        f"Link: {JIRA_WEB_URL}/browse/{issue_key}"
    )


# ─── Tool 5: Lookup User ─────────────────────────────────────────────────────

@tool
def lookup_jira_user(name_or_email: str) -> str:
    """
    Find a Jira user's account ID by their name or email address.

    Use this BEFORE adding comments with @mentions or reassigning tickets.
    The account ID (e.g. "712020:27a3f2fe-...") is required for Jira @mentions
    and assignments — display names alone won't work.

    Args:
        name_or_email: The person's display name (e.g. "Mohamed Belkahla") or
                       their email address.

    Returns:
        The user's account ID and display name, or a not-found message.
    """
    result = _lookup_user(name_or_email)

    if result.get("error"):
        return f"User lookup failed for '{name_or_email}': {result.get('message', 'Unknown error')}"

    users = result.get("users", [])
    if not users:
        return f"No Jira user found for '{name_or_email}'. Try a different name or email."

    if len(users) == 1:
        u = users[0]
        return f"Found: {u.get('displayName')} — account ID: {u.get('accountId')}"

    # Multiple matches
    lines = [f"Multiple users found for '{name_or_email}':"]
    for u in users[:5]:
        lines.append(f"  • {u.get('displayName')} — {u.get('accountId')}")
    return "\n".join(lines)
