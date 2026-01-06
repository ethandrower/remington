#!/usr/bin/env python3
"""
Jira Edit Issue Tool - Update fields on a Jira issue

Mirrors: mcp__atlassian__editJiraIssue

Usage:
    python -m src.tools.jira.edit_issue ECD-123 --assignee "712020:xxx"
    python -m src.tools.jira.edit_issue ECD-123 --priority High
    python -m src.tools.jira.edit_issue ECD-123 --labels "backend,urgent"
    python -m src.tools.jira.edit_issue ECD-123 --summary "New title"
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def edit_jira_issue(
    issue_key: str,
    fields: Optional[dict] = None,
    update: Optional[dict] = None
) -> dict:
    """
    Update fields on a Jira issue

    Args:
        issue_key: Issue key (e.g., "ECD-123")
        fields: Dict of fields to set
                Example: {"summary": "New title", "priority": {"name": "High"}}
        update: Dict of field operations (add, set, remove)
                Example: {"labels": [{"add": "urgent"}]}

    Returns:
        dict: {
            "success": True,
            "issue_key": "ECD-123",
            "fields_updated": ["summary", "priority"]
        }
    """
    if not fields and not update:
        return format_error(400, "No fields or updates provided")

    payload = {}
    if fields:
        payload["fields"] = fields
    if update:
        payload["update"] = update

    try:
        response = requests.put(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        # 204 No Content means success
        if response.status_code == 204:
            return {
                "success": True,
                "issue_key": issue_key,
                "fields_updated": list(fields.keys()) if fields else [],
                "updates_applied": list(update.keys()) if update else [],
            }

        return format_error(response.status_code, response.text)

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Update fields on a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Update assignee
    python -m src.tools.jira.edit_issue ECD-123 --assignee "712020:xxx"

    # Update priority
    python -m src.tools.jira.edit_issue ECD-123 --priority High

    # Update summary
    python -m src.tools.jira.edit_issue ECD-123 --summary "New issue title"

    # Add labels
    python -m src.tools.jira.edit_issue ECD-123 --add-labels "backend,urgent"

    # Set labels (replace all)
    python -m src.tools.jira.edit_issue ECD-123 --labels "frontend,ui"

    # Multiple fields at once
    python -m src.tools.jira.edit_issue ECD-123 --priority High --assignee "712020:xxx"

    # Raw JSON fields
    python -m src.tools.jira.edit_issue ECD-123 --json '{"summary": "New title"}'
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("--assignee", help="Account ID of assignee (use 'none' to unassign)")
    parser.add_argument("--priority", help="Priority name (e.g., High, Medium, Low)")
    parser.add_argument("--summary", help="New summary/title")
    parser.add_argument("--labels", help="Comma-separated labels (replaces existing)")
    parser.add_argument("--add-labels", help="Comma-separated labels to add")
    parser.add_argument("--remove-labels", help="Comma-separated labels to remove")
    parser.add_argument("--json", help="Raw JSON fields dict")

    args = parser.parse_args()

    fields = {}
    update = {}

    # Handle raw JSON
    if args.json:
        try:
            fields = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": True, "message": f"Invalid JSON: {e}"}), file=sys.stderr)
            sys.exit(1)

    # Handle individual fields
    if args.assignee:
        if args.assignee.lower() == "none":
            fields["assignee"] = None
        else:
            fields["assignee"] = {"accountId": args.assignee}

    if args.priority:
        fields["priority"] = {"name": args.priority}

    if args.summary:
        fields["summary"] = args.summary

    if args.labels:
        fields["labels"] = [l.strip() for l in args.labels.split(",")]

    # Handle label operations
    if args.add_labels:
        update["labels"] = [{"add": l.strip()} for l in args.add_labels.split(",")]

    if args.remove_labels:
        if "labels" not in update:
            update["labels"] = []
        update["labels"].extend([{"remove": l.strip()} for l in args.remove_labels.split(",")])

    if not fields and not update:
        parser.error("At least one field update is required")

    try:
        result = edit_jira_issue(args.issue_key, fields if fields else None, update if update else None)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)
        else:
            print(f"Updated {args.issue_key}", file=sys.stderr)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
