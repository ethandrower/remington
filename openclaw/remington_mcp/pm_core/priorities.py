"""Daily per-member priorities — pure compute layer.

Ported from ``scripts/core/daily_priorities.py``. For each team member: fetch
their open tickets, flag active SLA violations + unanswered @mentions, then
score and sort so the most urgent surface first.

STATE / INPUTS CHANGED (was DB, now passed in):
  * The roster used to come from ``src.team_roster`` (DB). It is now a required
    ``roster`` argument — a list of {name, slack_id, jira_id} dicts.
  * Active SLA violations used to be read from the dashboard DB. They are now a
    ``violations`` argument keyed by ticket key (feed it ``sla.check_slas``'s
    output, i.e. STATE.md) so priorities stays DB-free.

DROPPED: the Slack-string formatter (``format_priorities_for_slack``) — the
agent renders. Structured data only.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL

from ._dates import jira_project_clause, parse_jira_datetime

JIRA_PRIORITY_SCORE = {
    "Highest": 50, "High": 40, "Medium": 30, "Low": 20, "Lowest": 10,
}
SCORE_CRITICAL_SLA = 30
SCORE_WARNING_SLA = 15
SCORE_UNANSWERED_MENTION = 20


# ── Jira fetching (raw REST — needs duedate + embedded comments, which
#    search_jira does not expose) ──────────────────────────────────────────────

def fetch_member_tickets(cfg, jira_account_id: str) -> List[dict]:
    """Open tickets assigned to a member across all configured projects."""
    keys = [k.strip() for k in (cfg.project_key or "").split(",") if k.strip()]
    if not keys:
        return []
    projects_jql = ", ".join(f'"{k}"' for k in keys)
    jql = (
        f'assignee = "{jira_account_id}" AND project in ({projects_jql}) '
        f"AND statusCategory != Done ORDER BY priority DESC, updated DESC"
    )
    fields = ["summary", "status", "priority", "issuetype", "updated",
              "duedate", "labels", "comment"]
    try:
        resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json={"jql": jql, "maxResults": 50, "fields": fields},
            timeout=15,
        )
        if not resp.ok:
            return []
        return [_simplify_issue(cfg, i) for i in resp.json().get("issues", [])]
    except requests.RequestException:
        return []


def _simplify_issue(cfg, raw: dict) -> dict:
    f = raw.get("fields", {})
    return {
        "key": raw["key"],
        "summary": f.get("summary", ""),
        "status": (f.get("status") or {}).get("name", ""),
        "priority": (f.get("priority") or {}).get("name", "Medium"),
        "type": (f.get("issuetype") or {}).get("name", ""),
        "updated": f.get("updated"),
        "duedate": f.get("duedate"),
        "labels": f.get("labels", []),
        "link": f"{cfg.browse_base}/{raw['key']}",
        "_raw_comments": (f.get("comment") or {}).get("comments", []),
    }


def _fetch_comments(issue_key: str) -> List[dict]:
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


# ── Unanswered @mention detection ────────────────────────────────────────────

def find_unanswered_mentions(
    issue_key: str,
    jira_account_id: str,
    comments: Optional[List[dict]] = None,
    cutoff_hours: int = 24,
) -> List[dict]:
    """Comments that @mention the member and have had no reply from them within
    ``cutoff_hours``. Needs the raw ADF body (mention nodes), so it relies on
    raw comment payloads rather than trinity's text-flattened comments."""
    if comments is None:
        comments = _fetch_comments(issue_key)
    if not comments:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=cutoff_hours)
    flagged = []
    for idx, comment in enumerate(comments):
        author_id = (comment.get("author") or {}).get("accountId", "")
        if author_id == jira_account_id:
            continue
        created_str = comment.get("created", "")
        created_dt = parse_jira_datetime(created_str)
        if not created_dt or created_dt >= cutoff:
            continue
        if not _adf_has_mention(comment.get("body", {}), jira_account_id):
            continue
        member_replied = any(
            (c.get("author") or {}).get("accountId") == jira_account_id
            and (parse_jira_datetime(c.get("created")) or datetime.min.replace(tzinfo=timezone.utc))
            > created_dt
            for c in comments[idx + 1:]
        )
        if not member_replied:
            flagged.append({
                "comment_id": comment.get("id"),
                "author": (comment.get("author") or {}).get("displayName", "Unknown"),
                "created": created_str,
                "age_hours": _age_hours(created_dt),
            })
    return flagged


