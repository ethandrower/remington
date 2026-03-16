#!/usr/bin/env python3
"""
PM Agent Dashboard - Flask Backend

Simple Flask API + Vue.js frontend for monitoring PM agent checks
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.dashboard_db import get_dashboard_db

app = Flask(
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)
CORS(app)  # Enable CORS for API

# Get database instance
db = get_dashboard_db()


# ============================================================================
# HTML PAGES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    try:
        stats = db.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/violations')
def get_violations():
    """Get active violations"""
    try:
        violation_type = request.args.get('type')
        violations = db.get_active_violations(violation_type)
        # Parse metadata JSON blob for frontend consumption
        for v in violations:
            raw_meta = v.get('metadata')
            if raw_meta and isinstance(raw_meta, str):
                try:
                    v['metadata'] = json.loads(raw_meta)
                except Exception:
                    v['metadata'] = {}
            elif not raw_meta:
                v['metadata'] = {}
        return jsonify(violations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/violations/<item_id>/resolve', methods=['POST'])
def resolve_violation(item_id):
    """Mark a violation as resolved"""
    try:
        db.resolve_violation(item_id)
        return jsonify({"success": True, "message": f"Resolved {item_id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/checks/history')
def get_check_history():
    """Get check execution history"""
    try:
        check_type = request.args.get('type')
        limit = int(request.args.get('limit', 50))
        # Clean up any checks stuck in 'running' due to process crash/restart
        db.mark_stale_runs_failed(stale_after_minutes=15)
        history = db.get_check_history(check_type, limit)
        # Ensure datetime objects are serialized as strings for JSON
        for row in history:
            for k in ('started_at', 'completed_at'):
                if row.get(k) and not isinstance(row[k], str):
                    row[k] = row[k].isoformat()
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
def health_check():
    """Connectivity health check for all integrations"""
    import traceback
    results = {}

    # Database
    try:
        db.get_stats()
        results['database'] = {'ok': True}
    except Exception as e:
        results['database'] = {'ok': False, 'error': str(e)}

    # Jira — uses Atlassian Cloud API (api.atlassian.com/ex/jira/{cloud_id}), not instance URL
    try:
        import requests as req
        import base64
        cloud_id = os.getenv('ATLASSIAN_CLOUD_ID', '')
        email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL', '')
        token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN', '')
        if not all([cloud_id, email, token]):
            results['jira'] = {'ok': False, 'error': 'Missing ATLASSIAN_CLOUD_ID, ATLASSIAN_SERVICE_ACCOUNT_EMAIL, or ATLASSIAN_SERVICE_ACCOUNT_TOKEN'}
        else:
            auth = base64.b64encode(f'{email}:{token}'.encode()).decode()
            resp = req.get(
                f'https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself',
                headers={'Authorization': f'Basic {auth}', 'Accept': 'application/json'},
                timeout=5)
            if resp.ok:
                data = resp.json()
                results['jira'] = {'ok': True, 'account': data.get('displayName', data.get('emailAddress', 'unknown'))}
            else:
                results['jira'] = {'ok': False, 'error': f'HTTP {resp.status_code}: {resp.text[:200]}'}
    except Exception as e:
        results['jira'] = {'ok': False, 'error': str(e)}

    # Slack
    try:
        import requests as req
        token = os.getenv('SLACK_BOT_TOKEN', '')
        if not token:
            results['slack'] = {'ok': False, 'error': 'Missing SLACK_BOT_TOKEN'}
        else:
            resp = req.get('https://slack.com/api/auth.test',
                          headers={'Authorization': f'Bearer {token}'}, timeout=5)
            data = resp.json()
            if data.get('ok'):
                results['slack'] = {'ok': True, 'team': data.get('team'), 'user': data.get('user')}
            else:
                results['slack'] = {'ok': False, 'error': data.get('error', 'unknown')}
    except Exception as e:
        results['slack'] = {'ok': False, 'error': str(e)}

    # Anthropic API key presence (don't actually call it, costs money)
    key = os.getenv('ANTHROPIC_API_KEY', '')
    results['anthropic'] = {'ok': bool(key), 'error': None if key else 'Missing ANTHROPIC_API_KEY'}

    # SERVICE_ACCOUNT_NAME
    name = os.getenv('SERVICE_ACCOUNT_NAME', '')
    results['service_account_name'] = {'ok': bool(name), 'value': name or None,
                                        'error': None if name else 'Missing SERVICE_ACCOUNT_NAME — self-mention loops may occur'}

    overall_ok = all(v['ok'] for v in results.values())
    return jsonify({'ok': overall_ok, 'checks': results}), 200 if overall_ok else 207


@app.route('/api/checks/latest/<check_type>')
def get_latest_check(check_type):
    """Get latest check run for a type"""
    try:
        latest = db.get_latest_check(check_type)
        return jsonify(latest if latest else {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/checks/schedules')
def get_schedules():
    """Get all check schedules"""
    try:
        schedules = db.get_schedules()
        return jsonify(schedules)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/checks/run', methods=['POST'])
def run_check():
    """Trigger a manual check execution"""
    try:
        data = request.json
        check_type = data.get('check_type', 'sla-check')
        dry_run = data.get('dry_run', False)

        # Log check start
        run_id = db.log_check_start(check_type, triggered_by='manual')

        # Build command
        if check_type == 'blocked-analysis':
            cmd = ['python', '-m', 'scripts.core.blocked_ticket_analyzer']
        else:
            cmd = ['python', 'run_agent.py', check_type]
        if dry_run:
            cmd.append('--dry-run')

        # Execute check in background
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=str(Path(__file__).parent.parent.parent)
            )

            success = result.returncode == 0
            error_msg = None if success else result.stderr

            # Try to parse output for violations (if SLA check)
            violations_found = 0
            critical_count = 0
            warning_count = 0

            if success:
                try:
                    if check_type == 'sla-check':
                        snapshot_file = Path('.claude/data/sla-tracking/daily-snapshots') / f"{datetime.now().strftime('%Y-%m-%d')}.json"
                        if snapshot_file.exists():
                            with open(snapshot_file) as f:
                                snapshot = json.load(f)
                                violations_found = snapshot.get('total_violations', 0)
                                critical_count = snapshot.get('by_severity', {}).get('critical', 0)
                                warning_count = snapshot.get('by_severity', {}).get('warning', 0)
                    elif check_type == 'blocked-analysis':
                        from sqlalchemy import text as sa_text
                        with db.engine.connect() as conn:
                            row = conn.execute(sa_text(
                                "SELECT COUNT(*) as n, "
                                "SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as c, "
                                "SUM(CASE WHEN severity='warning' THEN 1 ELSE 0 END) as w "
                                "FROM active_violations WHERE violation_type='blocked_ticket' AND resolved_at IS NULL"
                            )).mappings().first()
                            if row:
                                violations_found = row['n'] or 0
                                critical_count = row['c'] or 0
                                warning_count = row['w'] or 0
                except Exception:
                    pass

            # Log completion
            db.log_check_complete(
                run_id,
                violations_found=violations_found,
                critical_count=critical_count,
                warning_count=warning_count,
                output_json={"stdout": result.stdout[:1000], "stderr": result.stderr[:1000]},
                error_message=error_msg
            )

            return jsonify({
                "success": success,
                "run_id": run_id,
                "violations_found": violations_found,
                "critical_count": critical_count,
                "warning_count": warning_count,
                "message": "Check completed successfully" if success else "Check failed",
                "error": error_msg
            })

        except subprocess.TimeoutExpired:
            db.log_check_complete(run_id, error_message="Check timed out after 10 minutes")
            return jsonify({"success": False, "error": "Check timed out"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agent/activity')
def get_agent_activity():
    """Get recent agent interactions (Slack, Jira, Bitbucket)"""
    try:
        from sqlalchemy import text as sa_text
        limit = int(request.args.get('limit', 50))
        engine = db.engine
        activities = []

        # Query Slack interactions from shared DB
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text("""
                    SELECT ts, channel, user_id, text, response, processed_at
                    FROM slack_processed_messages
                    ORDER BY processed_at DESC
                    LIMIT :limit
                """), {"limit": limit}).mappings().all()
                for row in rows:
                    ts = row['processed_at']
                    activities.append({
                        'platform': 'slack',
                        'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                        'item_id': row['ts'],
                        'channel': row['channel'],
                        'user': row['user_id'],
                        'request': row['text'] or 'N/A',
                        'response': row['response'] or 'Processed',
                        'link': None
                    })
        except Exception:
            pass  # Table may not exist yet if Slack monitor hasn't run

        # Query Bitbucket PR interactions from shared DB
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text("""
                    SELECT repo, pr_id, comment_id, processed_at
                    FROM bb_processed_pr_comments
                    ORDER BY processed_at DESC
                    LIMIT :limit
                """), {"limit": limit}).mappings().all()
                from src.utils.system_config import get_setting as _get_setting
                workspace = _get_setting('bitbucket_workspace', env_fallback='BITBUCKET_WORKSPACE') or ''
                for row in rows:
                    ts = row['processed_at']
                    activities.append({
                        'platform': 'bitbucket',
                        'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                        'item_id': f"PR-{row['pr_id']}",
                        'repo': row['repo'],
                        'comment_id': row['comment_id'],
                        'request': f"Comment on PR #{row['pr_id']}",
                        'response': 'Processed',
                        'link': f"https://bitbucket.org/{workspace}/{row['repo']}/pull-requests/{row['pr_id']}"
                    })
        except Exception:
            pass

        # Query general activity log from shared DB
        try:
            with engine.connect() as conn:
                rows = conn.execute(sa_text("""
                    SELECT timestamp, activity_type, details, item_id
                    FROM activities
                    WHERE activity_type IN ('jira_comment_posted', 'slack_message_posted', 'pm_story_draft', 'pm_story_created')
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """), {"limit": limit}).mappings().all()
                jira_url = os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')
                for row in rows:
                    platform = 'jira' if 'jira' in row['activity_type'] else 'slack'
                    ts = row['timestamp']
                    activities.append({
                        'platform': platform,
                        'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                        'item_id': row['item_id'] or 'N/A',
                        'activity_type': row['activity_type'],
                        'request': row['details'] or 'N/A',
                        'response': 'Action completed',
                        'link': f"{jira_url}/browse/{row['item_id']}" if row['item_id'] and platform == 'jira' else None
                    })
        except Exception:
            pass

        # Sort all activities by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        activities = activities[:limit]

        return jsonify(activities)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/blocked/analysis')
def get_blocked_analysis():
    """Get latest blocked ticket analysis results."""
    try:
        from sqlalchemy import text as sa_text
        from collections import Counter

        with db.engine.connect() as conn:
            try:
                rows = conn.execute(sa_text("""
                    SELECT key, summary, assignee, link, category, needs_alert,
                           action, alert_message, blocking_tickets, analyzed_at
                    FROM blocked_ticket_analyses
                    ORDER BY needs_alert DESC, analyzed_at DESC
                """)).mappings().all()
            except Exception:
                return jsonify({'results': [], 'stats': {}})

            results = []
            for row in rows:
                r = dict(row)
                r['blocking_tickets'] = json.loads(r['blocking_tickets'] or '[]')
                ts = r.get('analyzed_at')
                if ts and hasattr(ts, 'isoformat'):
                    r['analyzed_at'] = ts.isoformat()
                results.append(r)

        cats = Counter(r['category'] for r in results)
        stats = {
            'total': len(results),
            'needs_action': sum(1 for r in results if r['needs_alert']),
            'by_category': dict(cats),
            'last_run': results[0]['analyzed_at'] if results else None,
        }
        return jsonify({'results': results, 'stats': stats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/blocked/run', methods=['POST'])
def run_blocked_analysis():
    """Trigger a manual run of the blocked ticket analyzer (runs in background)."""
    import threading
    try:
        dry_run = (request.json or {}).get('dry_run', False)
        cmd = ['python', '-m', 'scripts.core.blocked_ticket_analyzer']
        if dry_run:
            cmd.append('--dry-run')
        project_root = str(Path(__file__).parent.parent.parent)

        def _run():
            try:
                subprocess.run(cmd, timeout=300, cwd=project_root)
            except Exception:
                pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Analysis started in background. Refresh in ~30 seconds to see results.',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/timesheets')
def get_timesheets():
    """Get timesheet records grouped by week then developer."""
    try:
        from sqlalchemy import text as sa_text

        weeks_limit = int(request.args.get('weeks', 8))

        with db.engine.connect() as conn:
            try:
                # Get distinct weeks (most recent first)
                week_rows = conn.execute(sa_text("""
                    SELECT DISTINCT week_start, week_end
                    FROM timesheet_weeks
                    ORDER BY week_start DESC
                    LIMIT :limit
                """), {"limit": weeks_limit}).mappings().all()
            except Exception:
                return jsonify([])

            result = []
            for wr in week_rows:
                week_start = wr["week_start"]
                week_end = wr["week_end"]

                # Get all developers for this week
                dev_rows = conn.execute(sa_text("""
                    SELECT account_id, developer_name, total_seconds, total_estimate_seconds
                    FROM timesheet_weeks
                    WHERE week_start = :week_start
                    ORDER BY total_seconds DESC
                """), {"week_start": week_start}).mappings().all()

                developers = []
                for dr in dev_rows:
                    # Get ticket entries for this dev+week
                    entry_rows = conn.execute(sa_text("""
                        SELECT issue_key, summary, status,
                               logged_seconds, estimate_seconds, due_date, jira_url
                        FROM timesheet_entries
                        WHERE account_id = :account_id AND week_start = :week_start
                        ORDER BY logged_seconds DESC
                    """), {"account_id": dr["account_id"], "week_start": week_start}).mappings().all()

                    developers.append({
                        "account_id": dr["account_id"],
                        "name": dr["developer_name"],
                        "total_seconds": dr["total_seconds"],
                        "total_estimate_seconds": dr["total_estimate_seconds"],
                        "entries": [dict(e) for e in entry_rows],
                    })

                result.append({
                    "week_start": week_start,
                    "week_end": week_end,
                    "developers": developers,
                    "team_total_seconds": sum(d["total_seconds"] for d in developers),
                    "team_total_estimate_seconds": sum(d["total_estimate_seconds"] for d in developers),
                })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/timesheets/run', methods=['POST'])
def run_timesheet():
    """Trigger a manual timesheet pull (runs in background)."""
    import threading
    try:
        data = request.json or {}
        dry_run = data.get('dry_run', False)
        current_week = data.get('current_week', False)
        week_offset = int(data.get('week_offset', 0))

        cmd = ['python', 'scripts/core/timesheet_report.py']
        if dry_run:
            cmd.append('--dry-run')
        if current_week:
            cmd.append('--current-week')
        if week_offset:
            cmd += ['--week-offset', str(week_offset)]

        project_root = str(Path(__file__).parent.parent.parent)

        def _run():
            try:
                subprocess.run(cmd, timeout=300, cwd=project_root)
            except Exception:
                pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Timesheet pull started. Refresh in ~30 seconds to see results.',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pr/reviews')
def get_pr_reviews():
    """Get PR review metrics and activity"""
    try:
        from sqlalchemy import text as sa_text
        limit = int(request.args.get('limit', 50))
        from src.utils.system_config import get_setting as _get_setting
        workspace = _get_setting('bitbucket_workspace', env_fallback='BITBUCKET_WORKSPACE') or ''
        reviews = []

        try:
            with db.engine.connect() as conn:
                rows = conn.execute(sa_text("""
                    SELECT repo, pr_id, commit_sha, reviewed_at
                    FROM bb_reviewed_pr_commits
                    ORDER BY reviewed_at DESC
                    LIMIT :limit
                """), {"limit": limit}).mappings().all()

                for row in rows:
                    ts = row['reviewed_at']
                    ts_str = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                    reviews.append({
                        'repo': row['repo'],
                        'pr_id': row['pr_id'],
                        'commit_sha': (row['commit_sha'] or '')[:8],
                        'reviewed_at': ts_str,
                        'link': f"https://bitbucket.org/{workspace}/{row['repo']}/pull-requests/{row['pr_id']}"
                    })
        except Exception:
            pass  # Table may not exist yet if Bitbucket monitor hasn't run

        now = datetime.now()
        def _days_ago(ts_str):
            try:
                return (now - datetime.fromisoformat(ts_str)).days
            except Exception:
                return 999

        stats = {
            'total_reviews': len(reviews),
            'reviews_last_24h': sum(1 for r in reviews if _days_ago(r['reviewed_at']) < 1),
            'reviews_last_week': sum(1 for r in reviews if _days_ago(r['reviewed_at']) < 7),
        }

        return jsonify({'reviews': reviews, 'stats': stats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# TEAM MEMBERS
# ============================================================================

@app.route('/api/team-members')
def get_team_members():
    """Get all team members."""
    try:
        members = db.get_team_members()
        return jsonify(members)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/team-members', methods=['POST'])
def create_team_member():
    """Create a new team member."""
    try:
        data = request.json
        if not data.get('display_name'):
            return jsonify({"error": "display_name is required"}), 400
        member_id = db.create_team_member(data)
        return jsonify({"success": True, "id": member_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/team-members/<int:member_id>', methods=['PUT'])
def update_team_member(member_id):
    """Update a team member by id."""
    try:
        data = request.json
        if not data.get('display_name'):
            return jsonify({"error": "display_name is required"}), 400
        db.update_team_member(member_id, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/team-members/<int:member_id>', methods=['DELETE'])
def delete_team_member(member_id):
    """Delete a team member by id."""
    try:
        db.delete_team_member(member_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/team-members/lookup')
def lookup_team_member():
    """
    Search Jira and Slack by name/email query.
    Used by the Add Member modal so users never need to know account IDs.

    ?q=<name or email>
    Returns {jira_matches: [...], slack_matches: [...], errors: [...]}
    """
    try:
        import requests as http_requests
        from slack_sdk import WebClient as SlackClient

        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({"error": "q is required"}), 400

        jira_url = os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')
        email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL', '')
        token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN', '')
        slack_token = os.getenv('SLACK_BOT_TOKEN', '')

        errors = []
        jira_matches = []
        slack_matches = []

        # --- Jira user search ---
        # Tries three endpoints and merges results, deduplicated by accountId.
        # Different Jira Cloud configs return different users from each endpoint:
        #   • user/picker   — what Jira UI uses for @mentions; most reliable
        #   • user/search   — general search by name/email
        #   • users/search  — broader visibility, catches users the others miss
        if jira_url and email and token:
            try:
                jira_auth = (email, token)
                seen_ids = {}  # accountId → merged user dict

                def _merge_user(u, avatar_key="24x24"):
                    """Add or enrich a user entry in seen_ids."""
                    aid = u.get("accountId", "")
                    if not aid:
                        return
                    # Exclude service/bot accounts only
                    if u.get("accountType") == "app":
                        return
                    existing = seen_ids.get(aid, {})
                    seen_ids[aid] = {
                        "account_id": aid,
                        "display_name": u.get("displayName") or existing.get("display_name", ""),
                        "email": u.get("emailAddress") or existing.get("email", ""),
                        "avatar_url": (
                            (u.get("avatarUrls") or {}).get(avatar_key)
                            or u.get("avatarUrl", "")
                            or existing.get("avatar_url", "")
                        ),
                    }

                # 1. user/picker — Jira's own @-mention autocomplete API
                r = http_requests.get(
                    f"{jira_url}/rest/api/3/user/picker",
                    auth=jira_auth,
                    params={"query": q, "maxResults": 10, "showAvatar": "true"},
                    timeout=10,
                )
                if r.ok:
                    for u in r.json().get("users", []):
                        _merge_user(u, avatar_key="24x24")
                else:
                    errors.append(f"Jira picker error {r.status_code}")

                # 2. user/search — standard user search
                r = http_requests.get(
                    f"{jira_url}/rest/api/3/user/search",
                    auth=jira_auth,
                    params={"query": q, "maxResults": 10},
                    timeout=10,
                )
                if r.ok:
                    for u in r.json():
                        _merge_user(u)
                else:
                    errors.append(f"Jira /user/search error {r.status_code}")

                # 3. user/assignable/search — project-scoped; try each key individually
                #    (ATLASSIAN_PROJECT_KEY may be comma-separated e.g. "ECD,MDP")
                project_keys = [k.strip() for k in os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',') if k.strip()]
                for pk in project_keys:
                    r = http_requests.get(
                        f"{jira_url}/rest/api/3/user/assignable/search",
                        auth=jira_auth,
                        params={"project": pk, "query": q, "maxResults": 10},
                        timeout=10,
                    )
                    if r.ok:
                        for u in r.json():
                            _merge_user(u)
                    # 404 = project key not found; 403 = no perms — silently skip both

                # Filter by query (picker may return broad results)
                q_lower = q.lower()
                jira_matches = [
                    u for u in seen_ids.values()
                    if q_lower in u["display_name"].lower() or q_lower in u["email"].lower()
                ][:10]

            except Exception as exc:
                errors.append(f"Jira lookup failed: {exc}")
        else:
            errors.append("Jira not configured (ATLASSIAN_SERVICE_ACCOUNT_EMAIL / TOKEN / JIRA_INSTANCE_URL missing)")

        # --- Slack user search (filter workspace list locally) ---
        if slack_token:
            try:
                sc = SlackClient(token=slack_token)
                q_lower = q.lower()
                cursor = None
                while True:
                    kwargs = {"limit": 200}
                    if cursor:
                        kwargs["cursor"] = cursor
                    resp = sc.users_list(**kwargs)
                    for member in resp.get('members', []):
                        if member.get('deleted') or member.get('is_bot') or member['id'] == 'USLACKBOT':
                            continue
                        profile = member.get('profile', {})
                        real_name = profile.get('real_name', '')
                        display_name = profile.get('display_name', '')
                        member_email = profile.get('email', '')
                        if (q_lower in real_name.lower()
                                or q_lower in display_name.lower()
                                or q_lower in member_email.lower()):
                            slack_matches.append({
                                "user_id": member['id'],
                                "display_name": display_name or real_name,
                                "real_name": real_name,
                                "email": member_email,
                                "avatar_url": profile.get('image_48', ''),
                            })
                    cursor = resp.get('response_metadata', {}).get('next_cursor')
                    if not cursor or len(slack_matches) >= 10:
                        break
                slack_matches = slack_matches[:10]
            except Exception as exc:
                errors.append(f"Slack lookup failed: {exc}")
        else:
            errors.append("Slack not configured (SLACK_BOT_TOKEN missing)")

        return jsonify({
            "jira_matches": jira_matches,
            "slack_matches": slack_matches,
            "errors": errors,
            "query": q,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/team-members/reconcile', methods=['POST'])
def reconcile_team_members():
    """
    Fetch Jira project assignees + Slack workspace users, then use Claude to
    suggest Slack ↔ Jira matches for unmapped members.
    """
    try:
        import anthropic
        import requests as http_requests
        from slack_sdk import WebClient as SlackClient

        jira_url = os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')
        email = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_EMAIL', '')
        token = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN', '')
        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '')
        slack_token = os.getenv('SLACK_BOT_TOKEN', '')

        errors = []

        # --- Step 1: Fetch Jira project assignees from recent tickets ---
        jira_users = []
        if jira_url and email and token and project_key:
            try:
                resp = http_requests.post(
                    f"{jira_url}/rest/api/3/search/jql",
                    auth=(email, token),
                    json={
                        "jql": f"project = {project_key} AND assignee is not EMPTY ORDER BY updated DESC",
                        "fields": ["assignee"],
                        "maxResults": 200,
                    },
                    timeout=30,
                )
                if resp.ok:
                    seen = set()
                    for issue in resp.json().get('issues', []):
                        assignee = issue.get('fields', {}).get('assignee') or {}
                        aid = assignee.get('accountId')
                        if aid and aid not in seen:
                            seen.add(aid)
                            jira_users.append({
                                'account_id': aid,
                                'display_name': assignee.get('displayName', ''),
                                'email': assignee.get('emailAddress', ''),
                            })
                else:
                    errors.append(f"Jira API error {resp.status_code}: {resp.text[:200]}")
            except Exception as exc:
                errors.append(f"Jira fetch failed: {exc}")
        else:
            errors.append("Missing ATLASSIAN_SERVICE_ACCOUNT_EMAIL / TOKEN / PROJECT_KEY / JIRA_INSTANCE_URL")

        # --- Step 2: Fetch Slack workspace members ---
        slack_users = []
        if slack_token:
            try:
                sc = SlackClient(token=slack_token)
                cursor = None
                while True:
                    kwargs = {"limit": 200}
                    if cursor:
                        kwargs["cursor"] = cursor
                    resp = sc.users_list(**kwargs)
                    for member in resp.get('members', []):
                        if member.get('deleted') or member.get('is_bot') or member['id'] == 'USLACKBOT':
                            continue
                        profile = member.get('profile', {})
                        name = profile.get('display_name') or profile.get('real_name') or ''
                        slack_users.append({
                            'user_id': member['id'],
                            'display_name': name,
                            'real_name': profile.get('real_name', ''),
                            'email': profile.get('email', ''),
                        })
                    cursor = resp.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
            except Exception as exc:
                errors.append(f"Slack fetch failed: {exc}")
        else:
            errors.append("Missing SLACK_BOT_TOKEN")

        if not jira_users and not slack_users:
            return jsonify({"error": "Could not fetch users.", "details": errors}), 400

        # --- Step 3: Filter out already-mapped users ---
        existing = db.get_team_members()
        mapped_jira_ids = {m['jira_account_id'] for m in existing if m.get('jira_account_id')}
        mapped_slack_ids = {m['slack_user_id'] for m in existing if m.get('slack_user_id')}

        unmapped_jira = [u for u in jira_users if u['account_id'] not in mapped_jira_ids]
        available_slack = [u for u in slack_users if u['user_id'] not in mapped_slack_ids]

        if not unmapped_jira:
            return jsonify({
                'suggestions': [],
                'message': 'All Jira users are already mapped!',
                'jira_count': len(jira_users),
                'slack_count': len(slack_users),
            })

        # --- Step 4: Call Claude to suggest matches ---
        anthropic_client = anthropic.Anthropic()
        prompt = f"""Match each Jira user to their corresponding Slack user based on name and email similarity.

