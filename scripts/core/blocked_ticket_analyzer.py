#!/usr/bin/env python3
"""
Blocked Ticket Analyzer - PM-logic driven blocked ticket assessment

Decision tree for each Blocked ticket (stops at first actionable finding):
  1. Does it have a proper "is blocked by" link?
     → NO: alert assignee to add a blocking link or remove Blocked status
  2. Is any blocking ticket actually resolved?
     → YES (Done/Closed/Pending Approval/etc.): alert dev to resume
  3. Analyze comment thread via Claude
     → Response needed from a specific person? Alert them.
     → Otherwise: legitimately blocked — skip, include in digest only.

Sends Slack alerts only for ACTIONABLE situations.
Runs on its own schedule (every 2 days for digest report).

Usage:
    python -m scripts.core.blocked_ticket_analyzer            # analyze + save to DB, no Slack
    python -m scripts.core.blocked_ticket_analyzer --report   # also send Slack digest
    python -m scripts.core.blocked_ticket_analyzer --dry-run  # print only, no writes
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.base import get_jira_auth_headers, JIRA_BASE_URL

# ─── Configuration ─────────────────────────────────────────────────────────────

# Statuses that mean the blocking ticket's work is effectively done
BLOCKER_RESOLVED_STATUSES = {
    'Done', 'Closed', 'Complete', 'Cancelled', 'Released',
    'Pending Approval',   # Dev work done, awaiting sign-off
    'Ready For QA',       # Dev work done, in review queue
}

# Statuses where the blocker is still legitimately in-flight
BLOCKER_ACTIVE_STATUSES = {
    'To Do', 'Open', 'In Progress', 'In Development',
    'Ready For Development', 'Blocked',
}

ANALYSIS_CATEGORIES = {
    'no_link':              'No Blocking Link',
    'blocker_resolved':     'Blocker Resolved — Ready to Resume',
    'response_needed':      'Response / Action Needed',
    'cascading_block':      'Cascading Block',
    'legitimately_blocked': 'Legitimately Blocked',
}

JIRA_BASE_URL_WEB = os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')

# PM identity — responsible for Jira hygiene (missing links, mis-categorised tickets)
PM_SLACK_ID = os.getenv('PM_SLACK_ID', '').strip('"\'')
PM_NAME = os.getenv('PM_NAME', 'PM').strip('"\'')


def get_pm_mention() -> str:
    """Return Slack mention for the PM."""
    if PM_SLACK_ID:
        return f'<@{PM_SLACK_ID}>'
    return f'@{PM_NAME}'


def resolve_mention(display_name: Optional[str]) -> str:
    """
    Resolve a person's display name to a Slack mention.
    Falls back to @display_name if not found in roster.
    """
    if not display_name:
        return ''
    try:
        from src.team_roster import get_slack_mention_by_name
        mention = get_slack_mention_by_name(display_name)
        if mention:
            return mention
    except ImportError:
        pass
    # Fallback: use plain @name
    return f'@{display_name}'


# ─── Jira Data Fetching ─────────────────────────────────────────────────────────

def get_blocked_tickets() -> List[Dict]:
    """Fetch all tickets currently in Blocked status."""
    try:
        resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json={
                'jql': f'project IN ({os.getenv("ATLASSIAN_PROJECT_KEY", "")}) AND status = "Blocked" AND resolution is EMPTY ORDER BY updated ASC',
                'fields': ['summary', 'status', 'assignee', 'updated', 'issuelinks'],
                'maxResults': 100,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get('issues', [])
    except Exception as e:
        print(f"❌ Failed to fetch blocked tickets: {e}")
        return []


def get_blocking_ticket_status(key: str) -> Optional[str]:
    """Get the current status of a ticket (used to check blocker status)."""
    try:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{key}",
            headers=get_jira_auth_headers(),
            params={'fields': 'summary,status,assignee'},
            timeout=15,
        )
        if resp.status_code == 200:
            fields = resp.json().get('fields', {})
            return {
                'status': fields.get('status', {}).get('name'),
                'summary': fields.get('summary', ''),
                'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            }
    except Exception:
        pass
    return None


def get_issue_comments(key: str) -> List[Dict]:
    """Fetch comments for a single ticket from the comments endpoint."""
    try:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/comment",
            headers=get_jira_auth_headers(),
            params={'maxResults': 8, 'orderBy': '-created'},
            timeout=15,
        )
        if resp.status_code == 200:
            raw = resp.json().get('comments', [])
            result = []
            for c in raw:
                author = c.get('author', {}).get('displayName', 'Unknown')
                created = c.get('created', '')[:10]
                body = c.get('body', {})
                result.append({'author': author, 'date': created, 'text': _extract_adf_text(body)})
            return result
    except Exception:
        pass
    return []


def extract_comments_text(fields: Dict) -> List[Dict]:
    """Extract comment list from issue fields (fallback for inline comments)."""
    comments = fields.get('comment', {}).get('comments', [])
    result = []
    for c in comments[-8:]:  # last 8 comments for context
        author = c.get('author', {}).get('displayName', 'Unknown')
        created = c.get('created', '')[:10]
        # Extract plain text from ADF body
        body = c.get('body', {})
        text = _extract_adf_text(body)
        result.append({'author': author, 'date': created, 'text': text})
    return result


def _extract_adf_text(adf: Any) -> str:
    """Recursively extract plain text from Atlassian Document Format."""
    if not adf:
        return ''
    if isinstance(adf, str):
        return adf
    if isinstance(adf, dict):
        if adf.get('type') == 'text':
            return adf.get('text', '')
        parts = []
        for item in adf.get('content', []):
            parts.append(_extract_adf_text(item))
        return ' '.join(p for p in parts if p).strip()
    return ''


# ─── Comment Analysis via Claude ────────────────────────────────────────────────

def analyze_comments_with_claude(
    ticket_key: str, summary: str, assignee: str, comments: List[Dict]
) -> Dict:
    """
    Use Claude to analyze the comment thread and determine if action is needed.
    Returns: {needs_action, who_to_tag, action_description, reason}

    who_to_tag will be an exact display name from the comment thread so it can
    be resolved to a Slack mention via the team roster.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or not comments:
        return {'needs_action': False, 'who_to_tag': None, 'action_description': None}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        comments_text = '\n'.join(
            f"[{c['date']}] {c['author']}: {c['text'][:400]}"
            for c in comments
        )

        prompt = f"""You are a PM triaging a blocked Jira ticket. The ticket has a legitimate \
in-progress blocker dependency, but you need to check whether there is also a \
PENDING RESPONSE or ACTION needed in the comment thread itself.

Ticket: {ticket_key}
Summary: {summary}
Assignee: {assignee}

Comment thread (oldest → newest):
{comments_text}

Your job: look only at the comments. Determine:
1. Is there an unanswered question, a request for input, or something someone \
was asked to provide that has not happened yet?
2. If YES — who specifically needs to act? Use their EXACT name as it appears in \
the comments (or the assignee name if they need to act). What do they need to do?
3. If NO — the ticket is simply documenting a wait; no action is needed from the thread.

Rules:
- Only flag "needs_action: true" if there is a CLEAR, SPECIFIC pending ask.
- Do not flag tickets where everyone is just waiting on the dependency.
- "who_to_tag" MUST be an exact name from the comment authors or the assignee name. \
Never invent a name.

Respond with ONLY valid JSON:
{{
  "needs_action": true,
  "who_to_tag": "Exact Person Name",
  "action_description": "1-2 sentence description of what they need to do",
  "reason": "One sentence explaining why this is actionable"
}}
or:
{{
  "needs_action": false,
  "who_to_tag": null,
  "action_description": null,
  "reason": "One sentence explaining why no action is needed"
}}"""

        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            messages=[{'role': 'user', 'content': prompt}]
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        return json.loads(response_text)

    except Exception as e:
        print(f"   ⚠️  Claude analysis failed for {ticket_key}: {e}")
        return {'needs_action': False, 'who_to_tag': None, 'action_description': None}


