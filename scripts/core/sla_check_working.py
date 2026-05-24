#!/usr/bin/env python3
"""
Working SLA Monitor - Simplified version that actually works
Checks Jira and Bitbucket for SLA violations and posts to Slack with links
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from trinity.jira import search_jira, get_status_history


def _time_in_current_status(key: str, fallback_hours: float) -> float:
    """Return time-in-current-status hours from trinity, or fallback on any error."""
    try:
        history = get_status_history(key)
        if history.get("error"):
            return fallback_hours
        return history.get("time_in_current_status_hours", fallback_hours)
    except Exception:
        return fallback_hours

# Add parent to path for bitbucket-cli import
sys.path.append(str(Path(__file__).parent.parent))

try:
    from bitbucket_cli.api import BitbucketAPI
    from bitbucket_cli.auth import load_config as load_bb_config
    HAS_BB_CLI = True
except ImportError:
    HAS_BB_CLI = False
    print("⚠️  bitbucket-cli not available, PR checks will be skipped")

import requests

# Import team roster for Slack mentions
try:
    from src.team_roster import get_slack_mention_by_name
    HAS_TEAM_ROSTER = True
except ImportError:
    HAS_TEAM_ROSTER = False
    print("⚠️  team_roster module not available, Slack mentions will be skipped")

# Import escalation module
try:
    from sla_escalation import process_violations, generate_escalation_summary
    HAS_ESCALATION = True
except ImportError:
    HAS_ESCALATION = False
    print("⚠️  sla_escalation module not available, escalations will be skipped")

# Import dashboard database for check execution tracking
try:
    # Add project root to path for dashboard_db import
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.database.dashboard_db import get_dashboard_db
    HAS_DASHBOARD_DB = True
except ImportError:
    HAS_DASHBOARD_DB = False
    print("⚠️  dashboard_db module not available, dashboard tracking will be skipped")


def calculate_business_hours_simple(start_time: datetime) -> float:
    """
    Simple business hours calculation
    Rough approximation: 40 business hours per week / 168 total hours
    """
    now = datetime.now()
    delta = now - start_time
    total_hours = delta.total_seconds() / 3600

    # Business hours ≈ total_hours * 0.238 (40/168)
    business_hours = total_hours * 0.238
    return business_hours


def check_pr_slas() -> List[Dict[str, Any]]:
    """Check PR review and staleness SLAs"""
    print("\n🔀 Checking PR SLAs (Bitbucket)...")

    violations = []

    if not HAS_BB_CLI:
        print("   ⏭️  Skipping PR checks (bitbucket-cli not available)")
        return violations

    try:
        bb_config = load_bb_config()
        bb_api = BitbucketAPI(bb_config)
        workspace = os.getenv("BITBUCKET_WORKSPACE") or bb_config.get("workspace", "")
        repos_str = os.getenv("BITBUCKET_REPOS", "")
        repos = [r.strip() for r in repos_str.split(",") if r.strip()] if repos_str else []

        for repo in repos:
            try:
                prs = bb_api.list_pull_requests(workspace, repo, state="OPEN")
                print(f"   Found {len(prs)} open PRs in {repo}")

                for pr in prs:
                    pr_id = pr["id"]
                    title = pr["title"]
                    author = pr["author"]["display_name"]
                    created_at = datetime.fromisoformat(pr["created_on"].replace("Z", "+00:00")).replace(tzinfo=None)
                    updated_at = datetime.fromisoformat(pr["updated_on"].replace("Z", "+00:00")).replace(tzinfo=None)

                    # Check staleness (no updates in 2+ business days)
                    hours_since_update = calculate_business_hours_simple(updated_at)

                    if hours_since_update > 16:  # 2 business days = 16 hours
                        violations.append({
                            "type": "pr_stale",
                            "severity": "warning" if hours_since_update < 32 else "critical",
                            "item_id": f"PR-{pr_id}",
                            "repo": repo,
                            "title": title,
                            "owner": author,
                            "hours_overdue": hours_since_update - 16,
                            "link": f"https://bitbucket.org/{workspace}/{repo}/pull-requests/{pr_id}",
                            "message": f"No updates for {hours_since_update:.0f}h (SLA: 16h / 2 business days)"
                        })

            except Exception as e:
                if "not found" in str(e).lower():
                    print(f"   ⏭️  Skipping {repo} (not accessible)")
                else:
                    print(f"   ❌ Error checking {repo}: {e}")

    except Exception as e:
        print(f"   ❌ Error checking PRs: {e}")

    print(f"   Found {len(violations)} PR violations")
    return violations


def check_jira_slas_direct() -> List[Dict[str, Any]]:
    """Check Jira SLAs using direct Python CLI tools (NOT Claude MCP)"""
    print("\n📋 Checking Jira SLAs (via Python CLI tools)...")

    violations = []

    try:
        # Query open tickets using our Python CLI tool
        project_keys = [k.strip() for k in os.getenv("ATLASSIAN_PROJECT_KEY", "").split(",") if k.strip()]
        project_clause = f'project IN ({", ".join(project_keys)})' if len(project_keys) > 1 else f'project = {project_keys[0]}'
        jql = f'{project_clause} AND sprint in openSprints() AND status NOT IN (Done, Closed, Cancelled)'

        data = search_jira(jql, max_results=100)
        if data.get("error"):
            print(f"   ❌ Jira search failed: {data.get('message') or data}")
            raise RuntimeError(f"Jira search failed: {data}")
        tickets = data.get('issues', [])
        print(f"   Found {len(tickets)} open tickets")

        # Check each ticket for SLA violations
        for ticket in tickets:
            key = ticket['key']
            status = ticket['status']
            assignee = ticket.get('assignee', 'Unassigned')
            title = ticket['summary']
            link = f"{os.getenv('JIRA_INSTANCE_URL', '').rstrip('/')}/browse/{key}"
            # Parse updated timestamp (handle both Z and timezone offsets)
            updated_str = ticket['updated']
            if 'Z' in updated_str:
                updated_str = updated_str.replace('Z', '+00:00')

            try:
                from dateutil import parser
                updated = parser.parse(updated_str)
            except:
                # Fallback: strip timezone and use naive datetime
                updated = datetime.fromisoformat(updated_str.split('+')[0].split('-')[0])
                updated = updated.replace(tzinfo=None)

            # Calculate hours since last update
            now = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
            time_since_update = (now - updated).total_seconds() / 3600

            # 1. Check QA SLAs (24 hour threshold - strict!)
            if status in ['In QA', 'QA', 'Ready for QA']:
                time_in_qa = _time_in_current_status(key, time_since_update)
                if time_in_qa > 24:
                    violations.append({
                        'type': 'qa_stale',
                        'severity': 'critical' if time_in_qa > 48 else 'warning',
                        'item_id': key,
                        'title': title,
                        'owner': assignee,
                        'hours_overdue': time_in_qa - 24,
                        'link': link,
                        'message': f'In QA for {time_in_qa:.1f}h (SLA: 24h)'
                    })

            # 2. Check Pending Approval (48 hour threshold)
            elif status == 'Pending Approval':
                time_in_pending = _time_in_current_status(key, time_since_update)
                if time_in_pending > 48:
                    violations.append({
                        'type': 'pending_approval',
                        'severity': 'critical' if time_in_pending > 72 else 'warning',
                        'item_id': key,
                        'title': title,
                        'owner': assignee,
                        'hours_overdue': time_in_pending - 48,
                        'link': link,
                        'message': f'Pending approval for {time_in_pending:.1f}h (SLA: 48h)'
                    })

            # 3. Check Blocked status (24h threshold — uses status history, not comment time)
            elif 'Blocked' in status or 'blocked' in ticket.get('labels', []):
                time_in_blocked = _time_in_current_status(key, time_since_update)
                if time_in_blocked > 24:
                    violations.append({
                        'type': 'blocked_ticket',
                        'severity': 'critical' if time_in_blocked > 48 else 'warning',
                        'item_id': key,
                        'title': title,
                        'owner': assignee,
                        'hours_overdue': time_in_blocked - 24,
                        'link': link,
                        'message': f'Blocked for {time_in_blocked:.1f}h (SLA: 24h — daily update required)'
                    })

            # 4. Check Changes Requested (48h for dev to address QA feedback and push back)
            elif status == 'Changes Requested':
                time_in_changes = _time_in_current_status(key, time_since_update)
                if time_in_changes > 48:
                    violations.append({
                        'type': 'changes_requested',
                        'severity': 'critical' if time_in_changes > 72 else 'warning',
                        'item_id': key,
                        'title': title,
                        'owner': assignee,
                        'hours_overdue': time_in_changes - 48,
                        'link': link,
                        'message': f'Changes Requested for {time_in_changes:.1f}h (SLA: 48h — address QA feedback and push back to QA)'
                    })

        print(f"   Found {len(violations)} Jira violations")

    except subprocess.TimeoutExpired:
        print("   ⏱️  Jira search timed out")
    except Exception as e:
        print(f"   ❌ Error checking Jira: {e}")
        import traceback
        traceback.print_exc()

    return violations


def get_owner_mention(owner_name: str) -> str:
    """Get Slack mention for owner or fallback to plain text"""
    if HAS_TEAM_ROSTER and owner_name:
        slack_mention = get_slack_mention_by_name(owner_name)
        if slack_mention:
            return slack_mention
    return owner_name


def format_violation_message(violation: Dict[str, Any]) -> str:
    """Format a single violation as a Slack message with owner mention"""
    severity_emoji = "⚠️" if violation.get("severity") == "critical" else "⏰"
    severity_text = "CRITICAL" if violation.get("severity") == "critical" else "WARNING"

    owner_display = get_owner_mention(violation.get('owner', 'unknown'))

    message = f"""{severity_emoji} *SLA {severity_text}*

