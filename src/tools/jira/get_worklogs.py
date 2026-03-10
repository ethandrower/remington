#!/usr/bin/env python3
"""
Jira Get Worklogs Tool - Fetch time-tracking worklogs for an issue

Uses Jira's native startedAfter/startedBefore millisecond timestamp filters
so we never over-fetch. Handles pagination automatically.

Usage:
    python -m src.tools.jira.get_worklogs ECD-123
    python -m src.tools.jira.get_worklogs ECD-123 --days 7
    python -m src.tools.jira.get_worklogs ECD-123 --since 2025-01-13
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def _to_ms(dt: datetime) -> int:
    """Convert datetime to Unix milliseconds (Jira's filter format)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fmt_seconds(seconds: int) -> str:
    """Format seconds as a human-readable duration (e.g., '3h 30m')."""
    if seconds <= 0:
        return "0h"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    elif hours:
        return f"{hours}h"
    else:
        return f"{minutes}m"


def get_issue_worklogs(
    issue_key: str,
    started_after: Optional[datetime] = None,
    started_before: Optional[datetime] = None,
) -> dict:
    """
    Get worklogs for a Jira issue, optionally filtered by date range.

    Args:
        issue_key: Issue key (e.g., "ECD-123")
        started_after: Only return worklogs on or after this datetime
        started_before: Only return worklogs before this datetime

    Returns:
        dict: {
            "issue_key": str,
            "total": int,
            "total_seconds": int,
            "worklogs": [
                {
                    "id": str,
                    "author": str,           # display name
                    "author_id": str,        # accountId
                    "started": str,          # ISO datetime string
                    "time_spent": str,       # e.g. "3h 30m"
                    "time_spent_seconds": int,
                    "comment": str,
                }
            ]
        }
    """
    params: dict = {"maxResults": 5000}
    if started_after:
        params["startedAfter"] = _to_ms(started_after)
    if started_before:
        params["startedBefore"] = _to_ms(started_before)

    all_worklogs = []
    start_at = 0

    try:
        while True:
            params["startAt"] = start_at
            response = requests.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/worklog",
                headers=get_jira_auth_headers(),
                params=params,
                timeout=30,
            )

            if response.status_code == 404:
                return format_error(404, f"Issue {issue_key} not found")
            if response.status_code != 200:
                return format_error(response.status_code, response.text)

            data = response.json()
            page = data.get("worklogs", [])
            all_worklogs.extend(page)

            total_server = data.get("total", 0)
            max_results = data.get("maxResults", 5000)
            if start_at + max_results >= total_server or not page:
                break
            start_at += max_results

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))

    simplified = []
    total_seconds = 0

    for wl in all_worklogs:
        author = wl.get("author", {})

        # Extract plain text from ADF comment if present
        comment_raw = wl.get("comment", "") or ""
        if isinstance(comment_raw, dict):
            try:
                texts = []
                for para in comment_raw.get("content", []):
                    for node in para.get("content", []):
                        if node.get("type") == "text":
                            texts.append(node.get("text", ""))
                comment_raw = " ".join(texts).strip()
            except Exception:
                comment_raw = ""

        seconds = wl.get("timeSpentSeconds", 0)
        total_seconds += seconds

        simplified.append({
            "id": wl.get("id", ""),
            "author": author.get("displayName", "Unknown"),
            "author_id": author.get("accountId", ""),
            "started": wl.get("started", ""),
            "time_spent": fmt_seconds(seconds),
            "time_spent_seconds": seconds,
            "comment": str(comment_raw)[:200],
        })

    return {
        "issue_key": issue_key,
        "total": len(simplified),
        "total_seconds": total_seconds,
        "worklogs": simplified,
    }


def main():
    parser = argparse.ArgumentParser(description="Get Jira worklogs for an issue")
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("--days", type=int, help="Only worklogs from the last N days")
    parser.add_argument("--since", type=str, help="Only worklogs since YYYY-MM-DD")
    args = parser.parse_args()

    started_after = None
    if args.days:
        started_after = datetime.now(timezone.utc) - timedelta(days=args.days)
    elif args.since:
        started_after = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    result = get_issue_worklogs(args.issue_key, started_after=started_after)
    print(json.dumps(result, indent=2))

    if result.get("error"):
        sys.exit(1)

    total = result.get("total_seconds", 0)
    print(f"\nTotal: {fmt_seconds(total)} across {result['total']} entries", file=sys.stderr)


if __name__ == "__main__":
    main()
