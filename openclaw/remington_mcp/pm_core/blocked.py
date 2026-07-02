"""Blocked-ticket analysis — pure compute layer.

Ported from ``scripts/core/blocked_ticket_analyzer.py``. Runs the PM decision
tree over every ticket in ``Blocked`` status and classifies each into one of the
analysis categories, marking the actionable ones. ``prior_state`` (from
STATE.md) provides the 48h per-(ticket, category) alert cooldown that the old
script kept in the ``blocked_sent_alerts`` SQLite table.

DECISION TREE (stops at first actionable finding), preserved faithfully:
  1. No "is blocked by" link            → no_link (PM hygiene, actionable)
  2. A blocking ticket is resolved       → blocker_resolved (actionable)
  3. All blockers themselves Blocked     → cascading_block (digest only)
  4. Otherwise legitimately blocked      → legitimately_blocked (digest only)

DROPPED / CHANGED:
  * Slack posting + digest posting (``post_to_slack``) — agent's job.
  * dashboard_db writes (``save_analyses_to_db``, ``save_to_active_violations``).
  * SQLite dedup (``should_send_alert``) → ``prior_state`` in/out.
  * Slack-mention resolution (``resolve_mention`` / ``get_pm_mention``) — the
    old code needed src.team_roster; here we emit plain display names + account
    IDs and let the agent resolve mentions. See TODO(port) in ``analyze_ticket``.
  * Step-3 Claude Haiku comment triage — the analyzer no longer makes its own
    LLM call. Legitimately-blocked tickets are returned WITH their recent
    comments attached so the agent (itself an LLM) can triage. See TODO(port).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL
from trinity.jira import get_jira_issue

from ._dates import jira_project_clause, now_utc, parse_jira_datetime, hours_since

# Statuses that mean the blocking ticket's work is effectively done.
BLOCKER_RESOLVED_STATUSES = {
    "Done", "Closed", "Complete", "Cancelled", "Released",
    "Pending Approval", "Ready For QA",
}

ANALYSIS_CATEGORIES = {
    "no_link": "No Blocking Link",
    "blocker_resolved": "Blocker Resolved — Ready to Resume",
    "cascading_block": "Cascading Block",
    "legitimately_blocked": "Legitimately Blocked",
}

# Which categories are actionable (were Slack-alerted in the original).
_ACTIONABLE = {"no_link", "blocker_resolved"}

ALERT_COOLDOWN_HOURS = 48


# ── Jira fetching (raw REST via trinity.base — search_jira does not expose
#    issuelinks or comment bodies) ─────────────────────────────────────────────

def _fetch_blocked_tickets(cfg) -> List[Dict]:
    clause = jira_project_clause(cfg.project_key)
    try:
        resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json={
                "jql": f'{clause} AND status = "Blocked" AND resolution is EMPTY '
                       f"ORDER BY updated ASC",
                "fields": ["summary", "status", "assignee", "updated", "issuelinks"],
                "maxResults": 100,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("issues", [])
    except Exception:
        return []


def _fetch_comments(key: str) -> List[Dict]:
    """Fetch the last few comments as plain text (for agent triage)."""
    try:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/comment",
            headers=get_jira_auth_headers(),
            params={"maxResults": 8, "orderBy": "-created"},
            timeout=15,
        )
        if resp.status_code == 200:
            out = []
            for c in resp.json().get("comments", []):
                out.append({
                    "author": (c.get("author") or {}).get("displayName", "Unknown"),
                    "date": (c.get("created") or "")[:10],
                    "text": _adf_text(c.get("body")),
                })
            return out
    except Exception:
        pass
    return []


def _adf_text(adf: Any) -> str:
    """Recursively extract plain text from Atlassian Document Format."""
    if not adf:
        return ""
    if isinstance(adf, str):
        return adf
    if isinstance(adf, dict):
        if adf.get("type") == "text":
            return adf.get("text", "")
        parts = [_adf_text(item) for item in adf.get("content", [])]
        return " ".join(p for p in parts if p).strip()
    return ""


def _blocker_status(key: str) -> Optional[Dict]:
    """Look up a blocking ticket's status/summary/assignee via trinity."""
    issue = get_jira_issue(key, fields=["summary", "status", "assignee"])
    if issue.get("error"):
        return None
    return {
        "status": issue.get("status"),
        "summary": issue.get("summary") or "",
        "assignee": (issue.get("assignee") or {}).get("name", "Unassigned"),
    }


# ── Decision tree ─────────────────────────────────────────────────────────────

