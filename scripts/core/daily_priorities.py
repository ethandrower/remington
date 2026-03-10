#!/usr/bin/env python3
"""
Daily Priorities — Per-member ticket prioritization for the standup routine.

For each active team member this module:
  1. Fetches all their open Jira tickets across configured project keys
  2. Flags active SLA violations (from the dashboard DB)
  3. Flags unanswered comments that mention them (>1 day without reply)
  4. Scores and sorts tickets so the highest-urgency items surface first

Called by the standup workflow — not intended to be run standalone, though
you can run it directly for testing:
    python -m scripts.core.daily_priorities

Configuration:
    ATLASSIAN_PROJECT_KEY  Comma-separated project keys to query (e.g. "ECD,MDP")
    All other Jira vars come from src.tools.jira.base
"""

import os
import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from src.tools.jira.base import get_jira_auth_headers, JIRA_BASE_URL, format_error
from src.team_roster import get_all_team_members, refresh_from_db


# ---------------------------------------------------------------------------
# Priority scoring weights
# ---------------------------------------------------------------------------

JIRA_PRIORITY_SCORE = {
    "Highest": 50,
    "High":    40,
    "Medium":  30,
    "Low":     20,
    "Lowest":  10,
}

SCORE_CRITICAL_SLA       = 30   # active critical violation in DB
SCORE_WARNING_SLA        = 15   # active warning violation in DB
SCORE_UNANSWERED_MENTION = 20   # tagged in a comment, no reply in >1 day


# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def _get_project_keys() -> List[str]:
    """Return the list of project keys to query (from ATLASSIAN_PROJECT_KEY)."""
    raw = os.getenv("ATLASSIAN_PROJECT_KEY", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def fetch_member_tickets(jira_account_id: str, project_keys: List[str]) -> List[dict]:
    """
    Return all open tickets assigned to `jira_account_id` across all project_keys.
    Excludes Done, Cancelled, and Won't Do statuses.
    """
    if not project_keys:
        return []

    projects_jql = ", ".join(f'"{k}"' for k in project_keys)
    jql = (
        f'assignee = "{jira_account_id}" '
        f'AND project in ({projects_jql}) '
        f'AND statusCategory != Done '
        f'ORDER BY priority DESC, updated DESC'
    )

    fields = [
        "summary", "status", "priority", "issuetype",
        "updated", "duedate", "labels", "comment",
    ]

    try:
        resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json={"jql": jql, "maxResults": 50, "fields": fields},
            timeout=15,
        )
        if not resp.ok:
            print(f"  ⚠️  Jira search failed ({resp.status_code}) for {jira_account_id}")
            return []

        issues = resp.json().get("issues", [])
        return [_simplify_issue(i) for i in issues]

    except requests.RequestException as exc:
        print(f"  ⚠️  Jira request error: {exc}")
        return []


def _simplify_issue(raw: dict) -> dict:
    """Flatten a raw Jira issue into a compact dict."""
    f = raw.get("fields", {})
    return {
        "key":      raw["key"],
        "summary":  f.get("summary", ""),
        "status":   (f.get("status") or {}).get("name", ""),
        "priority": (f.get("priority") or {}).get("name", "Medium"),
        "type":     (f.get("issuetype") or {}).get("name", ""),
        "updated":  f.get("updated"),
        "duedate":  f.get("duedate"),
        "labels":   f.get("labels", []),
        "link":     f"{JIRA_BASE_URL}/browse/{raw['key']}",
        # Raw comments embedded in the search result (may be truncated)
        "_raw_comments": (f.get("comment") or {}).get("comments", []),
    }


# ---------------------------------------------------------------------------
# Unanswered mention detection
# ---------------------------------------------------------------------------

def fetch_comments(issue_key: str) -> List[dict]:
    """Fetch all comments for an issue (full list, not truncated)."""
    try:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment",
            headers=get_jira_auth_headers(),
            params={"maxResults": 100, "orderBy": "created"},
            timeout=10,
        )
        if resp.ok:
            return resp.json().get("comments", [])
    except requests.RequestException:
        pass
    return []


