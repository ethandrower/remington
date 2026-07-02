"""PM self-audit — pure compute + trinity data fetch.

Ports two things into one monolith-free module:
  * The Jira fetch layer from ``scripts/core/pm_audit.py`` (sprint tickets,
    comments, changelogs) — re-pointed at trinity auth (raw REST is required
    because search_jira does not expose customfield_10020 / timeoriginalestimate
    / reporter, and there is no trinity changelog helper).
  * The pure compute layer that lived in the monolith at
    ``src/dashboard/pm_audit_compute.py`` — copied here verbatim (it had no Jira
    or Flask deps) so pm_core has zero monolith imports. Six metric groups
    (approval velocity, comment engagement, responsiveness, grooming, status
    transitions, scope management, blocker response) + A/B/C/D grading.

CHANGED / DROPPED:
  * ``resolve_pm`` hit the dashboard DB (role='pm'). Removed — the PM identity
    (``pm_account_id`` + ``pm_names``) is now passed in from config/STATE.
  * DB snapshot persistence (``save_snapshot``) — dropped; result is returned.
  * Business-hours window now comes from ``cfg`` (was hardcoded 9–17).

No cross-run state.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL

from ._dates import jira_project_clause, parse_jira_datetime, business_hours_between

# ── Grading thresholds (ported verbatim) ─────────────────────────────────────

DEFAULT_THRESHOLDS = {
    "approval": {"A": {"avg_hours": 8, "backlog": 2}, "B": {"avg_hours": 24, "backlog": 5},
                 "C": {"avg_hours": 48, "backlog": 8}},
    "engagement": {"A": {"ratio": 0.80}, "B": {"ratio": 0.60}, "C": {"ratio": 0.40}},
    "responsiveness": {"A": {"avg_hours": 4, "waiting": 2}, "B": {"avg_hours": 12, "waiting": 5},
                       "C": {"avg_hours": 24, "waiting": 8}},
    "grooming": {"A": {"estimation_pct": 90}, "B": {"estimation_pct": 75}, "C": {"estimation_pct": 50}},
    "transitions": {"A": {"min_transitions": 20, "min_reopens": 3},
                    "B": {"min_transitions": 10, "min_reopens": 1},
                    "C": {"min_transitions": 5, "min_reopens": 0}},
    "blocker_response": {"A": {"avg_hours": 4, "no_engagement": 0},
                         "B": {"avg_hours": 12, "no_engagement": 1},
                         "C": {"avg_hours": 24, "no_engagement": 3}},
}
GRADE_WEIGHTS = {"approval": 0.25, "engagement": 0.20, "responsiveness": 0.20,
                 "grooming": 0.10, "transitions": 0.10, "blocker_response": 0.15}
GRADE_NUMERIC = {"A": 4, "B": 3, "C": 2, "D": 1}

# Business-hours window — set per-run from cfg by run_pm_audit().
_BH_START = 9
_BH_END = 17
_HOLIDAYS: tuple = ()


def _business_hours_between(start: Optional[datetime], end: Optional[datetime]) -> float:
    return business_hours_between(start, end, _BH_START, _BH_END, _HOLIDAYS)


def _pm_matches(author_id, author_name, pm_account_id, pm_names) -> bool:
    if author_id and author_id == pm_account_id:
        return True
    if author_name:
        nl = author_name.lower()
        return any(n.lower() == nl for n in pm_names)
    return False


# ── Metric group computers (ported verbatim, _parse_dt → parse_jira_datetime) ─

def _compute_approval_velocity(tickets, changelogs, pm_account_id, pm_names):
    approval_durations, current_backlog, detail = [], [], []
    approvals_completed = 0
    for ticket in tickets:
        key = ticket.get("key", "")
        status = ticket.get("status", "")
        entered_pa, ticket_pa_hours = None, 0.0
        for entry in changelogs.get(key, []):
            for item in entry.get("items", []):
                if item.get("field") != "status":
                    continue
                to_str = (item.get("toString") or "").strip()
                from_str = (item.get("fromString") or "").strip()
                ts = parse_jira_datetime(entry.get("created"))
                if to_str == "Pending Approval" and entered_pa is None:
                    entered_pa = ts
                elif from_str == "Pending Approval" and entered_pa and ts:
                    hours = _business_hours_between(entered_pa, ts)
                    ticket_pa_hours += hours
                    approval_durations.append(hours)
                    if _pm_matches(entry.get("author", {}).get("accountId"),
                                   entry.get("author", {}).get("displayName"),
                                   pm_account_id, pm_names):
                        approvals_completed += 1
                    entered_pa = None
        if status == "Pending Approval":
            current_backlog.append(key)
            if entered_pa:
                hours = _business_hours_between(entered_pa, datetime.utcnow())
                ticket_pa_hours += hours
                approval_durations.append(hours)
        if ticket_pa_hours > 0 or status == "Pending Approval":
            detail.append({"key": key, "summary": ticket.get("summary", ""),
                           "pa_hours": round(ticket_pa_hours, 1),
                           "currently_pending": status == "Pending Approval"})
    avg_hours = round(sum(approval_durations) / len(approval_durations), 1) if approval_durations else 0.0
    return {"avg_pending_approval_hours": avg_hours,
            "pending_approval_backlog": len(current_backlog),
            "approvals_completed": approvals_completed,
            "detail": sorted(detail, key=lambda d: d["pa_hours"], reverse=True)}


def _compute_comment_activity(tickets, comments, pm_account_id, pm_names):
    total_pm_comments = 0
    tickets_with_pm_comment, threads_waiting, response_times, detail = set(), [], [], []
    for ticket in tickets:
        key = ticket.get("key", "")
        ticket_comments = comments.get(key, [])
        if not ticket_comments:
            continue
        pm_comment_count, pm_commented, pending_non_pm = 0, False, None
        sorted_comments = sorted(ticket_comments, key=lambda c: c.get("created", ""))
        for c in sorted_comments:
            author_id = c.get("author", {}).get("accountId")
            author_name = c.get("author", {}).get("displayName")
            created = parse_jira_datetime(c.get("created"))
            if _pm_matches(author_id, author_name, pm_account_id, pm_names):
                pm_comment_count += 1
                pm_commented = True
                if pending_non_pm and created:
                    response_times.append(_business_hours_between(pending_non_pm, created))
                    pending_non_pm = None
            else:
                if pm_commented and created:
                    pending_non_pm = created
        total_pm_comments += pm_comment_count
        if pm_commented:
            tickets_with_pm_comment.add(key)
        if sorted_comments:
            last_c = sorted_comments[-1]
            if pm_commented and not _pm_matches(last_c.get("author", {}).get("accountId"),
                                                last_c.get("author", {}).get("displayName"),
                                                pm_account_id, pm_names):
                threads_waiting.append(key)
        detail.append({"key": key, "summary": ticket.get("summary", ""),
                       "pm_comments": pm_comment_count, "total_comments": len(ticket_comments),
                       "waiting_on_pm": key in threads_waiting,
                       "last_commenter": sorted_comments[-1].get("author", {}).get("displayName", "") if sorted_comments else ""})
    total_tickets = len(tickets)
    engagement_ratio = round(len(tickets_with_pm_comment) / total_tickets, 2) if total_tickets else 0.0
    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0.0
    return {"total_pm_comments": total_pm_comments, "tickets_engaged": len(tickets_with_pm_comment),
            "total_sprint_tickets": total_tickets, "engagement_ratio": engagement_ratio,
            "threads_waiting_on_pm": len(threads_waiting), "avg_pm_response_hours": avg_response,
            "detail": sorted(detail, key=lambda d: d["pm_comments"], reverse=True)}


def _compute_grooming(tickets, pm_account_id):
    created_by_pm, estimated, unestimated = [], 0, []
    for ticket in tickets:
        key = ticket.get("key", "")
        if ticket.get("reporter_id", "") == pm_account_id:
            created_by_pm.append(key)
        if ticket.get("original_estimate_seconds") and ticket["original_estimate_seconds"] > 0:
            estimated += 1
        else:
            unestimated.append({"key": key, "summary": ticket.get("summary", ""),
                                "assignee": ticket.get("assignee", ""), "status": ticket.get("status", "")})
    total = len(tickets)
    coverage = round(estimated / total * 100, 1) if total else 0.0
    return {"tickets_created_by_pm": len(created_by_pm), "estimation_coverage_pct": coverage,
            "unestimated_count": len(unestimated),
            "detail": {"created_tickets": created_by_pm, "unestimated_tickets": unestimated}}


def _compute_transitions(changelogs, pm_account_id, pm_names):
    BACKWARD = {"To Do", "Open", "Ready For Development", "In Development", "In Progress"}
    FORWARD = {"Done", "Closed", "Ready For QA", "Pending Approval", "Complete"}
    pm_transitions, reopens, breakdown, detail = 0, 0, {}, []
    for key, entries in changelogs.items():
        for entry in entries:
            if not _pm_matches(entry.get("author", {}).get("accountId"),
                               entry.get("author", {}).get("displayName"), pm_account_id, pm_names):
                continue
            for item in entry.get("items", []):
                if item.get("field") != "status":
                    continue
                from_str = (item.get("fromString") or "").strip()
                to_str = (item.get("toString") or "").strip()
                pm_transitions += 1
                breakdown[f"{from_str} -> {to_str}"] = breakdown.get(f"{from_str} -> {to_str}", 0) + 1
                is_reopen = from_str in FORWARD and to_str in BACKWARD
                if is_reopen:
                    reopens += 1
                detail.append({"key": key, "from": from_str, "to": to_str,
                               "timestamp": entry.get("created", ""), "is_reopen": is_reopen})
    detail.sort(key=lambda d: d["timestamp"], reverse=True)
    return {"transitions_by_pm": pm_transitions, "reopens_rejections": reopens,
            "breakdown": breakdown, "detail": detail}


def _compute_scope_management(tickets, changelogs, pm_account_id, pm_names, sprint_start=None):
    sprint_start_dt = parse_jira_datetime(sprint_start) if sprint_start else None
    added, removed = [], []
    for key, entries in changelogs.items():
        for entry in entries:
            entry_dt = parse_jira_datetime(entry.get("created"))
            for item in entry.get("items", []):
                if item.get("field") != "Sprint":
                    continue
                to_str = item.get("toString") or ""
                from_str = item.get("fromString") or ""
                if sprint_start_dt and entry_dt and entry_dt <= sprint_start_dt:
                    continue
                author_name = entry.get("author", {}).get("displayName", "")
                author_id = entry.get("author", {}).get("accountId", "")
                if to_str:
                    added.append({"key": key, "by": author_name, "by_id": author_id,
                                  "timestamp": entry.get("created", "")})
                if from_str and not to_str:
                    removed.append({"key": key, "by": author_name, "by_id": author_id,
                                    "timestamp": entry.get("created", "")})
    dev_hours: Dict[str, float] = {}
    for ticket in tickets:
        assignee = ticket.get("assignee_id") or ticket.get("assignee", "Unassigned")
        dev_hours[assignee] = dev_hours.get(assignee, 0) + (ticket.get("original_estimate_seconds") or 0) / 3600
    dev_hours.pop("Unassigned", None)
    dev_hours.pop("", None)
    if len(dev_hours) >= 2:
        values = list(dev_hours.values())
        mean = sum(values) / len(values)
        cv = round((sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5 / mean, 2) if mean > 0 else 0.0
    else:
        cv = 0.0
    return {"tickets_added_mid_sprint": len(added), "tickets_removed_mid_sprint": len(removed),
            "assignment_balance_cv": cv,
            "detail": {"added": added, "removed": removed, "dev_hours": dev_hours}}


def _compute_blocker_response(tickets, changelogs, comments, pm_account_id, pm_names):
    response_times, no_engagement, detail = [], [], []
    for ticket in tickets:
        key = ticket.get("key", "")
        blocked_at = None
        for entry in changelogs.get(key, []):
            for item in entry.get("items", []):
                if item.get("field") == "status" and (item.get("toString") or "").strip() == "Blocked":
                    blocked_at = parse_jira_datetime(entry.get("created"))
        if not blocked_at:
            continue
        first_pm_after = None
        for c in sorted(comments.get(key, []), key=lambda x: x.get("created", "")):
            c_time = parse_jira_datetime(c.get("created"))
            if not c_time or c_time <= blocked_at:
                continue
            if _pm_matches(c.get("author", {}).get("accountId"),
                           c.get("author", {}).get("displayName"), pm_account_id, pm_names):
                first_pm_after = c_time
                break
        if first_pm_after:
            hours = _business_hours_between(blocked_at, first_pm_after)
            response_times.append(hours)
            detail.append({"key": key, "summary": ticket.get("summary", ""),
                           "blocked_at": blocked_at.isoformat(),
                           "pm_responded_at": first_pm_after.isoformat(),
                           "response_hours": round(hours, 1)})
        else:
            hours_since = _business_hours_between(blocked_at, datetime.utcnow())
            if hours_since >= 24:
                no_engagement.append(key)
            detail.append({"key": key, "summary": ticket.get("summary", ""),
                           "blocked_at": blocked_at.isoformat(), "pm_responded_at": None,
                           "response_hours": None, "hours_since_blocked": round(hours_since, 1)})
    avg_hours = round(sum(response_times) / len(response_times), 1) if response_times else None
    return {"avg_blocked_to_pm_comment_hours": avg_hours,
            "blocked_no_pm_engagement": len(no_engagement), "detail": detail}


# ── Grading (ported verbatim) ────────────────────────────────────────────────

def _grade_letter(value, thresholds, metric, higher_is_better=False):
    for grade in ("A", "B", "C"):
        threshold = thresholds[grade].get(metric)
        if threshold is None:
            continue
        if higher_is_better:
            if value >= threshold:
                return grade
        elif value <= threshold:
            return grade
    return "D"


def _compute_grades(metrics, thresholds=None):
    t = thresholds or DEFAULT_THRESHOLDS
    grades = {}
    g1 = _grade_letter(metrics.get("avg_pending_approval_hours") or 0, t["approval"], "avg_hours")
    g2 = _grade_letter(metrics.get("pending_approval_backlog") or 0, t["approval"], "backlog")
    grades["approval"] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])
    grades["engagement"] = _grade_letter(metrics.get("engagement_ratio") or 0, t["engagement"], "ratio", True)
    g1 = _grade_letter(metrics.get("avg_pm_response_hours") or 0, t["responsiveness"], "avg_hours")
    g2 = _grade_letter(metrics.get("threads_waiting_on_pm") or 0, t["responsiveness"], "waiting")
    grades["responsiveness"] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])
    grades["grooming"] = _grade_letter(metrics.get("estimation_coverage_pct") or 0, t["grooming"], "estimation_pct", True)
    g1 = _grade_letter(metrics.get("transitions_by_pm") or 0, t["transitions"], "min_transitions", True)
    g2 = _grade_letter(metrics.get("reopens_rejections") or 0, t["transitions"], "min_reopens", True)
    grades["transitions"] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])
    avg_block = metrics.get("avg_blocked_to_pm_comment_hours")
    if avg_block is not None:
        g1 = _grade_letter(avg_block, t["blocker_response"], "avg_hours")
        g2 = _grade_letter(metrics.get("blocked_no_pm_engagement") or 0, t["blocker_response"], "no_engagement")
        grades["blocker_response"] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])
    else:
        grades["blocker_response"] = "A"
    total_w = total_score = 0.0
    for group, weight in GRADE_WEIGHTS.items():
        total_score += GRADE_NUMERIC[grades.get(group, "C")] * weight
        total_w += weight
    avg_score = total_score / total_w if total_w else 2.0
    grades["overall"] = "A" if avg_score >= 3.5 else "B" if avg_score >= 2.5 else "C" if avg_score >= 1.5 else "D"
    return grades


def compute_pm_audit(tickets, comments, changelogs, pm_account_id,
                     pm_names=None, sprint_meta=None, thresholds=None) -> Dict[str, Any]:
    """Compute the full PM self-audit from raw data (pure). See module docstring."""
    pm_names = pm_names or []
    sprint_meta = sprint_meta or {}
    approval = _compute_approval_velocity(tickets, changelogs, pm_account_id, pm_names)
    engagement = _compute_comment_activity(tickets, comments, pm_account_id, pm_names)
    grooming = _compute_grooming(tickets, pm_account_id)
    transitions = _compute_transitions(changelogs, pm_account_id, pm_names)
    scope = _compute_scope_management(tickets, changelogs, pm_account_id, pm_names,
                                      sprint_start=sprint_meta.get("start_date"))
    blocker = _compute_blocker_response(tickets, changelogs, comments, pm_account_id, pm_names)
    metrics = {
        **{k: v for k, v in approval.items() if k != "detail"},
        **{k: v for k, v in engagement.items() if k != "detail"},
        **{k: v for k, v in grooming.items() if k != "detail"},
        **{k: v for k, v in transitions.items() if k not in ("detail", "breakdown")},
        **{k: v for k, v in scope.items() if k != "detail"},
        **{k: v for k, v in blocker.items() if k != "detail"},
    }
    grades = _compute_grades(metrics, thresholds)
    return {
        "pm_account_id": pm_account_id,
        "pm_display_name": pm_names[0] if pm_names else "",
        "sprint_id": sprint_meta.get("sprint_id", ""),
        "sprint_name": sprint_meta.get("sprint_name", ""),
        "computed_at": datetime.utcnow().isoformat() + "Z",
        **metrics,
        "transition_breakdown": transitions.get("breakdown", {}),
        "overall_grade": grades["overall"],
        "grades": grades,
        "detail": {
            "approval": approval.get("detail", []),
            "engagement": engagement.get("detail", []),
            "grooming": grooming.get("detail", {}),
            "transitions": transitions.get("detail", []),
            "scope": scope.get("detail", {}),
            "blocker_response": blocker.get("detail", []),
        },
    }


# ── Jira fetch layer (raw REST via trinity.base) ─────────────────────────────

def _jira_get(url, params=None, timeout=20):
    try:
        resp = requests.get(url, headers=get_jira_auth_headers(), params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _jira_post(url, payload, timeout=30):
    try:
        resp = requests.post(url, headers=get_jira_auth_headers(), json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def fetch_sprint_tickets(cfg, sprint_id: Optional[str] = None) -> tuple:
    """Fetch sprint tickets + sprint meta. Returns (tickets, sprint_meta)."""
    clause = jira_project_clause(cfg.project_key)
    if sprint_id:
        jql = f"{clause} AND sprint = {sprint_id} AND issuetype not in subTaskIssueTypes()"
    else:
        jql = f"{clause} AND sprint in openSprints() AND issuetype not in subTaskIssueTypes()"

    all_issues, sprint_meta, next_token = [], {}, None
    while True:
        payload = {"jql": jql, "maxResults": 100,
                   "fields": ["summary", "status", "assignee", "reporter",
                              "timeoriginalestimate", "customfield_10020"]}
        if next_token:
            payload["nextPageToken"] = next_token
        data = _jira_post(f"{JIRA_BASE_URL}/rest/api/3/search/jql", payload)
        if not data:
            break
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if not sprint_meta and issues:
            sprints = issues[0].get("fields", {}).get("customfield_10020") or []
            active = [s for s in sprints if s.get("state") == "active"]
            if active:
                s = active[0]
                sprint_meta = {"sprint_id": str(s.get("id", "")), "sprint_name": s.get("name", ""),
                               "start_date": (s.get("startDate") or "")[:10],
                               "end_date": (s.get("endDate") or "")[:10]}
        if data.get("isLast", True):
            break
        next_token = data.get("nextPageToken")
        if not next_token:
            break

    tickets = []
    for issue in all_issues:
        f = issue.get("fields", {})
        tickets.append({
            "key": issue.get("key", ""),
            "summary": f.get("summary", ""),
            "status": (f.get("status") or {}).get("name", ""),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "assignee_id": (f.get("assignee") or {}).get("accountId", ""),
            "reporter_id": (f.get("reporter") or {}).get("accountId", ""),
            "original_estimate_seconds": f.get("timeoriginalestimate") or 0,
        })
    return tickets, sprint_meta


def fetch_comments(key: str) -> List[Dict]:
    data = _jira_get(f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/comment",
                     params={"maxResults": 100, "orderBy": "created"})
    return data.get("comments", []) if data else []


def fetch_changelog(key: str) -> List[Dict]:
    all_entries, start_at = [], 0
    while True:
        data = _jira_get(f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/changelog",
                         params={"maxResults": 100, "startAt": start_at})
        if not data:
            break
        values = data.get("values", [])
        all_entries.extend(values)
        if start_at + len(values) >= data.get("total", 0):
            break
        start_at += len(values)
    return all_entries


def fetch_all_comments_and_changelogs(ticket_keys: List[str], max_workers: int = 8) -> tuple:
    comments: Dict[str, List] = {}
    changelogs: Dict[str, List] = {}

    def _fetch_one(key):
        return key, fetch_comments(key), fetch_changelog(key)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, k): k for k in ticket_keys}
        for future in as_completed(futures):
            key, c, cl = future.result()
            comments[key] = c
            changelogs[key] = cl
    return comments, changelogs


def run_pm_audit(
    cfg,
    pm_account_id: str,
    pm_names: Optional[List[str]] = None,
    sprint_id: Optional[str] = None,
    thresholds: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run the full PM self-audit for a sprint.

    Args:
        cfg: PMConfig (business-hours window sourced from here).
        pm_account_id: Jira account ID of the PM (REQUIRED — no DB auto-detect).
        pm_names: display-name variants for changelog matching.
        sprint_id: specific sprint; active sprint if omitted.
        thresholds: optional custom grading thresholds.

    Returns:
        The compute_pm_audit result dict (metrics + grades + detail), or
        ``{"error": ...}`` if no PM id / no tickets.
    """
    global _BH_START, _BH_END, _HOLIDAYS
    _BH_START, _BH_END, _HOLIDAYS = cfg.business_start, cfg.business_end, cfg.holidays

    if not pm_account_id:
        return {"error": "pm_account_id is required (no DB auto-detect in pm_core)"}

    tickets, sprint_meta = fetch_sprint_tickets(cfg, sprint_id)
    if not tickets:
        return {"error": "No tickets found for sprint", "sprint_meta": sprint_meta}

    comments, changelogs = fetch_all_comments_and_changelogs([t["key"] for t in tickets])
    return compute_pm_audit(
        tickets=tickets, comments=comments, changelogs=changelogs,
        pm_account_id=pm_account_id, pm_names=pm_names or [],
        sprint_meta=sprint_meta, thresholds=thresholds,
    )
