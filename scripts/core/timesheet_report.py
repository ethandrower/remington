#!/usr/bin/env python3
"""
Weekly Timesheet Report

Pulls Jira worklogs for the prior Mon–Sun week, groups by developer,
and posts a summary to Slack. Devs are paid what they report — no
expected-hours enforcement, just a clean record for reconciliation.

Usage:
    python scripts/core/timesheet_report.py                  # last full week
    python scripts/core/timesheet_report.py --dry-run        # print only, no Slack
    python scripts/core/timesheet_report.py --week-offset 1  # two weeks ago
    python scripts/core/timesheet_report.py --current-week   # Mon to today (mid-week)
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

import pytz
import requests

from trinity.jira import search_jira, get_issue_worklogs, fmt_seconds


def get_week_bounds(week_offset: int = 0, current_week: bool = False) -> tuple:
    """
    Return (week_start, week_end) as timezone-aware datetimes.

    week_offset=0  → last completed Mon–Sun
    week_offset=1  → two weeks ago
    current_week   → this week Mon 00:00 to now
    """
    tz_name = os.getenv("BUSINESS_TIMEZONE", "America/New_York")
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)

    # Find last Monday (or this Monday if today is Monday)
    days_since_monday = now.weekday()  # Monday=0

    if current_week:
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = now
    else:
        # Go back to the most recently *completed* week
        # If today is Monday, last week ended yesterday (Sunday)
        last_sunday = now - timedelta(days=days_since_monday + 1)
        last_monday = last_sunday - timedelta(days=6)

        # Apply additional week offset
        last_monday -= timedelta(weeks=week_offset)
        last_sunday -= timedelta(weeks=week_offset)

        week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return week_start, week_end


def fetch_timesheet_data(week_start: datetime, week_end: datetime) -> dict:
    """
    Fetch all worklogs for the project within the given week.

    Returns a dict keyed by developer account_id:
    {
        "account_id": {
            "name": str,
            "total_seconds": int,
            "issues": {
                "ECD-123": {
                    "summary": str,
                    "status": str,
                    "estimate_seconds": int,
                    "logged_seconds": int,
                    "entries": [worklog, ...]
                }
            }
        }
    }
    """
    raw_keys = [k.strip() for k in os.getenv("ATLASSIAN_PROJECT_KEY", "").split(",") if k.strip()]
    project_clause = (
        f'project IN ({", ".join(raw_keys)})'
        if len(raw_keys) > 1
        else f'project = {raw_keys[0] if raw_keys else ""}'
    )

    # JQL date format: YYYY-MM-DD
    date_from = week_start.strftime("%Y-%m-%d")
    date_to = week_end.strftime("%Y-%m-%d")

    print(f"  Searching for issues with worklogs {date_from} → {date_to}...")

    jql = (
        f'{project_clause} AND worklogDate >= "{date_from}" '
        f'AND worklogDate <= "{date_to}" ORDER BY updated DESC'
    )

    result = search_jira(
        jql,
        max_results=100,
        fields=["summary", "status", "assignee", "timeoriginalestimate", "timespent"],
    )

    if result.get("error"):
        raise Exception(f"Jira search failed: {result.get('message')}")

    issues = result.get("issues", [])
    print(f"  Found {len(issues)} issues with time logged this week")

    jira_url = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")
    developers: dict = {}

    for issue in issues:
        key = issue["key"]
        summary = issue.get("summary") or ""
        status = issue.get("status") or "Unknown"
        estimate_seconds = 0

        # Fetch raw issue for timeoriginalestimate (search tool doesn't expose it)
        # We include it in fields above but the simplified search strips it —
        # fetch the raw field value directly via the worklogs pass-through
        # (we'll compute from worklogs; estimate fetched separately below)

        # Fetch worklogs for this issue filtered to our week
        wl_result = get_issue_worklogs(issue["key"], started_after=week_start, started_before=week_end)
        if wl_result.get("error"):
            print(f"  ⚠️  Could not fetch worklogs for {key}: {wl_result.get('message')}")
            continue

        worklogs = wl_result.get("worklogs", [])
        if not worklogs:
            continue

        # Get original estimate + due date in one raw API call
        estimate_seconds, due_date = _get_issue_extras(key)

        for wl in worklogs:
            author_id = wl["author_id"]
            author_name = wl["author"]

            if author_id not in developers:
                developers[author_id] = {
                    "name": author_name,
                    "total_seconds": 0,
                    "issues": {},
                }

            dev = developers[author_id]
            dev["total_seconds"] += wl["time_spent_seconds"]

            if key not in dev["issues"]:
                dev["issues"][key] = {
                    "summary": summary,
                    "status": status,
                    "estimate_seconds": estimate_seconds,
                    "due_date": due_date,
                    "logged_seconds": 0,
                    "url": f"{jira_url}/browse/{key}",
                    "entries": [],
                }

            dev["issues"][key]["logged_seconds"] += wl["time_spent_seconds"]
            dev["issues"][key]["entries"].append(wl)

    return developers


def _get_issue_extras(issue_key: str) -> tuple:
    """Fetch timeoriginalestimate and duedate in one raw Jira API call.

    Returns:
        (estimate_seconds: int, due_date: str|None)  e.g. (14400, "2026-03-15")
    """
    from trinity.base import get_jira_auth_headers, JIRA_BASE_URL

    try:
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            params={"fields": "timeoriginalestimate,duedate"},
            timeout=15,
        )
        if response.status_code == 200:
            fields = response.json().get("fields", {})
            return (
                fields.get("timeoriginalestimate") or 0,
                fields.get("duedate"),  # "YYYY-MM-DD" or None
            )
    except Exception:
        pass
    return 0, None


def format_slack_report(developers: dict, week_start: datetime, week_end: datetime) -> list:
    """
    Build Slack blocks for the weekly timesheet report.
    Returns a list of Slack block objects.
    """
    week_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
    total_team_seconds = sum(d["total_seconds"] for d in developers.values())

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Weekly Timesheet — {week_label}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Team total logged: {fmt_seconds(total_team_seconds)}* across {len(developers)} developer(s)",
            },
        },
        {"type": "divider"},
    ]

    # Sort developers by total hours descending
    sorted_devs = sorted(developers.items(), key=lambda x: x[1]["total_seconds"], reverse=True)

    for _account_id, dev in sorted_devs:
        name = dev["name"]
        total = dev["total_seconds"]
        issues = dev["issues"]

        # Build per-issue lines
        issue_lines = []
        for key, info in sorted(issues.items(), key=lambda x: x[1]["logged_seconds"], reverse=True):
            logged = info["logged_seconds"]
            est = info["estimate_seconds"]
            status = info["status"]
            summary = info["summary"][:50]
            url = info["url"]

            est_part = f" / {fmt_seconds(est)} est" if est else ""
            over = logged > est > 0

            line = f"• <{url}|{key}> {summary}  [{status}]  *{fmt_seconds(logged)}{est_part}*"
            if over:
                line += "  ⚠️ over"
            issue_lines.append(line)

        dev_text = f"*👤 {name}* — *{fmt_seconds(total)} logged*\n" + "\n".join(issue_lines)

        # Slack section blocks have a 3000 char limit; chunk if needed
        if len(dev_text) > 2900:
            dev_text = dev_text[:2897] + "…"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": dev_text},
        })
        blocks.append({"type": "divider"})

    if not developers:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No time logged this week._"},
        })

    return blocks


def post_to_slack(blocks: list, week_label: str):
    """Post the timesheet report to Slack."""
    from src.utils.channel_config import get_channel
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    channel = get_channel("timesheets")

    if not slack_token or not channel:
        print("⚠️  Slack not configured — set SLACK_BOT_TOKEN and configure Timesheets channel in dashboard Settings")
        return False

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            },
            json={
                "channel": channel.strip('"'),
                "text": f"Weekly Timesheet — {week_label}",
                "blocks": blocks,
            },
            timeout=15,
        )

        if response.ok and response.json().get("ok"):
            print(f"  ✅ Timesheet posted to Slack ({channel})")
            return True
        else:
            print(f"  ❌ Slack post failed: {response.text}")
            return False

    except Exception as e:
        print(f"  ❌ Error posting to Slack: {e}")
        return False


def save_to_db(developers: dict, week_start: datetime, week_end: datetime):
    """Persist timesheet data to the shared database."""
    from src.database.connection import get_engine
    from src.database.schema import timesheet_weeks, timesheet_entries
    from sqlalchemy import text as sa_text

    engine = get_engine(default_path=str(PROJECT_ROOT / ".claude/data/bot-state/dashboard.db"))
    timesheet_weeks.create(engine, checkfirst=True)
    timesheet_entries.create(engine, checkfirst=True)
    # Add due_date column if it doesn't exist yet (migration for existing DBs)
    try:
        with engine.begin() as _c:
            _c.execute(sa_text("ALTER TABLE timesheet_entries ADD COLUMN due_date VARCHAR(20)"))
    except Exception:
        pass  # Column already exists
    week_start_str = week_start.strftime("%Y-%m-%d")
    week_end_str = week_end.strftime("%Y-%m-%d")
    now = datetime.now()

    try:
        with engine.begin() as conn:
            for account_id, dev in developers.items():
                total_estimate = sum(
                    info["estimate_seconds"] for info in dev["issues"].values()
                )

                conn.execute(sa_text("""
                    INSERT INTO timesheet_weeks
                        (account_id, developer_name, week_start, week_end,
                         total_seconds, total_estimate_seconds, recorded_at)
                    VALUES
                        (:account_id, :developer_name, :week_start, :week_end,
                         :total_seconds, :total_estimate_seconds, :recorded_at)
                    ON CONFLICT DO NOTHING
                """), {
                    "account_id": account_id, "developer_name": dev["name"],
                    "week_start": week_start_str, "week_end": week_end_str,
                    "total_seconds": dev["total_seconds"],
                    "total_estimate_seconds": total_estimate, "recorded_at": now,
                })
                conn.execute(sa_text("""
                    UPDATE timesheet_weeks
                    SET total_seconds = :total_seconds,
                        total_estimate_seconds = :total_estimate_seconds,
                        developer_name = :developer_name, recorded_at = :recorded_at
                    WHERE account_id = :account_id AND week_start = :week_start
                """), {
                    "account_id": account_id, "developer_name": dev["name"],
                    "week_start": week_start_str,
                    "total_seconds": dev["total_seconds"],
                    "total_estimate_seconds": total_estimate, "recorded_at": now,
                })

                for issue_key, info in dev["issues"].items():
                    conn.execute(sa_text("""
                        INSERT INTO timesheet_entries
                            (account_id, week_start, issue_key, summary, status,
                             logged_seconds, estimate_seconds, due_date, jira_url)
                        VALUES
                            (:account_id, :week_start, :issue_key, :summary, :status,
                             :logged_seconds, :estimate_seconds, :due_date, :jira_url)
                        ON CONFLICT DO NOTHING
                    """), {
                        "account_id": account_id, "week_start": week_start_str,
                        "issue_key": issue_key, "summary": info["summary"],
                        "status": info["status"],
                        "logged_seconds": info["logged_seconds"],
                        "estimate_seconds": info["estimate_seconds"],
                        "due_date": info.get("due_date"),
                        "jira_url": info.get("url", ""),
                    })
                    conn.execute(sa_text("""
                        UPDATE timesheet_entries
                        SET summary = :summary, status = :status,
                            logged_seconds = :logged_seconds,
                            estimate_seconds = :estimate_seconds,
                            due_date = :due_date, jira_url = :jira_url
                        WHERE account_id = :account_id
                          AND week_start = :week_start AND issue_key = :issue_key
                    """), {
                        "account_id": account_id, "week_start": week_start_str,
                        "issue_key": issue_key, "summary": info["summary"],
                        "status": info["status"],
                        "logged_seconds": info["logged_seconds"],
                        "estimate_seconds": info["estimate_seconds"],
                        "due_date": info.get("due_date"),
                        "jira_url": info.get("url", ""),
                    })

        print(f"  💾 Saved to DB ({len(developers)} developer(s), week {week_start_str})")
    except Exception as e:
        print(f"  ⚠️  DB save failed: {e}")


def save_snapshot(developers: dict, week_start: datetime):
    """Save JSON snapshot for historical records."""
    snapshots_dir = PROJECT_ROOT / ".claude" / "data" / "timesheets"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    week_str = week_start.strftime("W%Y-%m-%d")
    snapshot_file = snapshots_dir / f"{week_str}.json"

    snapshot = {
        "week_start": week_start.isoformat(),
        "generated_at": datetime.now().isoformat(),
        "developers": developers,
    }

    snapshot_file.write_text(json.dumps(snapshot, indent=2))
    print(f"  💾 Snapshot saved: {snapshot_file}")


def run(week_offset: int = 0, current_week: bool = False, dry_run: bool = False):
    """Main entry point."""
    print(f"\n{'='*60}")
    print("  📋 WEEKLY TIMESHEET REPORT")
    if dry_run:
        print("  MODE: DRY RUN (no Slack messages)")
    print(f"{'='*60}\n")

    week_start, week_end = get_week_bounds(week_offset=week_offset, current_week=current_week)
    week_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

    print(f"Period: {week_label}")
    print(f"  From: {week_start.isoformat()}")
    print(f"  To:   {week_end.isoformat()}\n")

    print("Fetching worklog data from Jira...")
    developers = fetch_timesheet_data(week_start, week_end)

    print(f"\nBuilding report for {len(developers)} developer(s)...")
    blocks = format_slack_report(developers, week_start, week_end)

    # Always print a plain-text summary to stdout
    print(f"\n{'='*60}")
    print(f"  TIMESHEET SUMMARY — {week_label}")
    print(f"{'='*60}")
    if not developers:
        print("  No time logged this week.")
    else:
        for _account_id, dev in sorted(developers.items(), key=lambda x: x[1]["total_seconds"], reverse=True):
            print(f"\n  👤 {dev['name']} — {fmt_seconds(dev['total_seconds'])}")
            for key, info in sorted(dev["issues"].items(), key=lambda x: x[1]["logged_seconds"], reverse=True):
                logged = fmt_seconds(info["logged_seconds"])
                est = fmt_seconds(info["estimate_seconds"]) if info["estimate_seconds"] else "no est"
                over = "⚠️ over" if info["logged_seconds"] > info["estimate_seconds"] > 0 else ""
                print(f"    {key}  [{info['status']}]  {logged} / {est}  {over}")
                print(f"      {info['summary'][:60]}")

    total_team = sum(d["total_seconds"] for d in developers.values())
    print(f"\n  Team total: {fmt_seconds(total_team)}")
    print(f"{'='*60}\n")

    # Save snapshot and DB record regardless of dry-run
    save_snapshot(developers, week_start)
    save_to_db(developers, week_start, week_end)

    if dry_run:
        print("🔇 Dry-run: Slack post skipped.")
        print("   Blocks that would be sent:")
        print(json.dumps(blocks, indent=2))
    else:
        post_to_slack(blocks, week_label)

    return developers


def main():
    parser = argparse.ArgumentParser(description="Weekly Jira Timesheet Report")
    parser.add_argument("--dry-run", action="store_true", help="Print report without posting to Slack")
    parser.add_argument("--week-offset", type=int, default=0, help="0=last week (default), 1=two weeks ago, etc.")
    parser.add_argument("--current-week", action="store_true", help="Report on current week Mon–today")
    args = parser.parse_args()

    run(week_offset=args.week_offset, current_week=args.current_week, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