# ─── Core Analysis Logic ────────────────────────────────────────────────────────

def analyze_ticket(issue: Dict) -> Dict:
    """
    Run the full PM decision tree for a single blocked ticket.
    Returns an analysis dict describing the category and recommended action.
    """
    key = issue['key']
    fields = issue['fields']
    summary = fields.get('summary', '')
    assignee_data = fields.get('assignee') or {}
    assignee = assignee_data.get('displayName', 'Unassigned')
    assignee_account_id = assignee_data.get('accountId')
    link = f"{JIRA_BASE_URL_WEB}/browse/{key}"
    issue_links = fields.get('issuelinks', [])
    comments = get_issue_comments(key)

    base = {
        'key': key,
        'summary': summary,
        'assignee': assignee,
        'assignee_account_id': assignee_account_id,
        'link': link,
        'analyzed_at': datetime.now().isoformat(),
        'needs_alert': False,
        'blocking_tickets': [],
    }

    # ── STEP 1: Check for "is blocked by" links ─────────────────────────────
    blocking_links = [l for l in issue_links if l.get('inwardIssue')]

    if not blocking_links:
        # PM responsibility — Jira hygiene is on the PM, not the dev
        pm_mention = get_pm_mention()
        assignee_mention = resolve_mention(assignee) if assignee != 'Unassigned' else 'unassigned'
        return {
            **base,
            'category': 'no_link',
            'needs_alert': True,
            'alert_message': (
                f"{pm_mention} — <{link}|{key}> is marked *Blocked* but has no "
                f"\"is blocked by\" link.\n"
                f"Assignee: {assignee_mention}. "
                f"Please follow up to get a blocking link added, or update the status if this is no longer blocked."
            ),
            'alert_target': 'pm',
            'alert_target_name': PM_NAME,
            'action': f'PM to follow up with {assignee}: add blocking link or update status',
        }

    # ── STEP 2: Check status of each blocking ticket ────────────────────────
    blocking_info = []
    resolved_blockers = []
    cascading_blockers = []  # blocking ticket is itself Blocked

    for link_obj in blocking_links:
        blocker_key = link_obj['inwardIssue']['key']
        blocker_status_from_link = link_obj['inwardIssue']['fields']['status']['name']

        # Fetch full details for richer status
        blocker_detail = get_blocking_ticket_status(blocker_key)
        blocker_status = blocker_detail['status'] if blocker_detail else blocker_status_from_link
        blocker_summary = blocker_detail['summary'][:60] if blocker_detail else ''
        blocker_assignee = blocker_detail['assignee'] if blocker_detail else 'Unknown'

        info = {
            'key': blocker_key,
            'status': blocker_status,
            'summary': blocker_summary,
            'assignee': blocker_assignee,
            'link': f"{JIRA_BASE_URL_WEB}/browse/{blocker_key}",
        }
        blocking_info.append(info)

        if blocker_status in BLOCKER_RESOLVED_STATUSES:
            resolved_blockers.append(info)
        elif blocker_status == 'Blocked':
            cascading_blockers.append(info)

    if resolved_blockers:
        # Blocker is done — dev should resume
        assignee_mention = resolve_mention(assignee)
        blocker_lines = '\n'.join(
            f"  • <{b['link']}|{b['key']}> is now *{b['status']}*"
            for b in resolved_blockers
        )
        blocker_list = ', '.join(f"{b['key']} ({b['status']})" for b in resolved_blockers)
        return {
            **base,
            'category': 'blocker_resolved',
            'needs_alert': True,
            'blocking_tickets': blocking_info,
            'alert_message': (
                f"{assignee_mention} — your blocker on <{link}|{key}> may be cleared:\n"
                f"{blocker_lines}\n"
                f"Please verify and update the ticket status to resume development."
            ),
            'alert_target': assignee,
            'alert_target_name': assignee,
            'action': f"Blocking ticket {blocker_list} may be resolved — verify and resume development",
        }

    if cascading_blockers and not [b for b in blocking_info if b not in cascading_blockers]:
        # All blockers are themselves Blocked — cascading block
        blocker_list = ', '.join(f"{b['key']}" for b in cascading_blockers)
        return {
            **base,
            'category': 'cascading_block',
            'needs_alert': False,  # Informational only — appears in digest
            'blocking_tickets': blocking_info,
            'alert_message': (
                f"*{key}* is caught in a cascading block chain: "
                f"blocked by {blocker_list}, which {'is' if len(cascading_blockers) == 1 else 'are'} also Blocked."
            ),
            'action': f"Cascading block via {blocker_list} — investigate root blocker",
        }

    # ── STEP 3: All blockers are legitimately active — analyze comments ──────
    if comments:
        claude_result = analyze_comments_with_claude(key, summary, assignee, comments)
        if claude_result.get('needs_action'):
            who = claude_result.get('who_to_tag') or assignee
            who_mention = resolve_mention(who)
            action_desc = claude_result.get('action_description', 'Please review the comment thread and respond.')
            return {
                **base,
                'category': 'response_needed',
                'needs_alert': True,
                'blocking_tickets': blocking_info,
                'alert_message': (
                    f"{who_mention} — <{link}|{key}> needs your input to move forward.\n"
                    f"{action_desc}"
                ),
                'alert_target': who,
                'alert_target_name': who,
                'claude_reason': claude_result.get('reason'),
                'action': action_desc,
            }

    # Ticket is legitimately blocked with active blockers and no pending responses
    blocker_desc = ', '.join(f"{b['key']} ({b['status']})" for b in blocking_info)
    return {
        **base,
        'category': 'legitimately_blocked',
        'needs_alert': False,
        'blocking_tickets': blocking_info,
        'action': f"Waiting on {blocker_desc}",
    }