def _adf_has_mention(node, account_id: str) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "mention" and node.get("attrs", {}).get("id") == account_id:
            return True
        for child in node.get("content", []):
            if _adf_has_mention(child, account_id):
                return True
    return False


def _age_hours(dt: Optional[datetime]) -> float:
    if not dt:
        return 0.0
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


# ── Scoring ──────────────────────────────────────────────────────────────────

def score_ticket(
    ticket: dict,
    violations: Dict[str, dict],
    unanswered_mentions: List[dict],
) -> Tuple[int, List[str]]:
    """Priority score + human-readable reason tags for one ticket."""
    score = JIRA_PRIORITY_SCORE.get(ticket["priority"], 30)
    reasons: List[str] = []

    violation = violations.get(ticket["key"])
    if violation:
        if violation.get("severity") == "critical":
            score += SCORE_CRITICAL_SLA
            reasons.append("Critical SLA violation")
        else:
            score += SCORE_WARNING_SLA
            reasons.append("Warning SLA violation")

    if unanswered_mentions:
        score += SCORE_UNANSWERED_MENTION
        oldest = max(m["age_hours"] for m in unanswered_mentions)
        reasons.append(f"Tagged in comment, no reply ({oldest:.0f}h ago)")

    if ticket.get("duedate"):
        due_dt = parse_jira_datetime(ticket["duedate"] + "T00:00:00+00:00")
        if due_dt:
            days_until = (due_dt - datetime.now(timezone.utc)).days
            if days_until < 0:
                score += 25
                reasons.append(f"Due date overdue ({abs(days_until)}d)")
            elif days_until <= 2:
                score += 15
                reasons.append(f"Due in {days_until}d")

    return score, reasons


def prioritize_member(cfg, member: dict, violations: Dict[str, dict]) -> dict:
    """Build the priority list for one member ({name, slack_id, jira_id})."""
    name = member.get("name", "")
    jira_id = member.get("jira_id", "")
    if not jira_id:
        return {"name": name, "slack_id": member.get("slack_id", ""), "jira_id": "",
                "tickets": [], "error": "No Jira account ID configured"}

    tickets = fetch_member_tickets(cfg, jira_id)
    scored = []
    for ticket in tickets:
        raw_comments = ticket.pop("_raw_comments", [])
        unanswered = find_unanswered_mentions(
            ticket["key"], jira_id, comments=raw_comments or None
        )
        score, reasons = score_ticket(ticket, violations, unanswered)
        scored.append({**ticket, "score": score, "reasons": reasons})
    scored.sort(key=lambda t: t["score"], reverse=True)

    return {"name": name, "slack_id": member.get("slack_id", ""),
            "jira_id": jira_id, "tickets": scored}


def build_daily_priorities(
    cfg,
    roster: List[dict],
    violations: Optional[Dict[str, dict]] = None,
) -> Dict[str, Any]:
    """Build prioritised ticket lists for every rostered member.

    Args:
        cfg: PMConfig.
        roster: list of {name, slack_id, jira_id} dicts (passed in — no DB).
        violations: dict keyed by ticket key → violation record (e.g. from
            ``sla.check_slas``). Optional; empty means no SLA boosts.

    Returns:
        {
          "members": [ {name, slack_id, jira_id,
                        tickets: [{key, summary, status, priority, link,
                                   score, reasons}], [error]} ],
          "violations_considered": int,
        }
    """
    violations = violations or {}
    members = []
    for member in sorted(roster, key=lambda m: m.get("name", "")):
        if not member.get("jira_id"):
            continue
        members.append(prioritize_member(cfg, member, violations))

    return {"members": members, "violations_considered": len(violations)}