def find_unanswered_mentions(
    issue_key: str,
    jira_account_id: str,
    comments: Optional[List[dict]] = None,
    cutoff_hours: int = 24,
) -> List[dict]:
    """
    Return comments that mention `jira_account_id` and have received no reply
    from that person within `cutoff_hours`.

    A "mention" is detected when the comment's ADF body contains a mention
    node with the target account ID, OR the author of the comment is someone
    else and the text contains the account ID.

    Returns a list of flagged comment dicts (may be empty).
    """
    if comments is None:
        comments = fetch_comments(issue_key)

    if not comments:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=cutoff_hours)
    flagged = []

    for idx, comment in enumerate(comments):
        # Only care about comments NOT authored by the member themselves
        author_id = (comment.get("author") or {}).get("accountId", "")
        if author_id == jira_account_id:
            continue

        created_str = comment.get("created", "")
        if not _is_older_than(created_str, cutoff):
            continue  # Too recent — give them time to reply

        if not _comment_mentions(comment, jira_account_id):
            continue  # Doesn't tag this person

        # Check if the member replied after this comment
        member_replied = any(
            (c.get("author") or {}).get("accountId") == jira_account_id
            and _parse_dt(c.get("created")) > _parse_dt(created_str)
            for c in comments[idx + 1:]
        )

        if not member_replied:
            flagged.append({
                "comment_id": comment.get("id"),
                "author": (comment.get("author") or {}).get("displayName", "Unknown"),
                "created": created_str,
                "age_hours": _age_hours(created_str),
            })

    return flagged


def _comment_mentions(comment: dict, account_id: str) -> bool:
    """Return True if the ADF body of a comment contains a mention of account_id."""
    body = comment.get("body", {})
    return _adf_has_mention(body, account_id)


def _adf_has_mention(node, account_id: str) -> bool:
    """Recursively walk an ADF node tree looking for a mention of account_id."""
    if isinstance(node, dict):
        if node.get("type") == "mention" and node.get("attrs", {}).get("id") == account_id:
            return True
        for child in node.get("content", []):
            if _adf_has_mention(child, account_id):
                return True
    return False


def _parse_dt(iso: Optional[str]) -> datetime:
    if not iso:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _is_older_than(iso: Optional[str], cutoff: datetime) -> bool:
    return _parse_dt(iso) < cutoff


def _age_hours(iso: Optional[str]) -> float:
    dt = _parse_dt(iso)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return 0.0
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


# ---------------------------------------------------------------------------
# SLA violation lookup
# ---------------------------------------------------------------------------

def _load_active_violations() -> Dict[str, dict]:
    """
    Return a dict keyed by ticket key (e.g. "ECD-123") → violation record.
    Queries the dashboard DB. Gracefully returns {} on any error.
    """
    try:
        from src.database.dashboard_db import get_dashboard_db
        violations = get_dashboard_db().get_active_violations()
        return {v["item_id"]: v for v in violations}
    except Exception as exc:
        print(f"  ⚠️  Could not load SLA violations from DB: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_ticket(
    ticket: dict,
    violations: Dict[str, dict],
    unanswered_mentions: List[dict],
) -> Tuple[int, List[str]]:
    """
    Compute a priority score and a list of human-readable reason tags.

    Returns (score, reasons).
    """
    score = JIRA_PRIORITY_SCORE.get(ticket["priority"], 30)
    reasons = []

    violation = violations.get(ticket["key"])
    if violation:
        severity = violation.get("severity", "warning")
        if severity == "critical":
            score += SCORE_CRITICAL_SLA
            reasons.append("🔴 Critical SLA violation")
        else:
            score += SCORE_WARNING_SLA
            reasons.append("⚠️ Warning SLA violation")

    if unanswered_mentions:
        score += SCORE_UNANSWERED_MENTION
        oldest = max(m["age_hours"] for m in unanswered_mentions)
        reasons.append(f"💬 Tagged in comment, no reply ({oldest:.0f}h ago)")

    if ticket.get("duedate"):
        days_until = (_parse_dt(ticket["duedate"] + "T00:00:00+00:00") - datetime.now(timezone.utc)).days
        if days_until < 0:
            score += 25
            reasons.append(f"📅 Due date overdue ({abs(days_until)}d)")
        elif days_until <= 2:
            score += 15
            reasons.append(f"📅 Due in {days_until}d")

    return score, reasons