# ─── Slack Posting ──────────────────────────────────────────────────────────────

def post_to_slack(channel: str, text: str) -> bool:
    """Post a message to a Slack channel."""
    token = os.getenv('SLACK_BOT_TOKEN', '').strip('"\'')
    if not token or not channel:
        print(f"   ⚠️  Slack not configured, skipping post")
        return False
    try:
        resp = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {token}'},
            json={'channel': channel, 'text': text, 'mrkdwn': True},
            timeout=10,
        )
        ok = resp.json().get('ok', False)
        if not ok:
            print(f"   ❌ Slack error: {resp.json().get('error')}")
        return ok
    except Exception as e:
        print(f"   ❌ Slack post failed: {e}")
        return False


def generate_digest(results: List[Dict]) -> str:
    """Format a Slack digest report of all blocked ticket analyses."""
    today = datetime.now().strftime('%b %d, %Y')
    total = len(results)

    by_category = {}
    for r in results:
        cat = r['category']
        by_category.setdefault(cat, []).append(r)

    actionable = [r for r in results if r['needs_alert']]
    clean = [r for r in results if not r['needs_alert']]

    lines = [
        f"🔍 *Blocked Ticket Report* | {today}",
        f"*{total} blocked tickets* — {len(actionable)} need action, {len(clean)} legitimately blocked\n",
    ]

    if by_category.get('no_link'):
        lines.append(f"*🚫 Missing Blocking Link* — {get_pm_mention()} to follow up:")
        for r in by_category['no_link']:
            assignee_mention = resolve_mention(r['assignee']) if r['assignee'] != 'Unassigned' else 'unassigned'
            lines.append(f"  • <{r['link']}|{r['key']}>: {r['summary'][:60]}")
            lines.append(f"    Assignee: {assignee_mention} — needs a blocking link or status update")
        lines.append('')

    if by_category.get('blocker_resolved'):
        lines.append("*✅ Blocker Resolved — Ready to Resume:*")
        for r in by_category['blocker_resolved']:
            assignee_mention = resolve_mention(r['assignee'])
            for b in r['blocking_tickets']:
                if b['status'] in BLOCKER_RESOLVED_STATUSES:
                    lines.append(f"  • <{r['link']}|{r['key']}>: {r['summary'][:55]}")
                    lines.append(
                        f"    → Blocked by <{b['link']}|{b['key']}> which is now *{b['status']}*"
                    )
                    lines.append(f"    → {assignee_mention}: please verify and resume")
        lines.append('')

    if by_category.get('response_needed'):
        lines.append("*💬 Waiting on Response / Action:*")
        for r in by_category['response_needed']:
            who_mention = resolve_mention(r.get('alert_target_name') or r['assignee'])
            lines.append(f"  • <{r['link']}|{r['key']}>: {r['summary'][:55]}")
            lines.append(f"    → {who_mention}: {r.get('action', 'Review comment thread and respond')}")
            if r.get('claude_reason'):
                lines.append(f"    _{r['claude_reason']}_")
        lines.append('')

    if by_category.get('cascading_block'):
        lines.append("*🔗 Cascading Blocks (FYI):*")
        for r in by_category['cascading_block']:
            blocker_keys = ', '.join(b['key'] for b in r['blocking_tickets'])
            lines.append(f"  • <{r['link']}|{r['key']}> ← blocked by {blocker_keys} (also Blocked)")
        lines.append('')

    if by_category.get('legitimately_blocked'):
        lines.append("*⏳ Legitimately Blocked (no action needed):*")
        for r in by_category['legitimately_blocked']:
            blocker_desc = ', '.join(
                f"{b['key']} ({b['status']})" for b in r['blocking_tickets']
            )
            lines.append(f"  • <{r['link']}|{r['key']}>: {r['summary'][:50]} — waiting on {blocker_desc}")

    return '\n'.join(lines)


