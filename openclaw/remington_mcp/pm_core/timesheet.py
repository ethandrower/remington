"""Weekly timesheet report — pure compute layer.

Ported from ``scripts/core/timesheet_report.py``. Pulls Jira worklogs for a
week, groups by developer, and returns a JSON-serialisable structure. No
expected-hours enforcement — devs are paid what they report; this is a clean
record for reconciliation.

DROPPED: Slack block rendering (``format_slack_report``), Slack posting, the
shared-DB persistence (``save_to_db``), and the JSON file snapshot
(``save_snapshot``). The agent formats/persists as needed.

No cross-run state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import requests

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL
from trinity.jira import search_jira, get_issue_worklogs, fmt_seconds

from ._dates import jira_project_clause, get_week_bounds


def _get_issue_extras(issue_key: str) -> tuple:
    """Fetch (timeoriginalestimate_seconds, duedate) in one raw call.

    search_jira does not expose these, so we hit the issue endpoint directly
    (still trinity auth). Ported from timesheet_report._get_issue_extras.
    """
    try:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            params={"fields": "timeoriginalestimate,duedate"},
            timeout=15,
        )
        if resp.status_code == 200:
            f = resp.json().get("fields", {})
            return f.get("timeoriginalestimate") or 0, f.get("duedate")
    except Exception:
        pass
    return 0, None


def fetch_timesheet_data(cfg, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
    """Fetch and group all worklogs for the project within the week.

    Returns a dict keyed by developer account_id → {name, total_seconds,
    issues: {KEY: {summary, status, estimate_seconds, due_date, logged_seconds,
    url, entries}}}.
    """
    clause = jira_project_clause(cfg.project_key)
    date_from = week_start.strftime("%Y-%m-%d")
    date_to = week_end.strftime("%Y-%m-%d")

    jql = (
        f'{clause} AND worklogDate >= "{date_from}" '
        f'AND worklogDate <= "{date_to}" ORDER BY updated DESC'
    )
    result = search_jira(
        jql, max_results=100,
        fields=["summary", "status", "assignee", "timeoriginalestimate", "timespent"],
    )
    if result.get("error"):
        raise RuntimeError(f"Jira search failed: {result.get('message')}")

    browse = cfg.browse_base
    developers: Dict[str, Any] = {}

    for issue in result.get("issues", []):
        key = issue["key"]
        summary = issue.get("summary") or ""
        status = issue.get("status") or "Unknown"

        wl_result = get_issue_worklogs(key, started_after=week_start, started_before=week_end)
        if wl_result.get("error"):
            continue
        worklogs = wl_result.get("worklogs", [])
        if not worklogs:
            continue

        estimate_seconds, due_date = _get_issue_extras(key)

        for wl in worklogs:
            author_id = wl["author_id"]
            dev = developers.setdefault(author_id, {
                "name": wl["author"], "total_seconds": 0, "issues": {},
            })
            dev["total_seconds"] += wl["time_spent_seconds"]
            issue_rec = dev["issues"].setdefault(key, {
                "summary": summary, "status": status,
                "estimate_seconds": estimate_seconds, "due_date": due_date,
                "logged_seconds": 0, "url": f"{browse}/{key}", "entries": [],
            })
            issue_rec["logged_seconds"] += wl["time_spent_seconds"]
            issue_rec["entries"].append(wl)

    return developers


def build_timesheet(cfg, week_offset: int = 0, current_week: bool = False) -> Dict[str, Any]:
    """Build the weekly timesheet report.

    Args:
        cfg: PMConfig (uses ``cfg.timezone`` for week bounds).
        week_offset: 0 = last completed week, 1 = two weeks ago, ...
        current_week: report on this week Mon → now instead.

    Returns:
        {
          "week_start": iso, "week_end": iso, "week_label": str,
          "developers": { account_id: {name, total_seconds, issues:{...}} },
          "team_total_seconds": int,
          "team_total_human": str,
        }
    """
    week_start, week_end = get_week_bounds(
        cfg.timezone, week_offset=week_offset, current_week=current_week
    )
    week_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

    developers = fetch_timesheet_data(cfg, week_start, week_end)
    team_total = sum(d["total_seconds"] for d in developers.values())

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "week_label": week_label,
        "developers": developers,
        "team_total_seconds": team_total,
        "team_total_human": fmt_seconds(team_total),
    }
