#!/usr/bin/env python3
"""
Jira Status History Tool - Get status change history for a ticket

Usage:
    python -m src.tools.jira.get_status_history ECD-123
    python -m src.tools.jira.get_status_history ECD-123 --target-status "In QA"
    python -m src.tools.jira.get_status_history ECD-123 --all-transitions
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional, List, Dict

import requests
from dateutil import parser as date_parser

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def get_status_history(
    issue_key: str,
    target_status: Optional[str] = None,
    all_transitions: bool = False
) -> dict:
    """
    Get status change history for a Jira issue

    Args:
        issue_key: Issue key (e.g., "ECD-123")
        target_status: Specific status to find (e.g., "In QA")
        all_transitions: Return all status transitions (default: False)

    Returns:
        dict: {
            "issue_key": "ECD-123",
            "current_status": "In QA",
            "time_in_current_status_hours": 36.5,
            "entered_current_status": "2025-01-15T10:30:00Z",
            "status_history": [
                {
                    "from_status": "To Do",
                    "to_status": "In Progress",
                    "changed_at": "2025-01-10T09:00:00Z",
                    "changed_by": "John Doe"
                }
            ],
            "target_status_info": {  # Only if target_status is specified
                "status": "In QA",
                "entered_at": "2025-01-15T10:30:00Z",
                "hours_in_status": 36.5,
                "days_in_status": 1.52
            }
        }
    """
    try:
        # Fetch issue with changelog expansion
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            params={"expand": "changelog"},
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()
        fields = data.get("fields", {})
        changelog = data.get("changelog", {})

        # Get current status
        current_status = fields.get("status", {}).get("name")
        current_status_category = fields.get("status", {}).get("statusCategory", {}).get("name")

        # Parse status transitions from changelog
        status_transitions = []

        for history in changelog.get("histories", []):
            created = history.get("created")
            author = history.get("author", {}).get("displayName", "Unknown")

            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_status = item.get("fromString")
                    to_status = item.get("toString")

                    status_transitions.append({
                        "from_status": from_status,
                        "to_status": to_status,
                        "changed_at": created,
                        "changed_by": author
                    })

        # Sort by date (oldest first)
        status_transitions.sort(key=lambda x: x["changed_at"])

        # Find when current status was entered (most recent transition TO current status)
        entered_current_status = None
        for transition in reversed(status_transitions):
            if transition["to_status"] == current_status:
                entered_current_status = transition["changed_at"]
                break

        # If no transition found, use created date (ticket was created in this status)
        if not entered_current_status:
            entered_current_status = fields.get("created")

        # Calculate time in current status
        time_in_current_status_hours = None
        if entered_current_status:
            try:
                entered_dt = date_parser.parse(entered_current_status)
            except Exception:
                # Fallback to basic ISO format
                entered_dt = datetime.fromisoformat(entered_current_status.replace("Z", "+00:00"))

            now = datetime.now(entered_dt.tzinfo)
            delta = now - entered_dt
            time_in_current_status_hours = delta.total_seconds() / 3600

        result = {
            "issue_key": issue_key,
            "current_status": current_status,
            "current_status_category": current_status_category,
            "entered_current_status": entered_current_status,
            "time_in_current_status_hours": round(time_in_current_status_hours, 2) if time_in_current_status_hours else None,
            "time_in_current_status_days": round(time_in_current_status_hours / 24, 2) if time_in_current_status_hours else None,
        }

        # Include all transitions if requested
        if all_transitions:
            result["status_history"] = status_transitions

        # Find specific target status if requested
        if target_status:
            target_info = _find_target_status_info(
                status_transitions,
                target_status,
                current_status,
                entered_current_status
            )
            if target_info:
                result["target_status_info"] = target_info

        return result

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def _find_target_status_info(
    transitions: List[Dict],
    target_status: str,
    current_status: str,
    current_status_entry: str
) -> Optional[Dict]:
    """
    Find when a specific status was entered and calculate duration

    Returns info about the MOST RECENT time the ticket entered target_status
    """
    # Find most recent transition TO target status
    entered_at = None
    exited_at = None

    for i, transition in enumerate(reversed(transitions)):
        reversed_index = len(transitions) - 1 - i

        if transition["to_status"] == target_status:
            entered_at = transition["changed_at"]

            # Find when it exited (next transition FROM target_status)
            for j in range(reversed_index + 1, len(transitions)):
                next_transition = transitions[j]
                if next_transition["from_status"] == target_status:
                    exited_at = next_transition["changed_at"]
                    break

            break  # Found most recent entry

    if not entered_at:
        return None

    # Calculate duration
    try:
        entered_dt = date_parser.parse(entered_at)
    except Exception:
        entered_dt = datetime.fromisoformat(entered_at.replace("Z", "+00:00"))

    # If still in target status, use current time
    if target_status == current_status:
        exited_dt = datetime.now(entered_dt.tzinfo)
        still_in_status = True
    elif exited_at:
        try:
            exited_dt = date_parser.parse(exited_at)
        except Exception:
            exited_dt = datetime.fromisoformat(exited_at.replace("Z", "+00:00"))
        still_in_status = False
    else:
        # Entered but never exited (data issue?)
        exited_dt = datetime.now(entered_dt.tzinfo)
        still_in_status = False

    delta = exited_dt - entered_dt
    hours_in_status = delta.total_seconds() / 3600

    return {
        "status": target_status,
        "entered_at": entered_at,
        "exited_at": exited_at if not still_in_status else None,
        "still_in_status": still_in_status,
        "hours_in_status": round(hours_in_status, 2),
        "days_in_status": round(hours_in_status / 24, 2)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Get status change history for a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get current status and time in status
    python -m src.tools.jira.get_status_history ECD-123

    # Find when ticket entered "In QA" and how long it's been there
    python -m src.tools.jira.get_status_history ECD-123 --target-status "In QA"

    # Get full status transition history
    python -m src.tools.jira.get_status_history ECD-123 --all-transitions
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("--target-status", help="Specific status to analyze")
    parser.add_argument("--all-transitions", action="store_true", help="Include all status transitions")

    args = parser.parse_args()

    try:
        result = get_status_history(
            args.issue_key,
            target_status=args.target_status,
            all_transitions=args.all_transitions
        )
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
