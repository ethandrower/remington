"""Remington's Atlassian + Bitbucket tool surface (MCP server).

Wraps the installed `trinity` package and exposes it as MCP tools that an OpenClaw
agent can load. This is the ONLY sanctioned Atlassian/Bitbucket path for Remington:
Jira, Confluence, and Bitbucket all flow through trinity's headless token auth.

Auth is handled entirely by trinity from the process environment
(ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN for Jira+Confluence, BITBUCKET_* for
Bitbucket). Nothing credential-related lives in this file.

Run (from the `openclaw/` dir, or with it on PYTHONPATH):
    python -m remington_mcp.trinity_mcp    # stdio transport
Register in the gateway's OpenClaw config as an MCP server named "trinity".

Write tools (add_comment, transition, create/update, PR comment/merge) are grouped
below and flagged. Remington gates writes via a propose->approve->execute standing
order at the agent layer; this server does not itself gate.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP

# --- trinity primitives -----------------------------------------------------
from trinity.jira import (
    search_jira,
    get_jira_issue,
    add_jira_comment,
    edit_jira_issue,
    transition_jira_issue,
    get_jira_transitions,
    lookup_jira_user,
    list_jira_projects,
    get_issue_worklogs,
    get_status_history,
    get_boards,
    get_sprints,
    get_active_sprint,
    get_sprint_issues,
    get_completed_sprint_issues,
)
from trinity.jira.create_issue import create_jira_issue
from trinity.confluence import (
    get_confluence_page,
    search_confluence,
    create_confluence_page,
    update_confluence_page,
    add_confluence_comment,
    list_space_pages,
)
from trinity.base.exceptions import (
    AuthenticationError,
    AtlassianAPIError,
    PermissionError as TrinityPermissionError,
)

try:  # Bitbucket is a class-based API; import defensively so Jira still works if BB env is absent
    from trinity.bitbucket import BitbucketAPI
    from trinity.base.auth import get_workspace, get_default_repo
except Exception:  # pragma: no cover
    BitbucketAPI = None  # type: ignore

    def get_workspace(*_a, **_k):  # type: ignore
        return None

    def get_default_repo(*_a, **_k):  # type: ignore
        return None


mcp = FastMCP("trinity")


# --- error boundary ---------------------------------------------------------
def _safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Turn trinity exceptions into structured, LLM-readable error dicts."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except AuthenticationError as e:
            return {"error": str(e), "type": "auth"}
        except TrinityPermissionError as e:
            return {"error": str(e), "type": "permission"}
        except AtlassianAPIError as e:
            return {"error": str(e), "type": "api"}
        except Exception as e:  # last-resort: never leak a stack trace to the agent
            return {"error": f"{type(e).__name__}: {e}", "type": "unexpected"}

    return wrapper


_bb_singleton = None


def _bb():
    global _bb_singleton
    if BitbucketAPI is None:
        raise AtlassianAPIError("Bitbucket support unavailable (BitbucketAPI import failed)")
    if _bb_singleton is None:
        _bb_singleton = BitbucketAPI()
    return _bb_singleton


def _resolve_repo(workspace: Optional[str], repo: Optional[str]) -> tuple[str, str]:
    ws = workspace or get_workspace()
    rp = repo or get_default_repo()
    if not ws or not rp:
        raise AtlassianAPIError(
            "Bitbucket workspace/repo not provided and no default configured "
            "(set via trinity config or pass workspace/repo)."
        )
    return ws, rp


# ===========================================================================
# JIRA — reads
# ===========================================================================
@mcp.tool()
@_safe
def jira_search(jql: str, max_results: int = 50, fields: Optional[list] = None) -> dict:
    """Run a JQL query and return matching Jira issues."""
    return search_jira(jql, max_results=max_results, fields=fields)


@mcp.tool()
@_safe
def jira_get_issue(
    issue_key: str, fields: Optional[list] = None, include_comments: bool = False
) -> dict:
    """Fetch a single Jira issue by key, optionally with its comments."""
    return get_jira_issue(issue_key, fields=fields, include_comments=include_comments)


@mcp.tool()
@_safe
def jira_get_transitions(issue_key: str) -> dict:
    """List the workflow transitions available for an issue (valid target statuses)."""
    return get_jira_transitions(issue_key)


@mcp.tool()
@_safe
def jira_lookup_user(query: str, max_results: int = 10) -> dict:
    """Look up Jira users by name/email to get accountIds for tagging."""
    return lookup_jira_user(query, max_results=max_results)


@mcp.tool()
@_safe
def jira_list_projects(search: Optional[str] = None, max_results: int = 50) -> dict:
    """List visible Jira projects (optionally filtered by a search string)."""
    return list_jira_projects(search=search, max_results=max_results)


@mcp.tool()
@_safe
def jira_get_worklogs(
    issue_key: str, started_after: Optional[str] = None, started_before: Optional[str] = None
) -> dict:
    """Get worklog entries for an issue. Dates are ISO-8601 strings (e.g. 2026-07-01)."""
    from datetime import datetime

    def _p(s: Optional[str]):
        return datetime.fromisoformat(s) if s else None

    return get_issue_worklogs(issue_key, started_after=_p(started_after), started_before=_p(started_before))


@mcp.tool()
@_safe
def jira_get_status_history(
    issue_key: str, target_status: Optional[str] = None, all_transitions: bool = False
) -> dict:
    """Get an issue's status-change history (e.g. when it entered a given status)."""
    return get_status_history(issue_key, target_status=target_status, all_transitions=all_transitions)


