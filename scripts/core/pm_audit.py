#!/usr/bin/env python3
"""
PM Self-Audit — Jira data fetcher + DB persistence

Fetches sprint tickets, comments, and changelogs from Jira,
runs them through the pure compute layer, and saves results to DB.

Usage:
    python -m scripts.core.pm_audit                     # auto-detect PM + active sprint
    python -m scripts.core.pm_audit --dry-run            # print JSON, no DB save
    python -m scripts.core.pm_audit --pm-id <accountId>  # specify PM account
    python -m scripts.core.pm_audit --sprint-id <id>     # specify sprint
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trinity.base import get_jira_auth_headers, JIRA_BASE_URL

JIRA_BASE_URL_WEB = os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')
PROJECT_KEY = os.getenv('ATLASSIAN_PROJECT_KEY', '')

# ─── Jira Data Fetching ──────────────────────────────────────────────────────

def _jira_get(url: str, params: Optional[Dict] = None, timeout: int = 20) -> Optional[Dict]:
    try:
        resp = requests.get(url, headers=get_jira_auth_headers(), params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠ GET {url}: {e}")
        return None


def _jira_post(url: str, payload: Dict, timeout: int = 30) -> Optional[Dict]:
    try:
        resp = requests.post(url, headers=get_jira_auth_headers(), json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠ POST {url}: {e}")
        return None


def fetch_sprint_tickets(sprint_id: Optional[str] = None) -> tuple:
    """Fetch all sprint tickets. Returns (tickets, sprint_meta)."""
    if sprint_id:
        jql = (
            f'project IN ({PROJECT_KEY}) AND sprint = {sprint_id} '
            f'AND issuetype not in subTaskIssueTypes()'
        )
    else:
        jql = (
            f'project IN ({PROJECT_KEY}) AND sprint in openSprints() '
            f'AND issuetype not in subTaskIssueTypes()'
        )

    all_issues = []
    sprint_meta = {}
    next_token = None

    while True:
        payload = {
            'jql': jql,
            'fields': ['summary', 'status', 'assignee', 'reporter',
                        'timeoriginalestimate', 'customfield_10020'],
            'maxResults': 100,
        }
        if next_token:
            payload['nextPageToken'] = next_token

        data = _jira_post(f"{JIRA_BASE_URL}/rest/api/3/search/jql", payload)
        if not data:
            break

        issues = data.get('issues', [])
        all_issues.extend(issues)

        # Extract sprint meta from first issue
        if not sprint_meta and issues:
            sprints = issues[0].get('fields', {}).get('customfield_10020') or []
            active = [s for s in sprints if s.get('state') == 'active']
            if active:
                s = active[0]
                sprint_meta = {
                    'sprint_id': str(s.get('id', '')),
                    'sprint_name': s.get('name', ''),
                    'start_date': (s.get('startDate') or '')[:10],
                    'end_date': (s.get('endDate') or '')[:10],
                }

        # Cursor-based pagination
        if data.get('isLast', True):
            break
        next_token = data.get('nextPageToken')
        if not next_token:
            break

    # Normalize tickets
    tickets = []
    for issue in all_issues:
        f = issue.get('fields', {})
        tickets.append({
            'key': issue.get('key', ''),
            'summary': f.get('summary', ''),
            'status': (f.get('status') or {}).get('name', ''),
            'assignee': (f.get('assignee') or {}).get('displayName', 'Unassigned'),
            'assignee_id': (f.get('assignee') or {}).get('accountId', ''),
            'reporter_id': (f.get('reporter') or {}).get('accountId', ''),
            'original_estimate_seconds': f.get('timeoriginalestimate') or 0,
        })

    return tickets, sprint_meta


def fetch_comments(key: str) -> List[Dict]:
    """Fetch all comments for a ticket."""
    data = _jira_get(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/comment",
        params={'maxResults': 100, 'orderBy': 'created'},
    )
    if not data:
        return []
    return data.get('comments', [])


def fetch_changelog(key: str) -> List[Dict]:
    """Fetch changelog for a ticket."""
    all_entries = []
    start_at = 0
    while True:
        data = _jira_get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/changelog",
            params={'maxResults': 100, 'startAt': start_at},
        )
        if not data:
            break
        values = data.get('values', [])
        all_entries.extend(values)
        if start_at + len(values) >= data.get('total', 0):
            break
        start_at += len(values)
    return all_entries


def fetch_all_comments_and_changelogs(
    ticket_keys: List[str],
    max_workers: int = 8,
) -> tuple:
    """Parallel fetch comments + changelogs for all tickets."""
    comments: Dict[str, List] = {}
    changelogs: Dict[str, List] = {}

    total = len(ticket_keys)
    done = 0

    def _fetch_one(key):
        c = fetch_comments(key)
        cl = fetch_changelog(key)
        return key, c, cl

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, k): k for k in ticket_keys}
        for future in as_completed(futures):
            key, c, cl = future.result()
            comments[key] = c
            changelogs[key] = cl
            done += 1
            if done % 10 == 0 or done == total:
                print(f"  Fetched {done}/{total} tickets...")

    return comments, changelogs


# ─── PM Identity Resolution ──────────────────────────────────────────────────

def resolve_pm(pm_account_id: Optional[str] = None) -> tuple:
    """
    Resolve PM account ID and display names.
    Returns (account_id, [name_variants]).
    """
    if pm_account_id:
        # Look up display name from team_members DB
        try:
            from src.database.dashboard_db import get_dashboard_db
            from sqlalchemy import text
            db = get_dashboard_db()
            with db.engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT display_name, jira_display_name FROM team_members "
                    "WHERE jira_account_id = :id"
                ), {"id": pm_account_id}).mappings().first()
                if row:
                    names = list({n for n in [row['display_name'], row.get('jira_display_name')] if n})
                    return pm_account_id, names
        except Exception:
            pass
        return pm_account_id, []

    # Auto-detect: find team member with role=pm
    try:
        from src.database.dashboard_db import get_dashboard_db
        from sqlalchemy import text
        db = get_dashboard_db()
        with db.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT jira_account_id, display_name, jira_display_name FROM team_members "
                "WHERE role = 'pm' AND is_active = 1 LIMIT 1"
            )).mappings().first()
            if row and row['jira_account_id']:
                names = list({n for n in [row['display_name'], row.get('jira_display_name')] if n})
                return row['jira_account_id'], names
    except Exception as e:
        print(f"  ⚠ Could not auto-detect PM: {e}")

    print("❌ No PM account ID provided and could not auto-detect from team_members DB.")
    print("   Use --pm-id <accountId> or add a team member with role='pm'.")
    sys.exit(1)


# ─── DB Persistence ──────────────────────────────────────────────────────────

def save_snapshot(result: Dict) -> None:
    """Save audit snapshot to pm_audit_snapshots table."""
    from src.database.dashboard_db import get_dashboard_db
    from sqlalchemy import text

    db = get_dashboard_db()
    with db.engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO pm_audit_snapshots (
                pm_account_id, pm_display_name, sprint_id, sprint_name, computed_at,
                avg_pending_approval_hours, pending_approval_backlog, approvals_completed,
                total_pm_comments, tickets_engaged, total_sprint_tickets,
                engagement_ratio, threads_waiting_on_pm, avg_pm_response_hours,
                tickets_created_by_pm, estimation_coverage_pct, unestimated_count,
                transitions_by_pm, reopens_rejections,
                tickets_added_mid_sprint, tickets_removed_mid_sprint, assignment_balance_cv,
                avg_blocked_to_pm_comment_hours, blocked_no_pm_engagement,
                overall_grade, grades_json, detail_json
            ) VALUES (
                :pm_account_id, :pm_display_name, :sprint_id, :sprint_name, :computed_at,
                :avg_pending_approval_hours, :pending_approval_backlog, :approvals_completed,
                :total_pm_comments, :tickets_engaged, :total_sprint_tickets,
                :engagement_ratio, :threads_waiting_on_pm, :avg_pm_response_hours,
                :tickets_created_by_pm, :estimation_coverage_pct, :unestimated_count,
                :transitions_by_pm, :reopens_rejections,
                :tickets_added_mid_sprint, :tickets_removed_mid_sprint, :assignment_balance_cv,
                :avg_blocked_to_pm_comment_hours, :blocked_no_pm_engagement,
                :overall_grade, :grades_json, :detail_json
            )
        """), {
            'pm_account_id': result['pm_account_id'],
            'pm_display_name': result.get('pm_display_name', ''),
            'sprint_id': result.get('sprint_id', ''),
            'sprint_name': result.get('sprint_name', ''),
            'computed_at': datetime.utcnow(),
            'avg_pending_approval_hours': result.get('avg_pending_approval_hours'),
            'pending_approval_backlog': result.get('pending_approval_backlog', 0),
            'approvals_completed': result.get('approvals_completed', 0),
            'total_pm_comments': result.get('total_pm_comments', 0),
            'tickets_engaged': result.get('tickets_engaged', 0),
            'total_sprint_tickets': result.get('total_sprint_tickets', 0),
            'engagement_ratio': result.get('engagement_ratio'),
            'threads_waiting_on_pm': result.get('threads_waiting_on_pm', 0),
            'avg_pm_response_hours': result.get('avg_pm_response_hours'),
            'tickets_created_by_pm': result.get('tickets_created_by_pm', 0),
            'estimation_coverage_pct': result.get('estimation_coverage_pct'),
            'unestimated_count': result.get('unestimated_count', 0),
            'transitions_by_pm': result.get('transitions_by_pm', 0),
            'reopens_rejections': result.get('reopens_rejections', 0),
            'tickets_added_mid_sprint': result.get('tickets_added_mid_sprint', 0),
            'tickets_removed_mid_sprint': result.get('tickets_removed_mid_sprint', 0),
            'assignment_balance_cv': result.get('assignment_balance_cv'),
            'avg_blocked_to_pm_comment_hours': result.get('avg_blocked_to_pm_comment_hours'),
            'blocked_no_pm_engagement': result.get('blocked_no_pm_engagement', 0),
            'overall_grade': result.get('overall_grade', ''),
            'grades_json': json.dumps(result.get('grades', {})),
            'detail_json': json.dumps(result.get('detail', {})),
        })
    print("✅ Snapshot saved to pm_audit_snapshots")


