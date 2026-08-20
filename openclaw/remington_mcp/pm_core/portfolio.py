"""Portfolio health check — pure compute layer.

Ported from ``scripts/core/portfolio_health_check.py``. Runs 7 hygiene signals
over the project's Initiatives + Epics and returns findings. This routine has no
cross-run state (the original only persisted to the dashboard DB for history),
so ``prior_state`` is accepted for signature symmetry but simply echoed back.

SIGNALS (preserved verbatim):
  1. NO_DUE_DATE           — in-flight Initiative with no due date (warning)
  2. STATUS_DRIFT          — Initiative status vs child rollup mismatch (critical)
  3. STALE_IN_PROGRESS     — in-flight Initiative, no update > 60 days (warning)
  4. OVERSCOPED            — Initiative with > 6 child Epics (info)
  5. OVERDUE_DRAFT         — Epic in Draft/To Do past due date (warning)
  6. ORPHAN_EPIC           — Epic with no / non-Initiative parent (info)
  7. INITIAL_RELEASE_BLOAT — "Initial Release" Initiative w/ > 3 open Epics (info)

DROPPED: console/Slack digest rendering, dashboard-DB persistence
(``save_to_db``, ``post_slack_digest``). The structured records + counts are
returned; formatting/posting is the agent's job.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import requests

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL

from ._dates import days_ago, past_due

# Statuses considered "in flight" for an Initiative (need a due date).
IN_FLIGHT_STATUSES = {"In Progress", "In Refinement", "Pending Approval"}
# Statuses considered "done" for Epic rollup.
DONE_STATUSES = {"Complete", "Done", "Released", "Cancelled", "Declined"}
# Statuses that mean the Initiative thinks it's finished.
COMPLETE_STATUSES = {"Complete", "Done", "Released"}

STALE_DAYS = 60
OVERSCOPED_EPICS = 6
INITIAL_RELEASE_OPEN_EPICS = 3

SEVERITY_ORDER = {"critical": 3, "warning": 2, "info": 1}


def _date(s: Optional[str]) -> Optional[str]:
    return s[:10] if s else None


def _max_severity(findings: List[Dict]) -> str:
    if not findings:
        return "info"
    return max(findings, key=lambda f: SEVERITY_ORDER.get(f["severity"], 0))["severity"]


def _fetch_issues(project_key: str, issuetype: str) -> List[Dict]:
    """Fetch all Initiatives or Epics for a single project key (raw REST —
    search_jira does not expose parent/duedate)."""
    issues: List[Dict] = []
    next_token: Optional[str] = None
    while True:
        payload: Dict[str, Any] = {
            "jql": f"project = {project_key} AND issuetype = {issuetype} ORDER BY created ASC",
            "fields": ["summary", "status", "duedate", "created", "updated", "parent"],
            "maxResults": 100,
        }
        if next_token:
            payload["nextPageToken"] = next_token
        resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        issues.extend(body.get("issues", []))
        next_token = body.get("nextPageToken")
        if not next_token:
            break
    return issues


def analyze_initiative(cfg, init: Dict, child_epics: List[Dict]) -> Dict[str, Any]:
    """Run all Initiative-level signals; return a finding record."""
    key = init["key"]
    fields = init["fields"]
    status_name = fields["status"]["name"]
    summary = fields.get("summary", "")
    duedate = fields.get("duedate")

    active_epics = [e for e in child_epics if e["fields"]["status"]["name"] not in DONE_STATUSES]
    done_epics = [e for e in child_epics if e["fields"]["status"]["name"] in DONE_STATUSES]
    total_epics = len(child_epics)

    findings: List[Dict[str, str]] = []

    if status_name in IN_FLIGHT_STATUSES and not duedate:
        findings.append({
            "code": "NO_DUE_DATE", "severity": "warning",
            "message": f"In-flight Initiative ({status_name}) has no due date — "
                       f"sprint planning has nothing to anchor against.",
        })

    if status_name in COMPLETE_STATUSES and active_epics:
        findings.append({
            "code": "STATUS_DRIFT", "severity": "critical",
            "message": f"Marked {status_name} but has {len(active_epics)} non-done "
                       f"child Epic(s). Either reopen or close out the children.",
        })
    elif status_name in IN_FLIGHT_STATUSES and total_epics > 0 and not active_epics:
        findings.append({
            "code": "STATUS_DRIFT", "severity": "critical",
            "message": f"Marked {status_name} but all {total_epics} child Epics are "
                       f"done/declined — should transition to Complete.",
        })

    if status_name in IN_FLIGHT_STATUSES:
        days = days_ago(fields.get("updated"))
        if days is not None and days > STALE_DAYS:
            findings.append({
                "code": "STALE_IN_PROGRESS", "severity": "warning",
                "message": f"{status_name} but no activity in {days} days — likely a "
                           f"zombie. Decide: revive, split, or close.",
            })

    if total_epics > OVERSCOPED_EPICS:
        findings.append({
            "code": "OVERSCOPED", "severity": "info",
            "message": f"{total_epics} child Epics — consider splitting into 2+ smaller "
                       f"Initiatives so progress is legible.",
        })

    if "initial release" in summary.lower() and len(active_epics) > INITIAL_RELEASE_OPEN_EPICS:
        findings.append({
            "code": "INITIAL_RELEASE_BLOAT", "severity": "info",
            "message": f'Named "Initial Release" but has {len(active_epics)} open Epics — '
                       f"name + scope are out of sync.",
        })

    return {
        "key": key,
        "issuetype": "Initiative",
        "summary": summary,
        "status": status_name,
        "parent_key": None,
        "created_at": _date(fields.get("created")),
        "updated_at": _date(fields.get("updated")),
        "due_date": _date(duedate),
        "epic_count": total_epics,
        "active_epic_count": len(active_epics),
        "done_epic_count": len(done_epics),
        "findings": findings,
        "severity": _max_severity(findings),
        "link": f"{cfg.browse_base}/{key}",
    }


def analyze_epic(cfg, epic: Dict, initiative_keys: set) -> Optional[Dict[str, Any]]:
    """Return an Epic finding record ONLY if it has findings."""
    key = epic["key"]
    fields = epic["fields"]
    status_name = fields["status"]["name"]
    summary = fields.get("summary", "")
    duedate = fields.get("duedate")
    parent_key = (fields.get("parent") or {}).get("key")

    findings: List[Dict[str, str]] = []

    if status_name in {"Draft", "To Do"} and past_due(duedate):
        days_overdue = days_ago(duedate) or 0
        findings.append({
            "code": "OVERDUE_DRAFT", "severity": "warning",
            "message": f"Epic in {status_name} but due date passed {days_overdue} days "
                       f"ago. Either start it or move the date.",
        })

    if not parent_key and status_name not in DONE_STATUSES:
        findings.append({
            "code": "ORPHAN_EPIC", "severity": "info",
            "message": "Epic has no parent Initiative — drops out of portfolio rollups.",
        })
    elif parent_key and parent_key not in initiative_keys:
        findings.append({
            "code": "ORPHAN_EPIC", "severity": "info",
            "message": f"Parent {parent_key} is not an Initiative — reparent to a real Initiative.",
        })

    if not findings:
        return None

    return {
        "key": key,
        "issuetype": "Epic",
        "summary": summary,
        "status": status_name,
        "parent_key": parent_key,
        "created_at": _date(fields.get("created")),
        "updated_at": _date(fields.get("updated")),
        "due_date": _date(duedate),
        "epic_count": 0,
        "active_epic_count": 0,
        "done_epic_count": 0,
        "findings": findings,
        "severity": _max_severity(findings),
        "link": f"{cfg.browse_base}/{key}",
    }


def check_portfolio_health(cfg, prior_state: Optional[Dict] = None) -> Dict[str, Any]:
    """Run the full portfolio hygiene audit.

    Args:
        cfg: PMConfig. Uses the FIRST configured project key (Initiatives/Epics
            live in one portfolio project).
        prior_state: unused (portfolio has no cross-run state); echoed back.

    Returns:
        {
          "records": [ <finding record per Initiative/Epic with findings> ],
          "counts": {critical, warning, info, total_findings,
                     total_initiatives, total_epics},
          "state": {},  # portfolio keeps no state
        }
    """
    project_key = (cfg.project_key or "").split(",")[0].strip()

    inits = _fetch_issues(project_key, "Initiative")
    epics = _fetch_issues(project_key, "Epic")

    epics_by_parent: Dict[str, List[Dict]] = {}
    for e in epics:
        p = (e["fields"].get("parent") or {}).get("key")
        if p:
            epics_by_parent.setdefault(p, []).append(e)

    initiative_keys = {i["key"] for i in inits}

    records: List[Dict] = []
    for init in inits:
        rec = analyze_initiative(cfg, init, epics_by_parent.get(init["key"], []))
        if rec["findings"]:
            records.append(rec)
    for epic in epics:
        rec = analyze_epic(cfg, epic, initiative_keys)
        if rec:
            records.append(rec)

    counts = {
        "critical": sum(1 for r in records if r["severity"] == "critical"),
        "warning": sum(1 for r in records if r["severity"] == "warning"),
        "info": sum(1 for r in records if r["severity"] == "info"),
        "total_findings": len(records),
        "total_initiatives": len(inits),
        "total_epics": len(epics),
    }
    return {"records": records, "counts": counts, "state": prior_state or {}}
