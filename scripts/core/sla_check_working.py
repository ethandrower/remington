#!/usr/bin/env python3
"""
Working SLA Monitor - Simplified version that actually works
Checks Jira and Bitbucket for SLA violations and posts to Slack with links
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

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
        workspace = bb_config.get("workspace", "citemed")
        repos = ["citemed_web"]

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
                            "link": f"https://bitbucket.org/citemed/{repo}/pull-requests/{pr_id}",
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


def check_jira_slas_via_claude() -> List[Dict[str, Any]]:
    """Check Jira SLAs using Claude with MCP tools"""
    print("\n📋 Checking Jira SLAs (via Claude MCP)...")

    violations = []

    try:
        # Use Claude to query Jira via MCP
        prompt = """Use the Atlassian MCP searchJiraIssuesUsingJql tool to find all open tickets in current sprint:

JQL: project = ECD AND sprint in openSprints() AND status NOT IN (Done, Closed, Cancelled)

For each ticket, check:
1. If in "Pending Approval" status for > 48 hours
2. If in "Blocked" status for > 24 hours
3. If comments have no response from assignee in > 48 hours (2 business days)

Return a JSON array of violations with this format:
[
  {
    "type": "pending_approval" | "blocked_ticket" | "comment_response",
    "severity": "warning" | "critical",
    "item_id": "ECD-XXX",
    "title": "ticket title",
    "owner": "assignee name",
    "hours_overdue": number,
    "link": "https://citemed.atlassian.net/browse/ECD-XXX",
    "message": "description of violation"
  }
]

If no violations, return empty array: []
"""

        result = subprocess.run(
            ["claude", "-p", "--output-format", "text", "--settings", ".claude/settings.local.json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            output = result.stdout.strip()

            # Try to extract JSON from Claude's response
            # Claude might wrap it in markdown code blocks
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            elif "```" in output:
                json_start = output.find("```") + 3
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            else:
                # Try to find JSON array in the output
                if "[" in output and "]" in output:
                    json_start = output.find("[")
                    json_end = output.rfind("]") + 1
                    json_str = output[json_start:json_end]
                else:
                    json_str = "[]"

            try:
                violations = json.loads(json_str)
                print(f"   Found {len(violations)} Jira violations")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Could not parse Claude response as JSON: {e}")
                print(f"   Response preview: {output[:200]}...")

        else:
            print(f"   ❌ Claude error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("   ⏱️  Claude timed out after 2 minutes")
    except Exception as e:
        print(f"   ❌ Error checking Jira: {e}")

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
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    log_channel = os.getenv("SLACK_PM_AGENT_LOG_CHANNEL")

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

    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel = os.getenv("SLACK_CHANNEL_STANDUP")

    if not slack_token or not slack_channel:
        print("   ❌ Missing SLACK_BOT_TOKEN or SLACK_CHANNEL_STANDUP in .env")
        return 0

    # Clean tokens
    clean_token = slack_token.strip('"\'')
    clean_channel = slack_channel.strip('"\'')

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

            result = response.json()
            if result.get("ok"):
                posted_count += 1
                thread_ts = result.get("ts")
                print(f"   ✅ Posted {violation['item_id']} (thread_ts: {thread_ts})")

                # Store thread_ts in violation for future tracking
                violation["slack_thread_ts"] = thread_ts

                # Record this alert in the deduplication database
                try:
                    record_alert(violation, slack_thread_ts=thread_ts)
                except Exception as record_error:
                    print(f"   ⚠️  Could not record alert: {record_error}")

                # Register thread for monitoring (so we can detect replies)
                try:
                    sys.path.append(str(Path(__file__).parent.parent / "bots"))
                    from slack_monitor import SlackMonitor
                    import sqlite3

                    # Directly register thread in database
                    db_path = Path(".claude/data/bot-state/slack_state.db")
                    with sqlite3.connect(db_path) as conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO tracked_threads
                            (thread_ts, channel, context, last_checked_ts)
                            VALUES (?, ?, ?, ?)
                            """,
                            (thread_ts, clean_channel, f"SLA violation: {violation['item_id']}", "0"),
                        )
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

    all_violations = []

    # Check PRs (Bitbucket)
    all_violations.extend(check_pr_slas())

    # Check Jira (via Claude MCP)
    if not args.skip_jira:
        all_violations.extend(check_jira_slas_via_claude())
    else:
        print("\n⏭️  Skipping Jira checks (--skip-jira flag)")

    # Log SLA check activity
    try:
        sys.path.append(str(Path(__file__).parent.parent))
        from src.activity_tracker import get_tracker
        tracker = get_tracker()
        tracker.log(
            "sla_check",
            f"Found {len(all_violations)} violations ({len([v for v in all_violations if v.get('severity') == 'critical'])} critical, {len([v for v in all_violations if v.get('severity') == 'warning'])} warnings)",
            success=True
        )
    except Exception as e:
        print(f"⚠️  Could not log to activity tracker: {e}")

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

    print(f"\n✅ SLA check complete - found {len(all_violations)} violations")

    # Exit with non-zero if critical violations found
    critical_count = len([v for v in all_violations if v.get("severity") == "critical"])
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