# ─── Database Logging ───────────────────────────────────────────────────────────

def save_to_active_violations(results: List[Dict]):
    """
    Write actionable blocked ticket results into active_violations so they
    appear in the unified Alerts view alongside SLA violations.
    Only needs_alert=True tickets become violations; legitimately_blocked are skipped.
    """
    CATEGORY_SEVERITY = {
        'no_link':          'critical',
        'blocker_resolved': 'critical',
        'response_needed':  'critical',
        'cascading_block':  'warning',
    }
    try:
        from src.database.dashboard_db import get_dashboard_db
        from sqlalchemy import text as sa_text
        _db = get_dashboard_db()
        now = datetime.now()

        with _db.engine.begin() as conn:
            # Clear old blocked_ticket violations (will re-insert fresh)
            conn.execute(sa_text(
                "DELETE FROM active_violations WHERE violation_type = 'blocked_ticket'"
            ))

            for r in results:
                if not r.get('needs_alert'):
                    continue
                severity = CATEGORY_SEVERITY.get(r['category'], 'warning')
                meta = json.dumps({
                    'category':         r['category'],
                    'action':           r.get('action', ''),
                    'blocking_tickets': r.get('blocking_tickets', []),
                })
                conn.execute(sa_text("""
                    INSERT INTO active_violations
                        (item_id, violation_type, severity, detected_at, hours_overdue,
                         owner, title, link, last_updated, metadata)
                    VALUES
                        (:item_id, 'blocked_ticket', :severity, :detected_at, 0,
                         :owner, :title, :link, :last_updated, :metadata)
                    ON CONFLICT (item_id) DO UPDATE SET
                        severity     = excluded.severity,
                        owner        = excluded.owner,
                        title        = excluded.title,
                        link         = excluded.link,
                        last_updated = excluded.last_updated,
                        metadata     = excluded.metadata,
                        resolved_at  = NULL
                """), {
                    'item_id':     r['key'],
                    'severity':    severity,
                    'detected_at': now.isoformat(),
                    'owner':       r.get('assignee', ''),
                    'title':       r.get('summary', ''),
                    'link':        r.get('link', ''),
                    'last_updated': now.isoformat(),
                    'metadata':    meta,
                })

        actionable = [r for r in results if r.get('needs_alert')]
        print(f"💾 Wrote {len(actionable)} blocked violations to active_violations")
    except Exception as e:
        print(f"⚠️  Could not write to active_violations: {e}")


