"""Daily standup workflow — pure compute orchestration.

Ported from ``scripts/core/standup_workflow.py`` (the 7-section report) plus the
Definition-of-Ready queries from ``scripts/utilities/dor_enforcement.py``
(section 7). Each section COMPUTES a structured result; nothing is posted or
written. SLA (section 5) delegates to ``sla.check_slas`` and threads its state
through ``prior_state``.

SECTIONS:
  1. sprint_burndown       — sprint completion %, status/priority breakdown, top open
  2. code_ticket_gaps      — In Progress tickets stalled ≥ 2 days
  3. productivity_audit    — NOT IMPLEMENTED in the original; stub preserved
  4. timesheet_analysis    — runs as a separate WEEKLY routine; see timesheet.py
  5. sla_monitoring        — delegates to sla.check_slas (state threaded)
  6. deadline_risk         — was never implemented in the original (stub)
  7. dor_enforcement       — missing deadlines / estimates / stalled refinement,
                             with suggested Jira comment texts (NOT posted)

DROPPED: all Slack posting (report + per-violation blocks), markdown/JSON file
saving, and — critically — the DOR enforcer's ``add_jira_comment`` calls. DOR
now returns the tickets + suggested comment text and mentions; POSTING is the
agent's job.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from trinity.jira import search_jira

from ._dates import jira_project_clause, parse_jira_datetime
from . import sla as _sla


# ── Section 1: Sprint burndown ───────────────────────────────────────────────

def _section_sprint_burndown(cfg) -> Dict[str, Any]:
    clause = jira_project_clause(cfg.project_key)
    jql = f"{clause} AND sprint in openSprints() ORDER BY status ASC"
    result = search_jira(jql, max_results=100)
    if result.get("error"):
        return {"status": "error", "error": result.get("message")}

    issues = result.get("issues", [])
    total = result.get("total", len(issues))
    status_breakdown, priority_breakdown, done_count = {}, {}, 0
    for issue in issues:
        status = issue.get("status") or "Unknown"
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
        if status.lower() in ("done", "closed", "resolved"):
            done_count += 1
        priority = issue.get("priority") or "None"
        priority_breakdown[priority] = priority_breakdown.get(priority, 0) + 1

    completion_pct = (done_count / total * 100) if total else 0.0
    open_tickets = [t for t in issues
                    if (t.get("status") or "").lower() not in ("done", "closed", "resolved")]
    priority_order = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}
    open_tickets.sort(key=lambda t: priority_order.get(t.get("priority") or "", 99))

    return {
        "status": "completed",
        "total_issues": total,
        "completion_pct": round(completion_pct, 1),
        "at_risk": completion_pct < 50,
        "status_breakdown": status_breakdown,
        "priority_breakdown": priority_breakdown,
        "top_open_tickets": [
            {"key": t.get("key"), "summary": (t.get("summary") or "")[:60],
             "status": t.get("status"), "assignee": t.get("assignee", "Unassigned"),
             "link": f"{cfg.browse_base}/{t.get('key')}"}
            for t in open_tickets[:5]
        ],
    }


# ── Section 2: Code-ticket gap detection ─────────────────────────────────────

def _section_code_ticket_gaps(cfg) -> Dict[str, Any]:
    clause = jira_project_clause(cfg.project_key)
    jql = f'{clause} AND status = "In Progress" AND sprint in openSprints() ORDER BY updated ASC'
    result = search_jira(jql, max_results=50,
                         fields=["summary", "assignee", "updated", "priority"])
    if result.get("error"):
        return {"status": "error", "error": result.get("message")}

    issues = result.get("issues", [])
    now = datetime.now()
    stalled, active = [], []
    for issue in issues:
        updated = parse_jira_datetime(issue.get("updated"))
        days_stale = 0
        if updated:
            ref = now.replace(tzinfo=updated.tzinfo) if updated.tzinfo else now
            days_stale = (ref - updated).days
        entry = {"key": issue.get("key"), "summary": (issue.get("summary") or "")[:60],
                 "assignee": issue.get("assignee", "Unassigned"), "days_stale": days_stale,
                 "link": f"{cfg.browse_base}/{issue.get('key')}"}
        (stalled if days_stale >= 2 else active).append(entry)

    return {"status": "completed", "total": result.get("total", len(issues)),
            "stalled": stalled, "active": active}


# ── Section 7: Definition of Ready enforcement (compute only) ─────────────────

def _dor_query(cfg, status_clause: str, extra: str, fields: List[str]) -> List[Dict]:
    clause = jira_project_clause(cfg.project_key)
    jql = f"{clause} AND sprint in openSprints() AND {status_clause} {extra}"
    result = search_jira(jql, max_results=50, fields=fields)
    if result.get("error"):
        return []
    return result.get("issues", [])


def _days_in_status(updated_str: Optional[str]) -> int:
    updated = parse_jira_datetime(updated_str)
    if not updated:
        return 0
    ref = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
    return (ref - updated).days


def _dor_comment_missing_deadline(ticket: Dict) -> Dict[str, Any]:
    days = _days_in_status(ticket.get("updated"))
    assignee = ticket.get("assignee") or "the assignee"
    text = (
        f"📅 MISSING DEADLINE\n\n"
        f"This ticket has been {ticket.get('status', 'Unknown')} for {days} days "
        f"without a due date set.\n\nRequired Action: {assignee} — Please set a due "
        f"date by EOD today for capacity planning and sprint tracking.\n\n"
        f"---\nAutomated reminder from Definition of Ready Enforcer"
    )
    return {"key": ticket.get("key"), "assignee": assignee, "comment": text}


def _dor_comment_missing_estimate(ticket: Dict) -> Dict[str, Any]:
    assignee = ticket.get("assignee") or "the assignee"
    text = (
        f"⏱️ MISSING HOURS ESTIMATE\n\nThis ticket does not have an Original "
        f'Estimate set.\n\nRequired Action: {assignee} — Please add a time estimate '
        f'in the "Original Estimate" field.\n\n'
        f"---\nAutomated reminder from Definition of Ready Enforcer"
    )
    return {"key": ticket.get("key"), "assignee": assignee, "comment": text}


def _dor_comment_stalled_refinement(ticket: Dict) -> Dict[str, Any]:
    days = _days_in_status(ticket.get("updated"))
    assignee = ticket.get("assignee") or "the assignee"
    text = (
        f"🚨 COMPLETE REFINEMENT\n\nThis ticket has been In Refinement for {days} "
        f"days.\n\nRequired Action: {assignee} — Please choose one:\n"
        f'1. Transition to "Ready for Development" if refinement is complete\n'
        f'2. Transition to "Ready for Design" if design is needed\n'
        f"3. Ask clarifying questions if more information is required\n\n"
        f"---\nAutomated reminder from Definition of Ready Enforcer (2-day limit)"
    )
    return {"key": ticket.get("key"), "assignee": assignee, "comment": text}


def _section_dor_enforcement(cfg) -> Dict[str, Any]:
    status_active = 'status IN ("In Progress", "Ready for Development", "Ready for QA")'
    fields = ["summary", "status", "assignee", "priority", "updated"]

    missing_deadlines = _dor_query(cfg, status_active, "AND duedate IS EMPTY "
                                   "ORDER BY status ASC, updated DESC", fields)
    missing_estimates = _dor_query(cfg, status_active, "AND timeoriginalestimate IS EMPTY "
                                   "ORDER BY status ASC, updated DESC", fields)
    stalled_refinement = _dor_query(cfg, 'status = "In Refinement"',
                                    "AND updated < -2d ORDER BY updated ASC", fields)

    # NOTE: original posted up to 5 Jira comments per category. Here we only
    # SUGGEST the comment text (first 5 each) — the agent posts.
    return {
        "status": "completed",
        "missing_deadlines": missing_deadlines,
        "missing_estimates": missing_estimates,
        "stalled_refinement": stalled_refinement,
        "counts": {
            "missing_deadlines": len(missing_deadlines),
            "missing_estimates": len(missing_estimates),
            "stalled_refinement": len(stalled_refinement),
        },
        "suggested_comments": {
            "missing_deadlines": [_dor_comment_missing_deadline(t) for t in missing_deadlines[:5]],
            "missing_estimates": [_dor_comment_missing_estimate(t) for t in missing_estimates[:5]],
            "stalled_refinement": [_dor_comment_stalled_refinement(t) for t in stalled_refinement[:5]],
        },
    }


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_standup(cfg, prior_state: Optional[Dict] = None) -> Dict[str, Any]:
    """Run the full daily standup analysis.

    Args:
        cfg: PMConfig.
        prior_state: dict of per-routine state; only ``prior_state["sla"]`` is
            used (threaded into ``sla.check_slas``).

    Returns:
        {
          "date": "YYYY-MM-DD",
          "sections": {
             "sprint_burndown": {...}, "code_ticket_gaps": {...},
             "productivity_audit": {status: "not_implemented"},
             "timesheet_analysis": {status: "deferred_weekly"},
             "sla_monitoring": <sla.check_slas result minus state>,
             "deadline_risk": {status: "not_implemented"},
             "dor_enforcement": {...},
          },
          "alerts_to_send": [ <SLA alerts past cooldown> ],
          "state": { "sla": {...} },   # persist this
        }
    """
    prior = prior_state or {}
    sla_result = _sla.check_slas(cfg, prior.get("sla"))

    sections = {
        "sprint_burndown": _section_sprint_burndown(cfg),
        "code_ticket_gaps": _section_code_ticket_gaps(cfg),
        "productivity_audit": {
            "status": "not_implemented",
            "note": "Planned: Slack timesheet + git commit analysis vs Jira tickets.",
        },
        "timesheet_analysis": {
            "status": "deferred_weekly",
            "note": "Timesheet runs as a separate weekly routine — see timesheet.build_timesheet.",
        },
        "sla_monitoring": {k: v for k, v in sla_result.items() if k != "state"},
        "deadline_risk": {
            "status": "not_implemented",
            "note": "Section 6 was never implemented in the original workflow.",
        },
        "dor_enforcement": _section_dor_enforcement(cfg),
    }

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sections": sections,
        "alerts_to_send": sla_result.get("alerts_to_send", []),
        "state": {"sla": sla_result.get("state", {})},
    }