# ─── Main Entry ───────────────────────────────────────────────────────────────

def run_pm_audit(
    pm_account_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run the full PM self-audit pipeline."""
    from src.dashboard.pm_audit_compute import compute_pm_audit

    print("=" * 60)
    print(" PM Self-Audit ".center(60))
    print("=" * 60)

    # 1. Resolve PM identity
    print("\n1. Resolving PM identity...")
    account_id, pm_names = resolve_pm(pm_account_id)
    print(f"   PM: {pm_names[0] if pm_names else account_id} ({account_id})")

    # 2. Fetch sprint tickets
    print("\n2. Fetching sprint tickets...")
    tickets, sprint_meta = fetch_sprint_tickets(sprint_id)
    print(f"   Found {len(tickets)} tickets in sprint: {sprint_meta.get('sprint_name', 'unknown')}")

    if not tickets:
        print("❌ No tickets found. Aborting.")
        return {}

    # 3. Parallel fetch comments + changelogs
    print(f"\n3. Fetching comments & changelogs for {len(tickets)} tickets...")
    ticket_keys = [t['key'] for t in tickets]
    comments, changelogs = fetch_all_comments_and_changelogs(ticket_keys)

    total_comments = sum(len(v) for v in comments.values())
    total_changelog = sum(len(v) for v in changelogs.values())
    print(f"   Fetched {total_comments} comments, {total_changelog} changelog entries")

    # 4. Compute metrics
    print("\n4. Computing PM audit metrics...")
    result = compute_pm_audit(
        tickets=tickets,
        comments=comments,
        changelogs=changelogs,
        pm_account_id=account_id,
        pm_names=pm_names,
        sprint_meta=sprint_meta,
    )

    # 5. Print summary
    print("\n" + "=" * 60)
    print(f" Overall Grade: {result['overall_grade']} ".center(60))
    print("=" * 60)
    grades = result.get('grades', {})
    print(f"  Approval Velocity:    {grades.get('approval', '-')}  (avg {result.get('avg_pending_approval_hours', 0):.1f}h, backlog: {result.get('pending_approval_backlog', 0)})")
    print(f"  Comment Engagement:   {grades.get('engagement', '-')}  ({result.get('tickets_engaged', 0)}/{result.get('total_sprint_tickets', 0)} tickets, {result.get('total_pm_comments', 0)} comments)")
    print(f"  Responsiveness:       {grades.get('responsiveness', '-')}  (avg {result.get('avg_pm_response_hours', 0):.1f}h, {result.get('threads_waiting_on_pm', 0)} waiting)")
    print(f"  Grooming:             {grades.get('grooming', '-')}  ({result.get('estimation_coverage_pct', 0):.0f}% estimated, {result.get('tickets_created_by_pm', 0)} created)")
    print(f"  Transitions:          {grades.get('transitions', '-')}  ({result.get('transitions_by_pm', 0)} transitions, {result.get('reopens_rejections', 0)} reopens)")
    blocker_h = result.get('avg_blocked_to_pm_comment_hours')
    blocker_str = f"{blocker_h:.1f}h" if blocker_h is not None else "N/A"
    print(f"  Blocker Response:     {grades.get('blocker_response', '-')}  (avg {blocker_str}, {result.get('blocked_no_pm_engagement', 0)} unengaged)")

    if dry_run:
        print("\n[DRY RUN] Printing full result JSON:\n")
        # Remove detail for console readability, keep metrics
        summary = {k: v for k, v in result.items() if k != 'detail'}
        print(json.dumps(summary, indent=2, default=str))
    else:
        # 6. Save to DB
        print("\n5. Saving snapshot to database...")
        save_snapshot(result)

    return result


def main():
    parser = argparse.ArgumentParser(description='PM Self-Audit — measure PM productivity')
    parser.add_argument('--pm-id', help='Jira account ID of the PM (auto-detect if omitted)')
    parser.add_argument('--sprint-id', help='Jira sprint ID (active sprint if omitted)')
    parser.add_argument('--dry-run', action='store_true', help='Print results without saving to DB')
    args = parser.parse_args()

    run_pm_audit(
        pm_account_id=args.pm_id,
        sprint_id=args.sprint_id,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
