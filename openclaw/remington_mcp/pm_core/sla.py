"""SLA checking — pure compute layer.

Ported from ``scripts/core/sla_check_working.py``. Computes Jira SLA violations
and, using the ``prior_state`` carried in from STATE.md, decides which ones are
new enough to warrant an alert (24h cooldown, re-alert on escalation to
critical). Posting the alerts is the agent's job — this module only computes.

DROPPED from the original (all side effects / monolith couplings):
  * Slack posting (``post_violations_to_slack``, ``log_to_pm_channel``)
  * SQLite dedup (``sla_alert_tracker``) — replaced by ``prior_state`` in/out
  * dashboard_db violation storage + check-run logging
  * ``sla_escalation`` module (Jira comment escalation)
  * file snapshots (``save_snapshot``)

STUBBED:
  * PR / Bitbucket staleness checks — see ``_check_pr_slas``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from trinity.jira import search_jira, get_status_history

from ._dates import (
    jira_project_clause,
    parse_jira_datetime,
    hours_since,
    now_utc,
)

# Cooldown before re-alerting the same item (hours). Was hardcoded in
# sla_alert_tracker.should_alert_violation.
ALERT_COOLDOWN_HOURS = 24

# SLA thresholds (hours) and the critical-escalation ceiling, per status.
# Carried over verbatim from check_jira_slas_direct.
_SLA_RULES = {
    "qa": {"threshold": 24, "critical": 48, "type": "qa_stale",
           "label": "In QA", "sla_note": "SLA: 24h"},
    "pending_approval": {"threshold": 48, "critical": 72, "type": "pending_approval",
                         "label": "Pending approval", "sla_note": "SLA: 48h"},
    "blocked": {"threshold": 24, "critical": 48, "type": "blocked_ticket",
                "label": "Blocked", "sla_note": "SLA: 24h — daily update required"},
    "changes_requested": {"threshold": 48, "critical": 72, "type": "changes_requested",
                          "label": "Changes Requested",
                          "sla_note": "SLA: 48h — address QA feedback and push back to QA"},
}

_QA_STATUSES = {"In QA", "QA", "Ready for QA"}


def _time_in_current_status(key: str, fallback_hours: float) -> float:
    """Time-in-current-status hours from trinity, or fallback on any error."""
    try:
        history = get_status_history(key)
        if history.get("error"):
            return fallback_hours
        return history.get("time_in_current_status_hours") or fallback_hours
    except Exception:
        return fallback_hours


def _make_violation(rule: Dict, key: str, title: str, owner: str,
                    link: str, hours: float) -> Dict[str, Any]:
    severity = "critical" if hours > rule["critical"] else "warning"
    return {
        "type": rule["type"],
        "severity": severity,
        "item_id": key,
        "title": title,
        "owner": owner,
        "hours_overdue": round(hours - rule["threshold"], 1),
        "link": link,
        "message": f"{rule['label']} for {hours:.1f}h ({rule['sla_note']})",
    }


def _check_jira_slas(cfg) -> List[Dict[str, Any]]:
    """Compute Jira SLA violations for open-sprint tickets."""
    violations: List[Dict[str, Any]] = []

    clause = jira_project_clause(cfg.project_key)
    jql = (
        f"{clause} AND sprint in openSprints() "
        f"AND status NOT IN (Done, Closed, Cancelled)"
    )
    data = search_jira(jql, max_results=100,
                       fields=["summary", "status", "assignee", "updated", "labels"])
    if data.get("error"):
        raise RuntimeError(f"Jira search failed: {data.get('message') or data}")

    browse = cfg.browse_base
    for ticket in data.get("issues", []):
        key = ticket["key"]
        status = ticket.get("status") or ""
        assignee = ticket.get("assignee", "Unassigned")
        title = ticket.get("summary") or ""
        labels = ticket.get("labels", []) or []
        link = f"{browse}/{key}"

        updated = parse_jira_datetime(ticket.get("updated"))
        time_since_update = hours_since(updated)

        if status in _QA_STATUSES:
            rule = _SLA_RULES["qa"]
        elif status == "Pending Approval":
            rule = _SLA_RULES["pending_approval"]
        elif "Blocked" in status or "blocked" in labels:
            rule = _SLA_RULES["blocked"]
        elif status == "Changes Requested":
            rule = _SLA_RULES["changes_requested"]
        else:
            continue

        elapsed = _time_in_current_status(key, time_since_update)
        if elapsed > rule["threshold"]:
            violations.append(_make_violation(rule, key, title, assignee, link, elapsed))

    return violations


def _check_pr_slas(cfg) -> List[Dict[str, Any]]:
    """PR / Bitbucket staleness checks.

    TODO(port): the original used the standalone ``bitbucket_cli`` client
    (list_pull_requests, 16h staleness threshold, critical > 32h). Re-point at
    ``trinity.bb`` once its PR-listing shape is confirmed; the compute is:
      hours_since_update = simple_business_hours(pr.updated_on)
      if hours_since_update > 16: violation (critical if > 32) type='pr_stale'.
    Returns [] for now so Jira SLA still works.
    """
    return []


def check_slas(cfg, prior_state: Optional[Dict] = None) -> Dict[str, Any]:
    """Compute SLA violations and decide which to alert on.

    Args:
        cfg: PMConfig.
        prior_state: dict keyed by item_id → {"last_alerted_at": iso,
            "severity": str}. Carried in from STATE.md; may be None/empty.

    Returns:
        {
          "violations": [ {type, severity, item_id, title, owner,
                           hours_overdue, link, message}, ... ],
          "alerts_to_send": [ <subset of violations past cooldown / escalated> ],
          "state": { item_id: {last_alerted_at, severity, type} },  # persist this
          "summary": {"total": int, "critical": int, "warning": int},
        }
    """
    prior = prior_state or {}
    violations = _check_jira_slas(cfg) + _check_pr_slas(cfg)

    now = now_utc().isoformat()
    alerts_to_send: List[Dict[str, Any]] = []
    new_state: Dict[str, Dict[str, Any]] = {}

    for v in violations:
        item_id = v["item_id"]
        prev = prior.get(item_id)
        should_alert = False
        if prev is None:
            should_alert = True  # never alerted
        else:
            last = parse_jira_datetime(prev.get("last_alerted_at"))
            aged_out = last is None or hours_since(last) >= ALERT_COOLDOWN_HOURS
            escalated = prev.get("severity") != "critical" and v["severity"] == "critical"
            should_alert = aged_out or escalated

        if should_alert:
            alerts_to_send.append(v)
            last_alerted_at = now
        else:
            last_alerted_at = prev.get("last_alerted_at", now)

        new_state[item_id] = {
            "last_alerted_at": last_alerted_at,
            "severity": v["severity"],
            "type": v["type"],
        }

    summary = {
        "total": len(violations),
        "critical": sum(1 for v in violations if v["severity"] == "critical"),
        "warning": sum(1 for v in violations if v["severity"] == "warning"),
    }
    return {
        "violations": violations,
        "alerts_to_send": alerts_to_send,
        "state": new_state,
        "summary": summary,
    }