def analyze_ticket(cfg, issue: Dict) -> Dict[str, Any]:
    """Run the PM decision tree for one blocked ticket; return a record.

    NOTE: unlike the original this returns plain display names + account IDs
    (``assignee``, ``assignee_account_id``) and does NOT build Slack-mention
    strings. TODO(port): the agent resolves names → Slack mentions and composes
    the actual alert text; ``alert_target`` tells it who to tag.
    """
    key = issue["key"]
    fields = issue["fields"]
    summary = fields.get("summary", "")
    assignee_data = fields.get("assignee") or {}
    assignee = assignee_data.get("displayName", "Unassigned")
    assignee_account_id = assignee_data.get("accountId")
    link = f"{cfg.browse_base}/{key}"
    issue_links = fields.get("issuelinks", [])

    base = {
        "key": key,
        "summary": summary,
        "assignee": assignee,
        "assignee_account_id": assignee_account_id,
        "link": link,
        "analyzed_at": now_utc().isoformat(),
        "needs_alert": False,
        "blocking_tickets": [],
    }

    # STEP 1 — must have an "is blocked by" (inward) link.
    blocking_links = [l for l in issue_links if l.get("inwardIssue")]
    if not blocking_links:
        return {
            **base,
            "category": "no_link",
            "needs_alert": True,
            "alert_target": "pm",  # Jira hygiene is on the PM, not the dev
            "action": f"PM to follow up with {assignee}: add blocking link or update status",
        }

    # STEP 2 — status of each blocking ticket.
    blocking_info: List[Dict] = []
    resolved_blockers: List[Dict] = []
    cascading_blockers: List[Dict] = []

    for link_obj in blocking_links:
        blocker_key = link_obj["inwardIssue"]["key"]
        status_from_link = link_obj["inwardIssue"]["fields"]["status"]["name"]
        detail = _blocker_status(blocker_key)
        blocker_status = detail["status"] if detail else status_from_link
        info = {
            "key": blocker_key,
            "status": blocker_status,
            "summary": (detail["summary"][:60] if detail else ""),
            "assignee": detail["assignee"] if detail else "Unknown",
            "link": f"{cfg.browse_base}/{blocker_key}",
        }
        blocking_info.append(info)
        if blocker_status in BLOCKER_RESOLVED_STATUSES:
            resolved_blockers.append(info)
        elif blocker_status == "Blocked":
            cascading_blockers.append(info)

    if resolved_blockers:
        blocker_list = ", ".join(f"{b['key']} ({b['status']})" for b in resolved_blockers)
        return {
            **base,
            "category": "blocker_resolved",
            "needs_alert": True,
            "blocking_tickets": blocking_info,
            "alert_target": assignee,
            "action": f"Blocking ticket {blocker_list} may be resolved — verify and resume development",
        }

    non_cascading = [b for b in blocking_info if b not in cascading_blockers]
    if cascading_blockers and not non_cascading:
        blocker_list = ", ".join(b["key"] for b in cascading_blockers)
        return {
            **base,
            "category": "cascading_block",
            "needs_alert": False,  # digest only
            "blocking_tickets": blocking_info,
            "action": f"Cascading block via {blocker_list} — investigate root blocker",
        }

    # STEP 3 — legitimately blocked. Attach comments for the agent to triage.
    # TODO(port): the original ran a Claude Haiku call here to detect a pending
    # response/action in the thread and, if found, re-categorised as
    # 'response_needed' (actionable, tagging who_to_tag). That LLM triage is now
    # the agent's responsibility — we surface `comments` so it can do it.
    comments = _fetch_comments(key)
    blocker_desc = ", ".join(f"{b['key']} ({b['status']})" for b in blocking_info)
    return {
        **base,
        "category": "legitimately_blocked",
        "needs_alert": False,
        "blocking_tickets": blocking_info,
        "comments": comments,
        "action": f"Waiting on {blocker_desc}",
    }


def analyze_blocked_tickets(cfg, prior_state: Optional[Dict] = None) -> Dict[str, Any]:
    """Analyze every Blocked ticket and decide which need a fresh alert.

    Args:
        cfg: PMConfig.
        prior_state: dict keyed by ``"KEY::category"`` → {"last_alerted_at": iso}.
            Provides the 48h alert cooldown.

    Returns:
        {
          "tickets": [ <analysis record per ticket, see analyze_ticket> ],
          "by_category": { category: [keys...] },
          "alerts_to_send": [ <actionable records past cooldown> ],
          "state": { "KEY::category": {"last_alerted_at": iso} },  # persist this
          "summary": {"total": int, "actionable": int},
        }
    """
    prior = prior_state or {}
    issues = _fetch_blocked_tickets(cfg)
    records = [analyze_ticket(cfg, issue) for issue in issues]

    now = now_utc().isoformat()
    alerts_to_send: List[Dict] = []
    new_state: Dict[str, Dict] = {}
    by_category: Dict[str, List[str]] = {}

    for r in records:
        by_category.setdefault(r["category"], []).append(r["key"])
        if not r.get("needs_alert"):
            continue
        dedup_key = f"{r['key']}::{r['category']}"
        prev = prior.get(dedup_key)
        last = parse_jira_datetime(prev.get("last_alerted_at")) if prev else None
        if last is None or hours_since(last) >= ALERT_COOLDOWN_HOURS:
            alerts_to_send.append(r)
            new_state[dedup_key] = {"last_alerted_at": now}
        else:
            new_state[dedup_key] = {"last_alerted_at": prev["last_alerted_at"]}

    return {
        "tickets": records,
        "by_category": by_category,
        "alerts_to_send": alerts_to_send,
        "state": new_state,
        "summary": {
            "total": len(records),
            "actionable": sum(1 for r in records if r.get("needs_alert")),
        },
    }