Jira users to match:
{json.dumps(unmapped_jira, indent=2)}

Available Slack users:
{json.dumps(available_slack, indent=2)}

Rules:
- Exact email match → "high" confidence
- Clear name match (same person, different formatting) → "medium" confidence
- Partial name similarity → "low" confidence
- Omit a Jira user if no reasonable match exists

Return ONLY a JSON array (no markdown, no explanation):
[
  {{
    "jira_account_id": "...",
    "jira_display_name": "...",
    "slack_user_id": "...",
    "slack_display_name": "...",
    "email": "...",
    "confidence": "high|medium|low",
    "reason": "brief explanation"
  }}
]"""

        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])

        suggestions = json.loads(response_text)

        return jsonify({
            'suggestions': suggestions,
            'jira_count': len(jira_users),
            'slack_count': len(slack_users),
            'unmapped_count': len(unmapped_jira),
            'warnings': errors if errors else None,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SPRINT PULSE
# ============================================================================

def _fetch_sprint_pulse_data(req, project_key, jira_base, headers, jira_web_url=''):
    """
    Inner logic for sprint pulse. Returns a plain dict (not a Flask Response).
    Called by both get_sprint_pulse() and the agent sprint-report endpoint.
    """
    # ── 1. Fetch sprint issues via JQL (paginated) ──────────────────────────
    all_issues = []
    next_page_token = None
    req_fields = [
        "summary", "status", "priority", "assignee",
        "timeoriginalestimate", "timespent", "duedate",
        "customfield_10020",
    ]

    while True:
        payload = {
            "jql": f"project = {project_key} AND sprint in openSprints() AND issuetype not in subTaskIssueTypes() ORDER BY created ASC",
            "fields": req_fields,
            "maxResults": 100,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token

        r = req.post(
            f"{jira_base}/rest/api/3/search/jql",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if not r.ok:
            raise RuntimeError(f"JQL search failed: {r.status_code} {r.text[:300]}")

        data = r.json()
        page = data.get('issues', [])
        all_issues.extend(page)
        next_page_token = data.get('nextPageToken')
        if not next_page_token or not page:
            break

    if not all_issues:
        raise LookupError(f"No active sprint found for project {project_key}")

    # ── 2. Extract sprint metadata from customfield_10020 ───────────────────
    sprint_info = None
    for issue in all_issues:
        cf = (issue.get('fields') or {}).get('customfield_10020') or []
        active = [s for s in cf if isinstance(s, dict) and s.get('state') == 'active']
        if active:
            sprint_info = active[0]
            break

    if not sprint_info:
        for issue in all_issues:
            cf = (issue.get('fields') or {}).get('customfield_10020') or []
            if cf and isinstance(cf[0], dict):
                sprint_info = cf[0]
                break

    if not sprint_info:
        sprint_info = {}

    sprint = {
        'id':         sprint_info.get('id', ''),
        'name':       sprint_info.get('name', 'Active Sprint'),
        'start_date': (sprint_info.get('startDate') or '')[:10] or None,
        'end_date':   (sprint_info.get('endDate') or '')[:10] or None,
        'state':      sprint_info.get('state', 'active'),
        'board_name': f"{project_key} Board",
    }

    # ── 3. Discover project statuses and build weight map ───────────────────
    status_weights = {}
    r = req.get(
        f"{jira_base}/rest/api/3/project/{project_key}/statuses",
        headers=headers,
        timeout=15,
    )
    if r.ok:
        seen = {}
        for issue_type_data in r.json():
            for s in issue_type_data.get('statuses', []):
                name = s.get('name', '')
                cat_key = (s.get('statusCategory') or {}).get('key', 'indeterminate')
                seen[name] = cat_key

        def _weight(name, cat_key):
            nl = name.lower()
            if cat_key == 'done':
                return 1.0
            if 'pending approval' in nl:
                return 0.92
            if 'changes' in nl or 'rework' in nl:
                return 0.88
            if 'qa' in nl or ('test' in nl and 'ready' not in nl):
                return 0.85
            if 'review' in nl and 'ready' not in nl:
                return 0.75
            if 'progress' in nl and 'ready' not in nl:
                return 0.35
            if 'blocked' in nl or 'impediment' in nl:
                return 0.02
            if cat_key == 'indeterminate':
                return 0.20
            return 0.05

        for name, cat_key in seen.items():
            status_weights[name] = _weight(name, cat_key)

    for issue in all_issues:
        s_obj = (issue.get('fields') or {}).get('status') or {}
        name = s_obj.get('name', '')
        if name and name not in status_weights:
            cat_key = (s_obj.get('statusCategory') or {}).get('key', 'indeterminate')
            status_weights[name] = _weight(name, cat_key)

    # ── 4. Group by developer ────────────────────────────────────────────────
    devs: dict = {}
    for issue in all_issues:
        f = issue.get('fields') or {}
        assignee = f.get('assignee') or {}
        account_id = assignee.get('accountId') or 'unassigned'
        display_name = assignee.get('displayName') or 'Unassigned'

        if account_id not in devs:
            devs[account_id] = {'account_id': account_id, 'name': display_name, 'tickets': []}

        status_obj = f.get('status') or {}
        priority_obj = f.get('priority') or {}
        est_sec = f.get('timeoriginalestimate') or 0
        spent_sec = f.get('timespent') or 0

        devs[account_id]['tickets'].append({
            'key':            issue.get('key', ''),
            'summary':        f.get('summary', ''),
            'status':         status_obj.get('name', 'Unknown'),
            'priority':       (priority_obj.get('name') or 'Medium'),
            'estimate_hours': round(est_sec / 3600, 2) if est_sec else 0,
            'logged_hours':   round(spent_sec / 3600, 2) if spent_sec else 0,
            'due_date':       f.get('duedate'),
        })

    dev_list = sorted(devs.values(), key=lambda d: d['name'])

    return {
        'sprint':         sprint,
        'developers':     dev_list,
        'status_weights': status_weights,
        'project_key':    project_key,
        'jira_url':       jira_web_url or '',
        'last_updated':   datetime.utcnow().isoformat() + 'Z',
    }


@app.route('/api/sprint-pulse')
def get_sprint_pulse():
    """
    Fetch active sprint data from Jira for Sprint Pulse dashboard.

    Uses the core JQL REST API (same as all other endpoints) — avoids the
    Agile REST API (/rest/agile/1.0) which returns 401 scope errors with
    service account Basic Auth. Sprint metadata comes from customfield_10020
    on the issues themselves. All scoring is done client-side in Vue.
    """
    try:
        import requests as req
        from src.tools.base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID, JIRA_WEB_URL

        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',')[0].strip()
        if not project_key:
            return jsonify({"error": "ATLASSIAN_PROJECT_KEY not configured"}), 400

        jira_base = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
        headers = get_jira_auth_headers()
        jira_web_url = JIRA_WEB_URL or os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')

        result = _fetch_sprint_pulse_data(req, project_key, jira_base, headers, jira_web_url)
        return jsonify(result)

    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ============================================================================
# SPRINT BURNDOWN
# ============================================================================

@app.route('/api/sprint-burndown')
def get_sprint_burndown():
    """
    Build a historical stacked burndown from Jira changelogs.
    For each business day since sprint start, replays each ticket's status
    changelog and buckets hours into: complete / verifying / active / queued / blocked.
    Changelogs are fetched in parallel (ThreadPoolExecutor) to keep latency low.
    """
    try:
        import requests as req
        from src.tools.base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID
        from datetime import datetime, timedelta
        from concurrent.futures import ThreadPoolExecutor, as_completed

        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',')[0].strip()
        if not project_key:
            return jsonify({"error": "ATLASSIAN_PROJECT_KEY not configured"}), 400

        jira_base = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
        headers = get_jira_auth_headers()

        result = _fetch_sprint_burndown_data(req, project_key, jira_base, headers)
        return jsonify(result)

    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


def _fetch_sprint_burndown_data(req, project_key, jira_base, headers):
    """
    Inner logic for sprint burndown. Returns a plain dict (not a Flask Response).
    Called by both get_sprint_burndown() and the agent sprint-report endpoint.
    """
    import re as _re
    from datetime import datetime, timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # ── 1. Fetch sprint issues ────────────────────────────────────────────────
    all_issues, next_page_token = [], None
    req_fields = ["summary", "status", "timeoriginalestimate", "customfield_10020"]
    while True:
        payload = {
            "jql": f"project = {project_key} AND sprint in openSprints() AND issuetype not in subTaskIssueTypes() ORDER BY created ASC",
            "fields": req_fields, "maxResults": 100,
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        r = req.post(f"{jira_base}/rest/api/3/search/jql", headers=headers, json=payload, timeout=30)
        if not r.ok:
            raise RuntimeError(f"JQL search failed: {r.status_code}")
        data = r.json()
        page = data.get('issues', [])
        all_issues.extend(page)
        next_page_token = data.get('nextPageToken')
        if not next_page_token or not page:
            break

    if not all_issues:
        raise LookupError("No active sprint issues found")

    # ── 2. Extract sprint dates ───────────────────────────────────────────────
    sprint_info = next(
        (s for i in all_issues
         for s in ((i.get('fields') or {}).get('customfield_10020') or [])
         if isinstance(s, dict) and s.get('state') == 'active'),
        None
    )
    if not sprint_info:
        raise LookupError("No active sprint metadata found")

    sprint_start = sprint_info.get('startDate', '')[:10]
    sprint_end   = sprint_info.get('endDate',   '')[:10]
    sprint_start_dt = datetime.strptime(sprint_start, '%Y-%m-%d').date()
    sprint_end_dt   = datetime.strptime(sprint_end,   '%Y-%m-%d').date()
    today       = datetime.utcnow().date()
    sprint_id   = sprint_info.get('id')
    sprint_name = sprint_info.get('name', '')

    # ── 3. Business-day range ─────────────────────────────────────────────────
    def biz_days_range(start, end):
        days, cur = [], start
        while cur <= end:
            if cur.weekday() < 5:
                days.append(cur)
            cur += timedelta(days=1)
        return days

    biz_days_list  = biz_days_range(sprint_start_dt, min(today, sprint_end_dt))
    total_biz_days = len(biz_days_range(sprint_start_dt, sprint_end_dt))

    def est_hours(issue):
        sec = (issue.get('fields') or {}).get('timeoriginalestimate') or 0
        return sec / 3600 if sec else 4

    total_hours = sum(est_hours(i) for i in all_issues)

    # ── 4. Fetch changelogs in parallel ───────────────────────────────────────
    def fetch_cl(key):
        try:
            r2 = req.get(
                f"{jira_base}/rest/api/3/issue/{key}/changelog",
                headers=headers, params={"maxResults": 200}, timeout=15
            )
            return key, r2.json().get('values', []) if r2.ok else []
        except Exception:
            return key, []

    changelogs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_cl, i['key']): i['key'] for i in all_issues}
        for fut in as_completed(futs, timeout=50):
            try:
                key, entries = fut.result()
                changelogs[key] = entries
            except Exception:
                pass

    # ── 5. Detect scope creep ─────────────────────────────────────────────────
    _offset_re = _re.compile(r'([+-])(\d{2})(\d{2})$')

    def _parse_jira_dt(s):
        s = s.replace('Z', '+00:00')
        s = _offset_re.sub(r'\1\2:\3', s)
        return datetime.fromisoformat(s).replace(tzinfo=None)

    sprint_start_dt_end = datetime.combine(sprint_start_dt, datetime.max.time())
    scope_additions = []
    sprint_join_dt  = {}

    for issue in all_issues:
        key   = issue['key']
        hours = est_hours(issue)
        join_dt = None
        for entry in changelogs.get(key, []):
            ts_str = entry.get('created', '')
            for item in entry.get('items', []):
                field = (item.get('field') or '').lower()
                if field not in ('sprint', 'customfield_10020'):
                    continue
                to_str = item.get('toString') or ''
                id_match   = sprint_id and (
                    f'id={sprint_id},' in to_str or f'id={sprint_id}]' in to_str
                )
                name_match = sprint_name and sprint_name in to_str
                if not (id_match or name_match):
                    continue
                try:
                    dt = _parse_jira_dt(ts_str)
                except Exception:
                    continue
                if dt > sprint_start_dt_end:
                    if join_dt is None or dt < join_dt:
                        join_dt = dt
        sprint_join_dt[key] = join_dt
        if join_dt is not None:
            scope_additions.append({
                'key': key,
                'hours': round(hours, 1),
                'added_date': join_dt.date().isoformat(),
            })

    added_hours   = round(sum(a['hours'] for a in scope_additions), 1)
    initial_hours = round(total_hours - added_hours, 1)

    # ── 6. Status → bucket ────────────────────────────────────────────────────
    def status_bucket(name):
        nl = (name or '').lower()
        if any(w in nl for w in ('complete', 'done', 'closed', 'shipped')):
            return 'complete'
        if 'block' in nl or 'impediment' in nl:
            return 'blocked'
        if 'qa' in nl or ('test' in nl and 'ready' not in nl):
            return 'verifying'
        if 'review' in nl and 'ready' not in nl:
            return 'verifying'
        if 'progress' in nl or 'changes' in nl or 'rework' in nl:
            return 'active'
        return 'queued'

    def status_at_day(issue_key, day_date, current_status):
        day_end = datetime.combine(day_date, datetime.max.time())
        events = []
        for entry in changelogs.get(issue_key, []):
            created_str = entry.get('created', '')
            for item in entry.get('items', []):
                if item.get('field') == 'status':
                    try:
                        dt = _parse_jira_dt(created_str)
                        events.append((dt, item.get('fromString', ''), item.get('toString', '')))
                    except Exception:
                        pass
        events.sort(key=lambda e: e[0])
        status = events[0][1] if events else current_status
        for event_dt, _, to_s in events:
            if event_dt <= day_end:
                status = to_s
            else:
                break
        return status

    # ── 7. Daily snapshots ────────────────────────────────────────────────────
    scope_by_day = []
    for day in biz_days_list:
        day_scope = sum(
            est_hours(i) for i in all_issues
            if sprint_join_dt.get(i['key']) is None
            or sprint_join_dt[i['key']].date() <= day
        )
        scope_by_day.append(round(day_scope, 1))

    daily_snapshots = []
    for day_idx, day in enumerate(biz_days_list):
        buckets = {'complete': 0, 'verifying': 0, 'active': 0, 'queued': 0, 'blocked': 0}
        for issue in all_issues:
            cur_status = (issue.get('fields') or {}).get('status', {}).get('name', 'Ready For Development')
            s = status_at_day(issue['key'], day, cur_status)
            buckets[status_bucket(s)] += est_hours(issue)

        remaining = buckets['verifying'] + buckets['active'] + buckets['queued'] + buckets['blocked']
        ideal = initial_hours * max(0, 1 - (day_idx + 1) / total_biz_days)
        daily_snapshots.append({
            'date':      day.isoformat(),
            'complete':  round(buckets['complete'],  1),
            'verifying': round(buckets['verifying'], 1),
            'active':    round(buckets['active'],    1),
            'queued':    round(buckets['queued'],    1),
            'blocked':   round(buckets['blocked'],   1),
            'remaining': round(remaining,            1),
            'ideal':     round(ideal,                1),
            'scope':     scope_by_day[day_idx],
        })

    today_snap = daily_snapshots[-1] if daily_snapshots else {}
    complete_h = today_snap.get('complete', 0)
    blocked_h  = today_snap.get('blocked',  0)
    remaining  = today_snap.get('remaining', 0)
    ideal_now  = today_snap.get('ideal',    0)

    return {
        'sprint':          {'name': sprint_info.get('name', ''), 'start_date': sprint_start, 'end_date': sprint_end},
        'daily_snapshots': daily_snapshots,
        'total_hours':     round(total_hours, 1),
        'initial_hours':   initial_hours,
        'added_hours':     added_hours,
        'added_tickets':   len(scope_additions),
        'scope_additions': scope_additions,
        'behind_hours':    round(remaining - ideal_now, 1),
        'blocked_hours':   round(blocked_h,  1),
        'complete_hours':  round(complete_h, 1),
        'complete_pct':    round(complete_h / total_hours * 100, 1) if total_hours else 0,
    }


# ============================================================================
# SPRINT PLANNING
# ============================================================================

@app.route('/api/sprint-planning/sprints')
def get_planning_sprints():
    """
    Return a list of future sprints for the project, extracted from Jira
    issue customfield_10020 (sprint field) via JQL — avoids needing the
    Agile REST API which throws 401 with Basic Auth service accounts.
    """
    try:
        import requests as req
        from src.tools.base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID

        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',')[0].strip()
        if not project_key:
            return jsonify({"error": "ATLASSIAN_PROJECT_KEY not configured"}), 400

        jira_base = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
        headers = get_jira_auth_headers()

        # Fetch a sample of future sprint issues just to extract sprint metadata
        r = req.post(
            f"{jira_base}/rest/api/3/search/jql",
            headers=headers,
            json={
                "jql": f"project = {project_key} AND sprint in futureSprints() ORDER BY created ASC",
                "fields": ["customfield_10020"],
                "maxResults": 100,
            },
            timeout=20,
        )
        if not r.ok:
            return jsonify({"error": f"JQL search failed: {r.status_code}"}), 500

        seen_ids = set()
        sprints = []
        for issue in r.json().get('issues', []):
            cf = (issue.get('fields') or {}).get('customfield_10020') or []
            for s in cf:
                if not isinstance(s, dict):
                    continue
                sprint_id = s.get('id')
                if sprint_id and sprint_id not in seen_ids and s.get('state') == 'future':
                    seen_ids.add(sprint_id)
                    sprints.append({
                        'id':         sprint_id,
                        'name':       s.get('name', f'Sprint {sprint_id}'),
                        'start_date': (s.get('startDate') or '')[:10] or None,
                        'end_date':   (s.get('endDate') or '')[:10] or None,
                        'state':      s.get('state', 'future'),
                    })

        sprints.sort(key=lambda s: s.get('start_date') or '')
        return jsonify({"sprints": sprints})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/sprint-planning')
def get_sprint_planning():
    """
    Full capacity planning breakdown for a selected future sprint.
    ?sprint_id=<id>   — required: Jira sprint integer ID
    ?rollover=1       — optional (default 1): include rollover hours from active sprint
    """
    try:
        import requests as req
        from src.tools.base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID
        from datetime import datetime, timedelta

        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',')[0].strip()
        if not project_key:
            return jsonify({"error": "ATLASSIAN_PROJECT_KEY not configured"}), 400

        sprint_id_str = request.args.get('sprint_id', '').strip()
        if not sprint_id_str:
            return jsonify({"error": "sprint_id is required"}), 400

        include_rollover = request.args.get('rollover', '1') != '0'

        jira_base = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
        headers = get_jira_auth_headers()

        # ── 1. Fetch team members (dev/wa/tech_lead only, active) ─────────────
        team_rows = db.get_team_members(active_only=True)
        PLANNING_ROLES = {'dev', 'wa', 'tech_lead'}
        team_by_jira_id = {}
        for m in team_rows:
            jira_id = m.get('jira_account_id')
            role = (m.get('role') or '').lower()
            if jira_id and role in PLANNING_ROLES:
                team_by_jira_id[jira_id] = {
                    'id':                   m['id'],
                    'display_name':         m['display_name'],
                    'role':                 role,
                    'weekly_capacity_hours': float(m.get('weekly_capacity_hours') or 40.0),
                    'jira_account_id':      jira_id,
                }

        # ── 2. Fetch future sprint issues ──────────────────────────────────────
        req_fields = ["summary", "status", "assignee", "timeoriginalestimate", "duedate", "customfield_10020"]
        all_issues, next_page_token = [], None
        sprint_info = None
        while True:
            payload = {
                "jql": f"project = {project_key} AND sprint = {sprint_id_str} ORDER BY created ASC",
                "fields": req_fields,
                "maxResults": 100,
            }
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            r = req.post(f"{jira_base}/rest/api/3/search/jql", headers=headers, json=payload, timeout=30)
            if not r.ok:
                return jsonify({"error": f"JQL search failed: {r.status_code} {r.text[:200]}"}), 500
            data = r.json()
            page = data.get('issues', [])
            all_issues.extend(page)
            next_page_token = data.get('nextPageToken')
            if not next_page_token or not page:
                break

        # Extract sprint metadata from first issue's customfield_10020
        for issue in all_issues:
            cf = (issue.get('fields') or {}).get('customfield_10020') or []
            for s in cf:
                if isinstance(s, dict) and str(s.get('id', '')) == str(sprint_id_str):
                    sprint_info = s
                    break
            if sprint_info:
                break
        if not sprint_info and all_issues:
            cf = (all_issues[0].get('fields') or {}).get('customfield_10020') or []
            if cf:
                sprint_info = cf[0]

        sprint_info = sprint_info or {}
        start_date_str = (sprint_info.get('startDate') or '')[:10]
        end_date_str   = (sprint_info.get('endDate') or '')[:10]

        # Calculate sprint weeks (working days / 5)
        sprint_weeks = 2.0  # default
        if start_date_str and end_date_str:
            try:
                sd = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                calendar_days = (ed - sd).days + 1
                sprint_weeks = max(1.0, round(calendar_days / 7, 1))
            except Exception:
                pass

        # ── 3. Group future sprint issues by assignee ──────────────────────────
        def _est_hours(issue):
            sec = (issue.get('fields') or {}).get('timeoriginalestimate') or 0
            return round(sec / 3600, 1)

        devs: dict = {}
        unassigned_tickets = []

        for issue in all_issues:
            f = issue.get('fields') or {}
            assignee = f.get('assignee') or {}
            account_id = assignee.get('accountId')
            status_obj = f.get('status') or {}
            ticket = {
                'key':            issue.get('key', ''),
                'summary':        f.get('summary', ''),
                'status':         status_obj.get('name', 'Unknown'),
                'status_cat':     (status_obj.get('statusCategory') or {}).get('key', 'new'),
                'estimate_hours': _est_hours(issue),
                'due_date':       f.get('duedate'),
            }

            if account_id and account_id in team_by_jira_id:
                if account_id not in devs:
                    devs[account_id] = {**team_by_jira_id[account_id], 'tickets': []}
                devs[account_id]['tickets'].append(ticket)
            else:
                # Either unassigned or assigned to someone not in team DB
                display_name = assignee.get('displayName', 'Unassigned') if account_id else 'Unassigned'
                ticket['assignee_name'] = display_name
                unassigned_tickets.append(ticket)

        # ── 4. Rollover: capacity-forecast from active sprint ─────────────────
        # Algorithm:
        #   1. Fetch active sprint tickets with timespent so we know remaining work
        #      per ticket (estimate − logged), not just raw estimate.
        #   2. Compute remaining business days to active sprint end.
        #   3. Per developer: remaining_capacity = days_left × (weekly_hours / 5).
        #   4. Sort their unfinished tickets by priority (Highest first), then due date.
        #   5. Greedily fill capacity: tickets that fit → will finish; overflow → rollover.
        # Only tickets that genuinely can't be completed given available time roll over.
        rollover_by_jira_id: dict = {}
        active_sprint_end_str = None
        active_sprint_days_remaining = None

        if include_rollover:
            try:
                from datetime import date as _date

                # Fetch active sprint issues (priority + timespent needed for algo)
                active_issues, next_tok = [], None
                while True:
                    payload2 = {
                        "jql": f"project = {project_key} AND sprint in openSprints() ORDER BY priority ASC",
                        "fields": ["summary", "status", "assignee", "timeoriginalestimate",
                                   "timespent", "duedate", "priority", "customfield_10020"],
                        "maxResults": 200,
                    }
                    if next_tok:
                        payload2["nextPageToken"] = next_tok
                    r2 = req.post(f"{jira_base}/rest/api/3/search/jql",
                                  headers=headers, json=payload2, timeout=30)
                    if not r2.ok:
                        break
                    d2 = r2.json()
                    active_issues.extend(d2.get('issues', []))
                    next_tok = d2.get('nextPageToken')
                    if not next_tok or not d2.get('issues'):
                        break

                # Extract active sprint end date from customfield_10020
                today = _date.today()
                active_sprint_end = None
                for issue in active_issues:
                    cf = (issue.get('fields') or {}).get('customfield_10020') or []
                    for s in cf:
                        if isinstance(s, dict) and s.get('state') == 'active':
                            end_str = (s.get('endDate') or '')[:10]
                            if end_str:
                                try:
                                    active_sprint_end = datetime.strptime(end_str, '%Y-%m-%d').date()
                                    active_sprint_end_str = end_str
                                except Exception:
                                    pass
                            break
                    if active_sprint_end:
                        break

                # Remaining business days (Mon–Fri) from today through sprint end
                if active_sprint_end:
                    days_range = (active_sprint_end - today).days + 1
                    biz_days_left = sum(
                        1 for i in range(max(days_range, 0))
                        if (today + timedelta(days=i)).weekday() < 5
                    )
                    active_sprint_days_remaining = max(biz_days_left, 0)
                else:
                    active_sprint_days_remaining = 5  # fallback: 1 week

                PRIORITY_ORDER = {'Highest': 1, 'High': 2, 'Medium': 3, 'Low': 4, 'Lowest': 5}

                # Group unfinished active-sprint tickets by developer
                active_by_dev: dict = {}
                for issue in active_issues:
                    f = issue.get('fields') or {}
                    account_id = (f.get('assignee') or {}).get('accountId')
                    if not account_id or account_id not in team_by_jira_id:
                        continue
                    status_cat = ((f.get('status') or {}).get('statusCategory') or {}).get('key', 'new')
                    if status_cat == 'done':
                        continue  # already finished
                    est_sec   = f.get('timeoriginalestimate') or 0
                    spent_sec = f.get('timespent') or 0
                    remaining_work = max(0.0, round((est_sec - spent_sec) / 3600, 1))
                    if remaining_work == 0:
                        continue  # fully logged
                    priority_name = (f.get('priority') or {}).get('name', 'Medium')
                    status_obj = f.get('status') or {}
                    if account_id not in active_by_dev:
                        active_by_dev[account_id] = []
                    active_by_dev[account_id].append({
                        'key':             issue.get('key', ''),
                        'summary':         f.get('summary', ''),
                        'status':          status_obj.get('name', 'Unknown'),
                        'priority':        priority_name,
                        'priority_order':  PRIORITY_ORDER.get(priority_name, 3),
                        'estimate_hours':  round(est_sec / 3600, 1),
                        'logged_hours':    round(spent_sec / 3600, 1),
                        'remaining_hours': remaining_work,
                        'due_date':        f.get('duedate'),
                        '_sort_due':       f.get('duedate') or '9999-12-31',
                    })

                # Greedy per-developer allocation
                for account_id, tickets in active_by_dev.items():
                    member = team_by_jira_id[account_id]
                    daily_hours = member['weekly_capacity_hours'] / 5.0
                    remaining_cap = round(daily_hours * active_sprint_days_remaining, 1)

                    # Higher priority first; ties broken by due date (earliest first)
                    tickets.sort(key=lambda t: (t['priority_order'], t['_sort_due']))

                    bucket = remaining_cap
                    will_rollover = []
                    for t in tickets:
                        if bucket >= t['remaining_hours']:
                            bucket = round(bucket - t['remaining_hours'], 1)
                            # fits — dev can finish it this sprint
                        else:
                            # over capacity — predict this ticket rolls over
                            # partial: only the hours that exceed capacity carry forward
                            overage = round(t['remaining_hours'] - max(bucket, 0), 1)
                            bucket = 0
                            will_rollover.append({
                                'key':             t['key'],
                                'summary':         t['summary'],
                                'status':          t['status'],
                                'priority':        t['priority'],
                                'estimate_hours':  t['estimate_hours'],
                                'logged_hours':    t['logged_hours'],
                                'remaining_hours': t['remaining_hours'],
                                'rollover_hours':  overage,
                                'due_date':        t['due_date'],
                            })
                    if will_rollover:
                        rollover_by_jira_id[account_id] = will_rollover

            except Exception:
                pass  # rollover failure is non-fatal

        # ── 5. Build developer summaries ───────────────────────────────────────
        dev_list = []
        for account_id, dev in devs.items():
            planned_hours = sum(t['estimate_hours'] for t in dev['tickets'])
            rollover_tickets = rollover_by_jira_id.get(account_id, [])
            rollover_hours = sum(r['rollover_hours'] for r in rollover_tickets)
            capacity_hours = dev['weekly_capacity_hours'] * sprint_weeks

            dev_list.append({
                'id':                   dev['id'],
                'jira_account_id':      account_id,
                'display_name':         dev['display_name'],
                'role':                 dev['role'],
                'weekly_capacity_hours': dev['weekly_capacity_hours'],
                'capacity_hours':       round(capacity_hours, 1),
                'planned_hours':        round(planned_hours, 1),
                'rollover_hours':       round(rollover_hours, 1),
                'total_load_hours':     round(planned_hours + rollover_hours, 1),
                'tickets':              dev['tickets'],
                'rollover_tickets':     rollover_tickets,
            })

        # Also include team members with no future sprint tickets yet
        for jira_id, m in team_by_jira_id.items():
            if jira_id not in devs:
                capacity_hours = m['weekly_capacity_hours'] * sprint_weeks
                rollover_tickets = rollover_by_jira_id.get(jira_id, [])
                rollover_hours = sum(r['rollover_hours'] for r in rollover_tickets)
                dev_list.append({
                    'id':                   m['id'],
                    'jira_account_id':      jira_id,
                    'display_name':         m['display_name'],
                    'role':                 m['role'],
                    'weekly_capacity_hours': m['weekly_capacity_hours'],
                    'capacity_hours':       round(capacity_hours, 1),
                    'planned_hours':        0.0,
                    'rollover_hours':       round(rollover_hours, 1),
                    'total_load_hours':     round(rollover_hours, 1),
                    'tickets':              [],
                    'rollover_tickets':     rollover_tickets,
                })

        dev_list.sort(key=lambda d: d['display_name'])

        return jsonify({
            'sprint': {
                'id':         sprint_info.get('id', sprint_id_str),
                'name':       sprint_info.get('name', f'Sprint {sprint_id_str}'),
                'start_date': start_date_str or None,
                'end_date':   end_date_str or None,
                'state':      sprint_info.get('state', 'future'),
                'weeks':      sprint_weeks,
            },
            'developers':         dev_list,
            'unassigned_tickets': unassigned_tickets,
            'rollover_enabled':   include_rollover,
            'rollover_context': {
                'active_sprint_end':           active_sprint_end_str,
                'active_sprint_days_remaining': active_sprint_days_remaining,
            } if include_rollover else None,
            'project_key':        project_key,
            'last_updated':       datetime.utcnow().isoformat() + 'Z',
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ============================================================================
# SETTINGS — Channel Configuration
# ============================================================================

# Report types the user can configure channels for
REPORT_TYPES = [
    {"report_type": "standup",         "label": "Daily Standup",        "env_fallback": "SLACK_CHANNEL_STANDUP"},
    {"report_type": "sla_violations",  "label": "SLA Violations",       "env_fallback": "SLACK_CHANNEL_STANDUP"},
    {"report_type": "sla_qa_alerts",   "label": "QA Alerts",            "env_fallback": "SLACK_CHANNEL_QA_ALERTS"},
    {"report_type": "timesheets",      "label": "Timesheets",           "env_fallback": "SLACK_TIMESHEET_CHANNEL"},
    {"report_type": "blocked_tickets", "label": "Blocked Tickets",      "env_fallback": "SLACK_CHANNEL_STANDUP"},
    {"report_type": "pm_logs",         "label": "PM Agent Logs",        "env_fallback": "SLACK_PM_AGENT_LOG_CHANNEL"},
]


@app.route('/api/settings/channels')
def get_channel_settings():
    """
    Return:
    - channels: list of all public Slack channels
    - config: current DB assignments per report type (+ env var fallback values)
    """
    try:
        import requests as req
        from sqlalchemy import text as sa_text

        slack_token = os.getenv('SLACK_BOT_TOKEN', '')
        channels = []
        slack_error = None

        if slack_token:
            try:
                cursor = None
                while True:
                    params = {"limit": 200, "exclude_archived": "true",
                              "types": "public_channel,private_channel"}
                    if cursor:
                        params["cursor"] = cursor
                    resp = req.get(
                        "https://slack.com/api/conversations.list",
                        headers={"Authorization": f"Bearer {slack_token}"},
                        params=params,
                        timeout=10,
                    )
                    data = resp.json()
                    if not data.get("ok"):
                        slack_error = data.get("error", "unknown")
                        break
                    for ch in data.get("channels", []):
                        channels.append({
                            "id": ch["id"],
                            "name": ch["name"],
                            "is_private": ch.get("is_private", False),
                        })
                    cursor = data.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
                channels.sort(key=lambda c: c["name"])
            except Exception as exc:
                slack_error = str(exc)
        else:
            slack_error = "SLACK_BOT_TOKEN not set"

        # Load current DB config
        db_config = {}
        try:
            with db.engine.connect() as conn:
                rows = conn.execute(sa_text(
                    "SELECT report_type, channel_id, channel_name, enabled FROM channel_config"
                )).mappings().all()
                for row in rows:
                    db_config[row["report_type"]] = dict(row)
        except Exception:
            pass

        # Build per-report-type config (merge DB + env fallback)
        config = {}
        for rt in REPORT_TYPES:
            key = rt["report_type"]
            db_row = db_config.get(key, {})
            env_val = os.getenv(rt["env_fallback"], "") if rt.get("env_fallback") else ""
            config[key] = {
                "channel_id":   db_row.get("channel_id") or None,
                "channel_name": db_row.get("channel_name") or None,
                "enabled":      db_row.get("enabled", True),
                "env_fallback": rt.get("env_fallback"),
                "env_value":    env_val or None,
            }

        return jsonify({
            "channels": channels,
            "config": config,
            "report_types": REPORT_TYPES,
            "slack_error": slack_error,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/settings/channels', methods=['POST'])
def save_channel_settings():
    """
    Save channel assignments.  Body: {assignments: [{report_type, channel_id, channel_name}]}
    """
    try:
        from sqlalchemy import text as sa_text

        data = request.json or {}
        assignments = data.get("assignments", [])
        now = datetime.utcnow()

        with db.engine.begin() as conn:
            for a in assignments:
                rt = a.get("report_type", "").strip()
                ch_id = a.get("channel_id") or None
                ch_name = a.get("channel_name") or None
                if not rt:
                    continue

                # Upsert row
                existing = conn.execute(
                    sa_text("SELECT id FROM channel_config WHERE report_type = :rt"),
                    {"rt": rt},
                ).first()

                if existing:
                    conn.execute(sa_text("""
                        UPDATE channel_config
                        SET channel_id = :ch_id, channel_name = :ch_name,
                            enabled = true, updated_at = :now
                        WHERE report_type = :rt
                    """), {"ch_id": ch_id, "ch_name": ch_name, "now": now, "rt": rt})
                else:
                    conn.execute(sa_text("""
                        INSERT INTO channel_config
                            (report_type, label, channel_id, channel_name, enabled, updated_at)
                        VALUES (:rt, :label, :ch_id, :ch_name, true, :now)
                    """), {
                        "rt": rt,
                        "label": next((r["label"] for r in REPORT_TYPES if r["report_type"] == rt), rt),
                        "ch_id": ch_id, "ch_name": ch_name, "now": now,
                    })

        return jsonify({"success": True, "saved": len(assignments)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# AGENT SPRINT REPORT
# ============================================================================

@app.route('/api/agent/sprint-report')
def get_agent_sprint_report():
    """
    Comprehensive, fully-computed sprint report for AI agents.

    Fetches sprint-pulse and burndown data from Jira, applies all Vue.js
    computed property math server-side, and returns a single agent-ready JSON
    with health score, grade, status distribution, developer velocity
    classification, per-ticket risk projections, action items, and (if a
    next sprint exists) capacity planning summary.

    Query params:
      ?include_burndown=0   Skip changelog replay (faster, ~2s vs ~30s).
                            Burndown fields will be null/zero.
      ?include_planning=0   Skip next-sprint capacity fetch (default: 1).
    """
    try:
        import requests as req
        from src.tools.base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID, JIRA_WEB_URL
        from src.dashboard.sprint_report import build_report
        from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

        project_key = os.getenv('ATLASSIAN_PROJECT_KEY', '').split(',')[0].strip()
        if not project_key:
            return jsonify({"error": "ATLASSIAN_PROJECT_KEY not configured"}), 400

        include_burndown = request.args.get('include_burndown', '1') != '0'
        include_planning = request.args.get('include_planning', '1') != '0'

        jira_base    = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
        headers      = get_jira_auth_headers()
        jira_web_url = JIRA_WEB_URL or os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')

        # ── Fetch pulse + burndown in parallel ────────────────────────────────
        pulse_data    = None
        burndown_data = {}
        fetch_errors  = {}

        def _do_pulse():
            return _fetch_sprint_pulse_data(req, project_key, jira_base, headers, jira_web_url)

        def _do_burndown():
            return _fetch_sprint_burndown_data(req, project_key, jira_base, headers)

        futures = {}
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures['pulse'] = ex.submit(_do_pulse)
            if include_burndown:
                futures['burndown'] = ex.submit(_do_burndown)

            pulse_not_found = False
            for name, fut in futures.items():
                try:
                    result = fut.result(timeout=90)
                    if name == 'pulse':
                        pulse_data = result
                    elif name == 'burndown':
                        burndown_data = result
                except LookupError as exc:
                    fetch_errors[name] = str(exc)
                    if name == 'pulse':
                        pulse_not_found = True
                except Exception as exc:
                    fetch_errors[name] = str(exc)

        if pulse_data is None:
            err = fetch_errors.get('pulse', 'Unknown error fetching sprint data')
            return jsonify({"error": err}), (404 if pulse_not_found else 500)

        # ── Optionally fetch next-sprint planning data ─────────────────────────
        planning_data = None
        if include_planning:
            try:
                # Find first future sprint
                r_future = req.post(
                    f"{jira_base}/rest/api/3/search/jql",
                    headers=headers,
                    json={
                        "jql": f"project = {project_key} AND sprint in futureSprints() ORDER BY created ASC",
                        "fields": ["customfield_10020"],
                        "maxResults": 50,
                    },
                    timeout=20,
                )
                if r_future.ok:
                    seen_ids = set()
                    next_sprint_id = None
                    for issue in r_future.json().get('issues', []):
                        cf = (issue.get('fields') or {}).get('customfield_10020') or []
                        for s in cf:
                            if isinstance(s, dict) and s.get('state') == 'future':
                                sid = s.get('id')
                                if sid and sid not in seen_ids:
                                    seen_ids.add(sid)
                                    if next_sprint_id is None:
                                        next_sprint_id = sid
                    if next_sprint_id:
                        from flask import url_for
                        # Re-use existing get_sprint_planning logic by calling the helper directly
                        # Build a minimal request context substitute
                        class _FakeRequest:
                            args = {'sprint_id': str(next_sprint_id), 'rollover': '1'}
                        # Monkey-patch request.args temporarily isn't safe; call internals directly
                        # Instead, re-invoke via internal function call with the sprint ID
                        team_rows = db.get_team_members(active_only=True)
                        PLANNING_ROLES = {'dev', 'wa', 'tech_lead'}
                        team_by_jira_id = {}
                        for m in team_rows:
                            jid = m.get('jira_account_id')
                            role = (m.get('role') or '').lower()
                            if jid and role in PLANNING_ROLES:
                                team_by_jira_id[jid] = {
                                    'id': m['id'],
                                    'display_name': m['display_name'],
                                    'role': role,
                                    'weekly_capacity_hours': float(m.get('weekly_capacity_hours') or 40.0),
                                    'jira_account_id': jid,
                                }

                        from datetime import timedelta as _td
                        sprint_id_str = str(next_sprint_id)
                        req_fields_p = ["summary", "status", "assignee",
                                        "timeoriginalestimate", "duedate", "customfield_10020"]
                        plan_issues, next_tok = [], None
                        sprint_info_p = None
                        while True:
                            payload_p = {
                                "jql": f"project = {project_key} AND sprint = {sprint_id_str} ORDER BY created ASC",
                                "fields": req_fields_p, "maxResults": 100,
                            }
                            if next_tok:
                                payload_p["nextPageToken"] = next_tok
                            rp = req.post(f"{jira_base}/rest/api/3/search/jql",
                                          headers=headers, json=payload_p, timeout=30)
                            if not rp.ok:
                                break
                            dp = rp.json()
                            plan_issues.extend(dp.get('issues', []))
                            next_tok = dp.get('nextPageToken')
                            if not next_tok or not dp.get('issues'):
                                break

                        for issue in plan_issues:
                            cf = (issue.get('fields') or {}).get('customfield_10020') or []
                            for s in cf:
                                if isinstance(s, dict) and str(s.get('id', '')) == sprint_id_str:
                                    sprint_info_p = s
                                    break
                            if sprint_info_p:
                                break

                        sprint_info_p = sprint_info_p or {}
                        start_p = (sprint_info_p.get('startDate') or '')[:10]
                        end_p   = (sprint_info_p.get('endDate') or '')[:10]

                        sprint_weeks_p = 2.0
                        if start_p and end_p:
                            try:
                                from datetime import datetime as _dt
                                sd_p = _dt.strptime(start_p, '%Y-%m-%d').date()
                                ed_p = _dt.strptime(end_p,   '%Y-%m-%d').date()
                                sprint_weeks_p = max(1.0, round((ed_p - sd_p).days / 7, 1))
                            except Exception:
                                pass

                        def _est_h(issue):
                            sec = (issue.get('fields') or {}).get('timeoriginalestimate') or 0
                            return round(sec / 3600, 1)

                        plan_devs: dict = {}
                        unassigned_tickets_p = []
                        for issue in plan_issues:
                            f = issue.get('fields') or {}
                            assignee = f.get('assignee') or {}
                            acct_id = assignee.get('accountId')
                            status_obj = f.get('status') or {}
                            ticket_p = {
                                'key':            issue.get('key', ''),
                                'summary':        f.get('summary', ''),
                                'status':         status_obj.get('name', 'Unknown'),
                                'status_cat':     (status_obj.get('statusCategory') or {}).get('key', 'new'),
                                'estimate_hours': _est_h(issue),
                                'due_date':       f.get('duedate'),
                            }
                            if acct_id and acct_id in team_by_jira_id:
                                if acct_id not in plan_devs:
                                    plan_devs[acct_id] = {**team_by_jira_id[acct_id], 'tickets': []}
                                plan_devs[acct_id]['tickets'].append(ticket_p)
                            else:
                                ticket_p['assignee_name'] = assignee.get('displayName', 'Unassigned') if acct_id else 'Unassigned'
                                unassigned_tickets_p.append(ticket_p)

                        dev_list_p = []
                        for acct_id, dev in plan_devs.items():
                            planned_h = sum(t['estimate_hours'] for t in dev['tickets'])
                            cap_h = dev['weekly_capacity_hours'] * sprint_weeks_p
                            dev_list_p.append({
                                'id': dev['id'], 'jira_account_id': acct_id,
                                'display_name': dev['display_name'], 'role': dev['role'],
                                'weekly_capacity_hours': dev['weekly_capacity_hours'],
                                'capacity_hours': round(cap_h, 1),
                                'planned_hours': round(planned_h, 1),
                                'rollover_hours': 0.0,
                                'total_load_hours': round(planned_h, 1),
                                'tickets': dev['tickets'],
                                'rollover_tickets': [],
                            })
                        for jid, m in team_by_jira_id.items():
                            if jid not in plan_devs:
                                cap_h = m['weekly_capacity_hours'] * sprint_weeks_p
                                dev_list_p.append({
                                    'id': m['id'], 'jira_account_id': jid,
                                    'display_name': m['display_name'], 'role': m['role'],
                                    'weekly_capacity_hours': m['weekly_capacity_hours'],
                                    'capacity_hours': round(cap_h, 1),
                                    'planned_hours': 0.0, 'rollover_hours': 0.0,
                                    'total_load_hours': 0.0, 'tickets': [], 'rollover_tickets': [],
                                })
                        dev_list_p.sort(key=lambda d: d['display_name'])

                        planning_data = {
                            'sprint': {
                                'id': sprint_id_str,
                                'name': sprint_info_p.get('name', f'Sprint {sprint_id_str}'),
                                'start_date': start_p or None,
                                'end_date':   end_p or None,
                                'state': 'future',
                                'weeks': sprint_weeks_p,
                            },
                            'developers':         dev_list_p,
                            'unassigned_tickets': unassigned_tickets_p,
                            'rollover_enabled':   False,
                            'rollover_context':   None,
                            'project_key':        project_key,
                        }
            except Exception:
                pass  # planning failure is non-fatal

        # ── Load team members for velocity classification ──────────────────────
        team_members = None
        try:
            team_members = db.get_team_members(active_only=True)
        except Exception:
            pass

        # ── Build and return the computed report ──────────────────────────────
        report = build_report(
            pulse_data=pulse_data,
            burndown_data=burndown_data,
            planning_data=planning_data,
            team_members=team_members,
        )

        # Surface any non-fatal fetch errors so agents know if data is partial
        if fetch_errors:
            report['fetch_warnings'] = fetch_errors

        return jsonify(report)

    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ============================================================================
# PROJECT SETTINGS (system_config table)
# ============================================================================

# Defines all configurable project settings shown in the dashboard UI.
# env_fallback: the ENV var to read if no DB value is set.
PROJECT_SETTINGS = [
    {
        "key": "atlassian_cloud_id",
        "label": "Atlassian Cloud ID",
        "description": "Your Atlassian Cloud UUID. Found in admin.atlassian.com or the URL of your Jira instance.",
        "env_fallback": "ATLASSIAN_CLOUD_ID",
        "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    },
    {
        "key": "jira_url",
        "label": "Jira Instance URL",
        "description": "Base URL of your Jira instance.",
        "env_fallback": "JIRA_INSTANCE_URL",
        "placeholder": "https://your-company.atlassian.net",
    },
    {
        "key": "jira_project_key",
        "label": "Jira Project Key",
        "description": "Primary Jira project key used for JQL queries and sprint monitoring.",
        "env_fallback": "ATLASSIAN_PROJECT_KEY",
        "placeholder": "ECD",
    },
    {
        "key": "bitbucket_workspace",
        "label": "Bitbucket Workspace",
        "description": "Your Bitbucket workspace slug (the part of the URL after bitbucket.org/).",
        "env_fallback": "BITBUCKET_WORKSPACE",
        "placeholder": "my-company",
    },
    {
        "key": "confluence_spaces",
        "label": "Confluence Spaces",
        "description": "Comma-separated Confluence space keys the agent monitors for mentions.",
        "env_fallback": "CONFLUENCE_SPACES",
        "placeholder": "ENG,DOCS",
    },
]


@app.route('/api/settings/system')
def get_system_settings():
    """Return current project settings: DB values + ENV fallback values."""
    try:
        from src.utils.system_config import get_all_settings

        db_values = get_all_settings()
        config = {}
        for s in PROJECT_SETTINGS:
            key = s["key"]
            env_val = os.getenv(s["env_fallback"], "") if s.get("env_fallback") else ""
            config[key] = {
                "db_value": db_values.get(key) or None,
                "env_value": env_val or None,
                "effective_value": db_values.get(key) or env_val or None,
                "env_fallback": s.get("env_fallback"),
            }
        return jsonify({"settings": PROJECT_SETTINGS, "config": config})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/settings/system', methods=['POST'])
def save_system_settings():
    """Save project settings. Body: {values: {key: value}}"""
    try:
        from src.utils.system_config import save_setting

        data = request.json or {}
        values = data.get("values", {})

        for key, value in values.items():
            # Only save known keys
            if any(s["key"] == key for s in PROJECT_SETTINGS):
                save_setting(key, value.strip() if value else None)

        return jsonify({"success": True, "saved": len(values)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SEED DATA (Initialize schedules)
# ============================================================================

def seed_schedules():
    """Initialize default check schedules"""
    db.upsert_schedule(
        'sla-check',
        'hourly (9am-5pm weekdays)',
        'Monitor SLA compliance: QA (24h), Pending Approval (48h), Blocked tickets, Stale PRs'
    )
    db.upsert_schedule(
        'standup',
        'daily at 9am (Mon-Fri)',
        'Daily standup workflow: Code-ticket gaps, productivity audit, timesheet analysis'
    )
    db.upsert_schedule(
        'blocked-analysis',
        'daily at 10am (Mon-Fri)',
        'Blocked ticket PM decision tree: check for missing links, resolved blockers, pending responses'
    )
    db.upsert_schedule(
        'test-quality',
        'on-demand',
        'Test quality validation for QA tickets and PRs (not yet configured)'
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print(" 🤖 PM Agent Dashboard ".center(70))
    print("=" * 70)
    print("\nInitializing dashboard...")

    # Seed schedules
    seed_schedules()
    print("✅ Check schedules initialized")

    # Use PORT (Heroku standard) with DASHBOARD_PORT as local override
    port = int(os.getenv('PORT', os.getenv('DASHBOARD_PORT', 8080)))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"\n🚀 Dashboard running at: http://localhost:{port}")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 70)

    app.run(host='0.0.0.0', port=port, debug=debug)
