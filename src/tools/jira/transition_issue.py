#!/usr/bin/env python3
"""
Jira Transition Issue Tool - Change the status of a Jira issue

Mirrors: mcp__atlassian__transitionJiraIssue

Usage:
    python -m src.tools.jira.transition_issue ECD-123 "Done"
    python -m src.tools.jira.transition_issue ECD-123 "In Progress"
    python -m src.tools.jira.transition_issue ECD-123 --transition-id 21
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error
from .get_transitions import get_jira_transitions


def transition_jira_issue(
    issue_key: str,
    transition_name: Optional[str] = None,
    transition_id: Optional[str] = None,
    fields: Optional[dict] = None,
    comment: Optional[str] = None
) -> dict:
    """
    Transition a Jira issue to a new status

    Args:
        issue_key: Issue key (e.g., "ECD-123")
        transition_name: Name of the transition (e.g., "Done", "In Progress")
        transition_id: ID of the transition (takes precedence over name)
        fields: Optional fields to set during transition
        comment: Optional comment to add during transition

    Returns:
        dict: {
            "success": True,
            "issue_key": "ECD-123",
            "transition": "Done",
            "new_status": "Done"
        }
    """
    if not transition_id and not transition_name:
        return format_error(400, "Either transition_name or transition_id is required")

    # If only name provided, look up the ID
    if not transition_id:
        transitions = get_jira_transitions(issue_key)
        if transitions.get("error"):
            return transitions

        # Find matching transition
        matched = None
        for t in transitions.get("transitions", []):
            if t["name"].lower() == transition_name.lower() or \
               t["to_status"].lower() == transition_name.lower():
                matched = t
                break

        if not matched:
            available = [f"{t['name']} -> {t['to_status']}" for t in transitions.get("transitions", [])]
            return format_error(
                400,
                f"Transition '{transition_name}' not available. "
                f"Current status: {transitions.get('current_status')}. "
                f"Available: {', '.join(available)}"
            )

        transition_id = matched["id"]

    # Build transition payload
    payload = {
        "transition": {"id": str(transition_id)}
    }

    if fields:
        payload["fields"] = fields

    if comment:
        payload["update"] = {
            "comment": [{"add": {"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}}]
        }

    try:
        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        # 204 No Content means success
        if response.status_code == 204:
            # Get new status
            issue_response = requests.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
                headers=get_jira_auth_headers(),
                params={"fields": "status"},
                timeout=30
            )
            new_status = None
            if issue_response.status_code == 200:
                new_status = issue_response.json().get("fields", {}).get("status", {}).get("name")

            return {
                "success": True,
                "issue_key": issue_key,
                "transition_id": transition_id,
                "new_status": new_status,
            }

        return format_error(response.status_code, response.text)

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Transition a Jira issue to a new status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Transition by status name
    python -m src.tools.jira.transition_issue ECD-123 "Done"
    python -m src.tools.jira.transition_issue ECD-123 "In Progress"

    # Transition by ID (from get_transitions)
    python -m src.tools.jira.transition_issue ECD-123 --transition-id 21

    # Transition with comment
    python -m src.tools.jira.transition_issue ECD-123 "Done" --comment "Completed review"

Tip: Use get_transitions.py first to see available transitions
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("transition", nargs="?", help="Transition name (e.g., 'Done', 'In Progress')")
    parser.add_argument("--transition-id", help="Transition ID (takes precedence over name)")
    parser.add_argument("--comment", help="Comment to add during transition")

    args = parser.parse_args()

    if not args.transition and not args.transition_id:
        parser.error("Either transition name or --transition-id is required")

    try:
        result = transition_jira_issue(
            args.issue_key,
            transition_name=args.transition,
            transition_id=args.transition_id,
            comment=args.comment
        )
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)
        else:
            print(f"Transitioned {args.issue_key} to {result.get('new_status')}", file=sys.stderr)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