def save_analyses_to_db(results: List[Dict]):
    """Save analysis results to dashboard database via SQLAlchemy (works on SQLite + PostgreSQL)."""
    try:
        from src.database.dashboard_db import get_dashboard_db
        from sqlalchemy import text as sa_text
        _db = get_dashboard_db()
        with _db.engine.begin() as conn:
            for r in results:
                conn.execute(sa_text("""
                    INSERT INTO blocked_ticket_analyses
                        (key, summary, assignee, link, category, needs_alert,
                         action, alert_message, blocking_tickets, analyzed_at)
                    VALUES
                        (:key, :summary, :assignee, :link, :category, :needs_alert,
                         :action, :alert_message, :blocking_tickets, :analyzed_at)
                    ON CONFLICT (key) DO UPDATE SET
                        category         = excluded.category,
                        needs_alert      = excluded.needs_alert,
                        action           = excluded.action,
                        alert_message    = excluded.alert_message,
                        blocking_tickets = excluded.blocking_tickets,
                        analyzed_at      = excluded.analyzed_at
                """), {
                    'key': r['key'],
                    'summary': r['summary'],
                    'assignee': r['assignee'],
                    'link': r['link'],
                    'category': r['category'],
                    'needs_alert': r['needs_alert'],
                    'action': r.get('action'),
                    'alert_message': r.get('alert_message'),
                    'blocking_tickets': json.dumps(r.get('blocking_tickets', [])),
                    'analyzed_at': r['analyzed_at'],
                })
        print(f"💾 Saved {len(results)} analyses to dashboard database")
    except Exception as e:
        print(f"⚠️  Could not save to dashboard database: {e}")


