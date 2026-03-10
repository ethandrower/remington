#!/usr/bin/env python3
"""
Jira Get Transitions Tool - Get available status transitions for an issue

Mirrors: mcp__atlassian__getTransitionsForJiraIssue

Usage:
    python -m src.tools.jira.get_transitions ECD-123
"""

import argparse
import json
import sys

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def get_jira_transitions(issue_key: str) -> dict:
    """
    Get available status transitions for a Jira issue

    Args:
        issue_key: Issue key (e.g., "ECD-123")

    Returns:
        dict: {
            "issue_key": "ECD-123",
            "current_status": "In Progress",
            "transitions": [
                {
                    "id": "21",
                    "name": "Done",
                    "to_status": "Done",
                    "to_category": "Done"
                },
                ...
            ]
        }
    """
    try:
        # First get current status
        issue_response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            params={"fields": "status"},
            timeout=30
        )

        current_status = None
        if issue_response.status_code == 200:
            issue_data = issue_response.json()
            current_status = issue_data.get("fields", {}).get("status", {}).get("name")

        # Get available transitions
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=get_jira_auth_headers(),
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        transitions = []
        for t in data.get("transitions", []):
            transitions.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "to_status": t.get("to", {}).get("name"),
                "to_category": t.get("to", {}).get("statusCategory", {}).get("name"),
            })

        return {
            "issue_key": issue_key,
            "current_status": current_status,
            "transitions": transitions
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Get available status transitions for a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get available transitions
    python -m src.tools.jira.get_transitions ECD-123

    # Output shows current status and available transitions
    # Use the transition ID with transition_issue.py to change status
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")

    args = parser.parse_args()

    try:
        result = get_jira_transitions(args.issue_key)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