@mcp.tool()
@_safe
def jira_get_boards(
    project_key: Optional[str] = None, board_type: Optional[str] = None, max_results: int = 50
) -> dict:
    """List Jira Agile boards, optionally filtered by project or board type."""
    return get_boards(project_key=project_key, board_type=board_type, max_results=max_results)


@mcp.tool()
@_safe
def jira_get_sprints(board_id: int, state: Optional[str] = None, max_results: int = 50) -> dict:
    """List sprints on a board. state = active|future|closed."""
    return get_sprints(board_id, state=state, max_results=max_results)


@mcp.tool()
@_safe
def jira_get_active_sprint(board_id: int) -> dict:
    """Get the currently active sprint for a board."""
    return get_active_sprint(board_id)


@mcp.tool()
@_safe
def jira_get_sprint_issues(
    sprint_id: int,
    status: Optional[str] = None,
    issue_types: Optional[list] = None,
    max_results: int = 100,
) -> dict:
    """List issues in a sprint, optionally filtered by status or issue types."""
    return get_sprint_issues(sprint_id, status=status, issue_types=issue_types, max_results=max_results)


@mcp.tool()
@_safe
def jira_get_completed_sprint_issues(sprint_id: int, exclude_types: Optional[list] = None) -> dict:
    """List the completed (done) issues in a sprint — for velocity/burndown."""
    return get_completed_sprint_issues(sprint_id, exclude_types=exclude_types)


# ===========================================================================
# JIRA — writes  (propose -> approve -> execute at the agent layer)
# ===========================================================================
@mcp.tool()
@_safe
def jira_add_comment(issue_key: str, comment_text: str, mentions: Optional[list] = None) -> dict:
    """WRITE. Add a comment to an issue. `mentions` = list of accountIds to @-tag."""
    return add_jira_comment(issue_key, comment_text, mentions=mentions)


@mcp.tool()
@_safe
def jira_transition_issue(
    issue_key: str,
    transition_name: Optional[str] = None,
    transition_id: Optional[str] = None,
    comment: Optional[str] = None,
) -> dict:
    """WRITE. Move an issue to a new status by transition name or id."""
    return transition_jira_issue(
        issue_key, transition_name=transition_name, transition_id=transition_id, comment=comment
    )


@mcp.tool()
@_safe
def jira_edit_issue(issue_key: str, fields: dict) -> dict:
    """WRITE. Edit fields on an issue (summary, assignee, labels, priority, custom fields...)."""
    return edit_jira_issue(issue_key, **fields)