def should_send_alert(key: str, category: str) -> bool:
    """Check dedup table — don't re-alert within 48 hours for same ticket+category."""
    try:
        from src.database.dashboard_db import get_dashboard_db
        from sqlalchemy import text as sa_text
        _db = get_dashboard_db()
        now = datetime.now()
        with _db.engine.begin() as conn:
            row = conn.execute(sa_text(
                "SELECT sent_at FROM blocked_sent_alerts WHERE key = :key AND category = :category"
            ), {'key': key, 'category': category}).fetchone()

            if row:
                raw = row[0]
                last_sent = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))
                if now - last_sent < timedelta(hours=48):
                    return False  # Already alerted within 48h

            # Upsert the current alert timestamp
            conn.execute(sa_text("""
                INSERT INTO blocked_sent_alerts (key, category, sent_at)
                VALUES (:key, :category, :now)
                ON CONFLICT (key, category) DO UPDATE SET sent_at = excluded.sent_at
            """), {'key': key, 'category': category, 'now': now.isoformat()})

        return True
    except Exception as e:
        print(f"⚠️  Alert dedup check failed: {e}")
        return True  # Default to sending if DB check fails


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Blocked Ticket Analyzer — PM decision-logic analysis')
    parser.add_argument('--report', action='store_true', help='Send full digest to Slack')
    parser.add_argument('--dry-run', action='store_true', help='Print output only, no Slack or DB writes')
    args = parser.parse_args()

    print('\n' + '=' * 65)
    print(' 🔍 BLOCKED TICKET ANALYSIS '.center(65))
    print('=' * 65)

    # Fetch all blocked tickets
    issues = get_blocked_tickets()
    print(f'\n📋 Found {len(issues)} blocked tickets in open sprints\n')

    if not issues:
        print('✅ No blocked tickets — nothing to analyze.')
        return

    # Analyze each ticket
    results = []
    for issue in issues:
        key = issue['key']
        summary = issue['fields'].get('summary', '')[:60]
        print(f'  Analyzing {key}: {summary}...')
        result = analyze_ticket(issue)
        results.append(result)

        category_label = ANALYSIS_CATEGORIES.get(result['category'], result['category'])
        alert_flag = ' ⚠️ ' if result['needs_alert'] else ' ✅'
        print(f'    {alert_flag} {category_label}')
        if result.get('action'):
            print(f'       → {result["action"]}')

    # Summary
    actionable = [r for r in results if r['needs_alert']]
    print(f'\n📊 Summary: {len(actionable)}/{len(results)} tickets need action')

    # Save to database
    if not args.dry_run:
        save_analyses_to_db(results)
        save_to_active_violations(results)

    # Send individual Slack alerts (deduped)
    from src.utils.channel_config import get_channel
    standup_channel = get_channel("blocked_tickets") or ''
    alerts_sent = 0

    if not args.dry_run:
        for r in actionable:
            if should_send_alert(r['key'], r['category']):
                if post_to_slack(standup_channel, r['alert_message']):
                    alerts_sent += 1
                    print(f"  📤 Alerted on {r['key']} ({r['category']})")
            else:
                print(f"  ⏭️  Skipping {r['key']} — alerted within last 48h")

    # Send full digest report if requested
    if args.report or args.dry_run:
        digest = generate_digest(results)
        print('\n' + '─' * 65)
        print('DIGEST REPORT:')
        print('─' * 65)
        print(digest)
        print('─' * 65)

        if args.report and not args.dry_run:
            if post_to_slack(standup_channel, digest):
                print('📤 Digest posted to Slack')

    print(f'\n✅ Analysis complete — {alerts_sent} alerts sent')


if __name__ == '__main__':
    main()