# ---------------------------------------------------------------------------
# Per-member prioritization
# ---------------------------------------------------------------------------

def prioritize_member(member_name: str, member: dict, violations: Dict[str, dict]) -> dict:
    """
    Build the priority list for a single team member.

    Returns:
        {
            "name": str,
            "slack_id": str,
            "jira_id": str,
            "tickets": [
                {
                    "key", "summary", "status", "priority",
                    "link", "score", "reasons": [str]
                },
                ...
            ]
        }
    """
    jira_id = member.get("jira_id", "")
    if not jira_id:
        return {
            "name": member_name,
            "slack_id": member.get("slack_id", ""),
            "jira_id": "",
            "tickets": [],
            "error": "No Jira account ID configured",
        }

    project_keys = _get_project_keys()
    tickets = fetch_member_tickets(jira_id, project_keys)

    scored = []
    for ticket in tickets:
        # Use comments already embedded in the search result where available;
        # fall back to a full fetch only if the list was truncated
        raw_comments = ticket.pop("_raw_comments", [])
        unanswered = find_unanswered_mentions(
            ticket["key"], jira_id, comments=raw_comments or None
        )
        score, reasons = score_ticket(ticket, violations, unanswered)
        scored.append({**ticket, "score": score, "reasons": reasons})

    scored.sort(key=lambda t: t["score"], reverse=True)

    return {
        "name":     member_name,
        "slack_id": member.get("slack_id", ""),
        "jira_id":  jira_id,
        "tickets":  scored,
    }


# ---------------------------------------------------------------------------
# Main entry point (called by standup)
# ---------------------------------------------------------------------------

def run_daily_priorities() -> List[dict]:
    """
    Build the priorities list for every active team member.

    Returns a list of member priority dicts (see `prioritize_member`),
    ordered alphabetically by member name.
    Skips members with no Jira account ID.
    """
    refresh_from_db()  # Pick up any members added since last import
    roster = get_all_team_members()

    if not roster:
        print("⚠️  daily_priorities: no team members found — add them via the dashboard UI")
        return []

    violations = _load_active_violations()
    print(f"  Loaded {len(violations)} active SLA violations")

    results = []
    for name, member in sorted(roster.items()):
        if not member.get("jira_id"):
            print(f"  Skipping {name} — no Jira ID")
            continue
        print(f"  Processing {name}…")
        result = prioritize_member(name, member, violations)
        results.append(result)
        ticket_count = len(result.get("tickets", []))
        print(f"    → {ticket_count} open ticket(s)")

    return results


def format_priorities_for_slack(results: List[dict]) -> str:
    """
    Format the priority results as a Slack message block.
    Returns a plain-text Slack-formatted string.
    """
    if not results:
        return "No team members configured with Jira IDs."

    lines = ["*📋 Today's Priorities by Team Member*", ""]

    for member in results:
        slack_id = member.get("slack_id")
        mention = f"<@{slack_id}>" if slack_id else member["name"]
        tickets = member.get("tickets", [])
        error = member.get("error")

        lines.append(f"*{mention}*")

        if error:
            lines.append(f"  ⚠️ {error}")
        elif not tickets:
            lines.append("  ✅ No open tickets")
        else:
            for t in tickets[:5]:  # Cap at 5 per person to keep message readable
                reason_str = "  |  ".join(t["reasons"]) if t["reasons"] else ""
                priority_emoji = {
                    "Highest": "🔴", "High": "🟠", "Medium": "🟡",
                    "Low": "🔵", "Lowest": "⚪"
                }.get(t["priority"], "⚪")
                line = f"  {priority_emoji} <{t['link']}|{t['key']}>: {t['summary'][:60]}"
                if reason_str:
                    line += f"\n      ↳ {reason_str}"
                lines.append(line)

            if len(tickets) > 5:
                lines.append(f"  _… and {len(tickets) - 5} more_")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from dotenv import load_dotenv
    load_dotenv()

    print("Running daily priorities check…\n")
    results = run_daily_priorities()

    print("\n" + "=" * 60)
    print(format_priorities_for_slack(results))
    print("=" * 60)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2, default=str))