@mcp.tool()
@_safe
def jira_create_issue(
    project_key: str,
    issue_type: str,
    summary: str,
    description: Optional[str] = None,
    fields: Optional[dict] = None,
) -> dict:
    """WRITE. Create a Jira issue. `fields` carries any extra/custom fields."""
    return create_jira_issue(
        project_key=project_key,
        issue_type=issue_type,
        summary=summary,
        description=description,
        **(fields or {}),
    )


# ===========================================================================
# CONFLUENCE
# ===========================================================================
@mcp.tool()
@_safe
def confluence_get_page(page_id: str, include_body: bool = True) -> dict:
    """Fetch a Confluence page by id (with body by default)."""
    return get_confluence_page(page_id, include_body=include_body)


@mcp.tool()
@_safe
def confluence_search(
    query: str, space_key: Optional[str] = None, content_type: Optional[str] = None, max_results: int = 25
) -> dict:
    """Search Confluence (CQL text). Optionally scope to a space or content type."""
    return search_confluence(query, space_key=space_key, content_type=content_type, max_results=max_results)


@mcp.tool()
@_safe
def confluence_list_space_pages(space_key: str, max_results: int = 50) -> dict:
    """List pages in a Confluence space."""
    return list_space_pages(space_key, max_results=max_results)


@mcp.tool()
@_safe
def confluence_create_page(
    space_key: str, title: str, body: str, parent_id: Optional[str] = None, body_format: str = "storage"
) -> dict:
    """WRITE. Create a Confluence page. body_format = storage|wiki|editor."""
    return create_confluence_page(space_key, title, body, parent_id=parent_id, body_format=body_format)


@mcp.tool()
@_safe
def confluence_update_page(
    page_id: str,
    title: Optional[str] = None,
    body: Optional[str] = None,
    body_format: str = "storage",
    version_comment: Optional[str] = None,
) -> dict:
    """WRITE. Update a Confluence page's title/body."""
    return update_confluence_page(
        page_id, title=title, body=body, body_format=body_format, version_comment=version_comment
    )


@mcp.tool()
@_safe
def confluence_add_comment(page_id: str, text: str, reply_to: Optional[str] = None) -> dict:
    """WRITE. Add a footer comment to a Confluence page (or reply to a comment)."""
    return add_confluence_comment(page_id, text, reply_to=reply_to)


# ===========================================================================
# BITBUCKET  (workspace/repo default to trinity config when omitted)
# ===========================================================================
@mcp.tool()
@_safe
def bitbucket_list_pull_requests(
    state: str = "OPEN", workspace: Optional[str] = None, repo: Optional[str] = None
) -> list:
    """List pull requests in a repo. state = OPEN|MERGED|DECLINED|SUPERSEDED."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().list_pull_requests(ws, rp, state=state)


@mcp.tool()
@_safe
def bitbucket_get_pull_request(
    pr_id: int, workspace: Optional[str] = None, repo: Optional[str] = None
) -> dict:
    """Get a single pull request by id."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().get_pull_request(ws, rp, pr_id)


@mcp.tool()
@_safe
def bitbucket_get_pr_comments(
    pr_id: int, workspace: Optional[str] = None, repo: Optional[str] = None
) -> list:
    """Get the comments on a pull request."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().get_comments(ws, rp, pr_id)


@mcp.tool()
@_safe
def bitbucket_get_pr_diff(
    pr_id: int, workspace: Optional[str] = None, repo: Optional[str] = None
) -> str:
    """Get the unified diff for a pull request (for code review)."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().get_diff(ws, rp, pr_id)


@mcp.tool()
@_safe
def bitbucket_get_pr_activity(
    pr_id: int, workspace: Optional[str] = None, repo: Optional[str] = None
) -> list:
    """Get a PR's activity feed (approvals, updates, comments) — for staleness/turnaround SLAs."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().get_activity(ws, rp, pr_id)


@mcp.tool()
@_safe
def bitbucket_add_pr_comment(
    pr_id: int, message: str, workspace: Optional[str] = None, repo: Optional[str] = None
) -> dict:
    """WRITE. Add a comment to a pull request."""
    ws, rp = _resolve_repo(workspace, repo)
    return _bb().add_comment(ws, rp, pr_id, message)


if __name__ == "__main__":
    mcp.run()