📋 *{violation['item_id']}*: {violation.get('title', 'No title')[:80]}

👤 *Owner*: {owner_display}
⏱️  *Overdue*: {violation['hours_overdue']:.0f} hours
💬 *Issue*: {violation['message']}

🔗 <{violation['link']}|View {violation['item_id']}>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_Reply to this thread if you have updates or questions_
"""
    return message


def log_to_pm_channel(message: str) -> bool:
    """Log activity to PM agent logs channel"""
    from src.utils.channel_config import get_channel
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    log_channel = get_channel("pm_logs")

    if not slack_token or not log_channel:
        return False

    try:
        # Strip quotes from token
        clean_token = slack_token.strip('"\'')
        clean_channel = log_channel.strip('"\'')

        headers = {"Authorization": f"Bearer {clean_token}"}
        payload = {
            "channel": clean_channel,
            "text": message,
            "mrkdwn": True
        }

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=10
        )

        return response.json().get("ok", False)
    except Exception:
        return False


def post_violations_to_slack(violations: List[Dict[str, Any]]) -> int:
    """Post each violation as a separate Slack message. Returns count of successfully posted messages."""
    print("\n📤 Posting violations to Slack (individual messages)...")

    from src.utils.channel_config import get_channel
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel_standup = get_channel("sla_violations")
    slack_channel_qa = get_channel("sla_qa_alerts")

    if not slack_token:
        print("   ❌ Missing SLACK_BOT_TOKEN in .env")
        return 0

    if not slack_channel_standup:
        print("   ❌ No SLA violations channel configured (set SLACK_CHANNEL_STANDUP or use Settings)")
        return 0

    # Clean tokens
    clean_token = slack_token.strip('"\'')
    clean_channel_standup = slack_channel_standup.strip('"\'')
    clean_channel_qa = slack_channel_qa.strip('"\'') if slack_channel_qa else None

    posted_count = 0
    skipped_count = 0

    try:
        # Import deduplication helpers
        from sla_alert_tracker import should_alert_violation, record_alert

        headers = {"Authorization": f"Bearer {clean_token}"}

        # Sort violations: critical first, then warnings
        sorted_violations = sorted(
            violations,
            key=lambda v: (0 if v.get("severity") == "critical" else 1, v.get("item_id", ""))
        )

        print(f"\n🔍 Checking {len(sorted_violations)} violations for deduplication...")

        for violation in sorted_violations:
            # Check if we should alert (24-hour cooldown + escalation check)
            if not should_alert_violation(violation):
                skipped_count += 1
                continue

            message = format_violation_message(violation)

            # Route QA violations to dedicated QA channel (if configured)
            # Otherwise, use general standup channel
            violation_type = violation.get('type')
            if violation_type == 'qa_stale' and clean_channel_qa:
                target_channel = clean_channel_qa
                channel_name = "QA alerts"
            else:
                target_channel = clean_channel_standup
                channel_name = "standup"

            payload = {
                "channel": target_channel,
                "text": message,
                "mrkdwn": True
            }

            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json=payload,
                timeout=10
            )

            result = response.json()
            if result.get("ok"):
                posted_count += 1
                thread_ts = result.get("ts")
                print(f"   ✅ Posted {violation['item_id']} to #{channel_name} (thread_ts: {thread_ts})")

                # Store thread_ts in violation for future tracking
                violation["slack_thread_ts"] = thread_ts

                # Record this alert in the deduplication database
                try:
                    record_alert(violation, slack_thread_ts=thread_ts)
                except Exception as record_error:
                    print(f"   ⚠️  Could not record alert: {record_error}")

                # Register thread for monitoring (so we can detect replies)
                try:
                    from src.database.connection import get_engine
                    from sqlalchemy import text as sa_text
                    from datetime import datetime as _dt
                    _engine = get_engine(default_path=".claude/data/bot-state/slack_state.db")
                    with _engine.begin() as _conn:
                        _conn.execute(sa_text("""
                            INSERT INTO slack_tracked_threads
                                (thread_ts, channel, context, last_checked_ts, created_at)
                            VALUES (:ts, :channel, :context, :last_ts, :now)
                            ON CONFLICT (thread_ts) DO UPDATE SET
                                context         = excluded.context,
                                last_checked_ts = excluded.last_checked_ts
                        """), {
                            'ts': thread_ts,
                            'channel': target_channel,
                            'context': f"SLA violation: {violation['item_id']}",
                            'last_ts': '0',
                            'now': _dt.now(),
                        })
                    print(f"   📌 Registered thread for monitoring: {thread_ts}")
                except Exception as reg_error:
                    print(f"   ⚠️  Could not register thread: {reg_error}")

            else:
                print(f"   ❌ Failed to post {violation['item_id']}: {result.get('error')}")

        print(f"\n   ✅ Posted {posted_count}/{len(violations)} violations to Slack")
        if skipped_count > 0:
            print(f"   ⏭️  Skipped {skipped_count} violations (alerted within last 24h)")
        return posted_count

    except Exception as e:
        print(f"   ❌ Error posting to Slack: {e}")
        return posted_count


def save_snapshot(violations: List[Dict[str, Any]]):
    """Save daily snapshot of violations"""
    data_dir = Path(".claude/data/sla-tracking/daily-snapshots")
    data_dir.mkdir(parents=True, exist_ok=True)

    snapshot_file = data_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"

    snapshot = {
        "date": datetime.now().isoformat(),
        "total_violations": len(violations),
        "by_severity": {
            "critical": len([v for v in violations if v.get("severity") == "critical"]),
            "warning": len([v for v in violations if v.get("severity") == "warning"]),
        },
        "violations": violations
    }

    with open(snapshot_file, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\n💾 Saved snapshot to {snapshot_file}")


def main():
    """Main entrypoint"""
    import argparse

    parser = argparse.ArgumentParser(description="SLA Monitor - Working Implementation")
    parser.add_argument("--no-slack", action="store_true", help="Skip posting to Slack")
    parser.add_argument("--skip-jira", action="store_true", help="Skip Jira checks (PRs only)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔍 SLA MONITORING CHECK")
    print("=" * 60)

    # Log check start to dashboard database
    run_id = None
    if HAS_DASHBOARD_DB:
        try:
            db = get_dashboard_db()
            run_id = db.log_check_start('sla-check', triggered_by='scheduled')
            print(f"📊 Logging to dashboard (run_id: {run_id})")
        except Exception as e:
            print(f"⚠️  Could not log check start to dashboard: {e}")

    all_violations = []
    check_errors = []

    # Check PRs (Bitbucket)
    try:
        all_violations.extend(check_pr_slas())
    except Exception as e:
        check_errors.append(f"PR check error: {e}")
        print(f"⚠️  PR check failed: {e}")

    # Check Jira (via direct Python CLI tools)
    if not args.skip_jira:
        try:
            all_violations.extend(check_jira_slas_direct())
        except Exception as e:
            check_errors.append(f"Jira check error: {e}")
            print(f"⚠️  Jira check failed: {e}")
    else:
        print("\n⏭️  Skipping Jira checks (--skip-jira flag)")

    # Log SLA check activity with detailed statistics
    try:
        # Add project root to path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        from src.activity_tracker import get_tracker
        tracker = get_tracker()

        # Calculate totals
        total_tickets = len([v for v in all_violations if v.get('type') in ['qa_stale', 'pending_approval', 'blocked_ticket', 'changes_requested']])
        total_prs = len([v for v in all_violations if v.get('type') == 'pr_stale'])
        critical_count = len([v for v in all_violations if v.get('severity') == 'critical'])
        warning_count = len([v for v in all_violations if v.get('severity') == 'warning'])

        # Create summary message for heartbeat
        details = f"Checked Jira tickets and PRs | Violations: {len(all_violations)} ({critical_count} critical, {warning_count} warnings)"

        tracker.log(
            "sla_check",
            details,
            success=True
        )
    except Exception as e:
        print(f"⚠️  Could not log to activity tracker: {e}")

    # Store violations in dashboard database
    if HAS_DASHBOARD_DB and all_violations:
        try:
            db = get_dashboard_db()
            for violation in all_violations:
                # Add detected_at timestamp if not present
                if 'detected_at' not in violation:
                    violation['detected_at'] = datetime.now().isoformat()
                db.upsert_violation(violation)
            print(f"📊 Stored {len(all_violations)} violations in dashboard database")
        except Exception as e:
            print(f"⚠️  Could not store violations in dashboard: {e}")

    # Process escalations (Jira comments + Slack threads)
    if HAS_ESCALATION and all_violations:
        dry_run = args.no_slack  # Use same flag for dry run
        all_violations = process_violations(all_violations, dry_run=dry_run)

        # Print escalation summary
        escalation_summary = generate_escalation_summary(all_violations)
        print(escalation_summary)

    # Print summary to console
    print("\n" + "=" * 60)
    print("🔍 SLA VIOLATIONS SUMMARY")
    print("=" * 60)
    print(f"\n📊 Total Violations: {len(all_violations)}")
    print(f"• Critical: {len([v for v in all_violations if v.get('severity') == 'critical'])}")
    print(f"• Warnings: {len([v for v in all_violations if v.get('severity') == 'warning'])}\n")

    if all_violations:
        print("Violations found:")
        for v in all_violations:
            severity_marker = "⚠️ " if v.get("severity") == "critical" else "⏰ "
            print(f"  {severity_marker}{v['item_id']}: {v.get('title', 'No title')[:60]}...")
    else:
        print("✅ No violations found - all items within SLA targets!")

    print("=" * 60)

    # Post to Slack (individual messages per violation)
    if not args.no_slack and all_violations:
        posted_count = post_violations_to_slack(all_violations)

        # Log to PM agent logs channel
        if posted_count > 0:
            log_message = f"📊 *SLA Check Complete*\n"
            log_message += f"• Total Violations: {len(all_violations)}\n"
            log_message += f"• Critical: {len([v for v in all_violations if v.get('severity') == 'critical'])}\n"
            log_message += f"• Warnings: {len([v for v in all_violations if v.get('severity') == 'warning'])}\n"
            log_message += f"\nPosted {posted_count} individual violation messages to #ecd-standup"
            log_to_pm_channel(log_message)
    elif not args.no_slack and not all_violations:
        # No violations to post
        log_message = "✅ *SLA Check Complete*\nNo violations found - all items within SLA targets!"
        log_to_pm_channel(log_message)
    else:
        print("\n⏭️  Skipping Slack post (--no-slack flag)")

    # Save snapshot
    save_snapshot(all_violations)

    if check_errors:
        print(f"\n⚠️  SLA check completed with {len(check_errors)} error(s):")
        for err in check_errors:
            print(f"   • {err}")
    else:
        print(f"\n✅ SLA check complete - found {len(all_violations)} violations")

    # Log check completion to dashboard database
    if HAS_DASHBOARD_DB and run_id:
        try:
            critical_count = len([v for v in all_violations if v.get("severity") == "critical"])
            warning_count = len([v for v in all_violations if v.get("severity") == "warning"])
            error_message = "\n".join(check_errors) if check_errors else None
            db.log_check_complete(
                run_id,
                violations_found=len(all_violations),
                critical_count=critical_count,
                warning_count=warning_count,
                error_message=error_message
            )

            # Update schedule last_run timestamp
            db.update_schedule_last_run('sla-check')

            print(f"📊 Dashboard updated: {len(all_violations)} violations ({critical_count} critical, {warning_count} warnings)")
        except Exception as e:
            print(f"⚠️  Could not log check completion to dashboard: {e}")

    # Exit with non-zero if critical violations found
    critical_count = len([v for v in all_violations if v.get("severity") == "critical"])
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
