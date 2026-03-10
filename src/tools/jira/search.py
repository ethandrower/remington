#!/usr/bin/env python3
"""
Jira Search Tool - Search issues using JQL

Mirrors: mcp__atlassian__searchJiraIssuesUsingJql

Usage:
    python -m src.tools.jira.search "project = ECD AND status = 'In Progress'"
    python -m src.tools.jira.search "assignee = currentUser()" --max-results 20
    python -m src.tools.jira.search "project = ECD" --fields summary,status,assignee
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def search_jira(
    jql: str,
    max_results: int = 50,
    fields: Optional[list] = None,
    expand: Optional[list] = None
) -> dict:
    """
    Search Jira issues using JQL (Jira Query Language)

    Args:
        jql: JQL query string (e.g., "project = ECD AND status = 'In Progress'")
        max_results: Maximum number of results to return (default 50, max 100)
        fields: List of fields to return (default: common fields)
        expand: List of expansions (e.g., ["changelog", "renderedFields"])

    Returns:
        dict: {
            "total": int,           # Total matching issues
            "count": int,           # Number returned
            "issues": [             # Simplified issue list
                {
                    "key": "ECD-123",
                    "summary": "...",
                    "status": "In Progress",
                    "assignee": "Name",
                    "priority": "High",
                    "type": "Story",
                    "created": "2025-01-01T...",
                    "updated": "2025-01-02T..."
                }
            ]
        }
    """
    if fields is None:
        fields = [
            "summary", "status", "assignee", "priority",
            "created", "updated", "issuetype", "labels",
            "reporter", "description"
        ]

    payload = {
        "jql": jql,
        "maxResults": min(max_results, 100),
        "fields": fields
    }

    if expand:
        payload["expand"] = expand

    try:
        # Use the new JQL search endpoint (api/3/search is deprecated)
        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        # Simplify the response for easier consumption
        simplified_issues = []
        for issue in data.get("issues", []):
            fields_data = issue.get("fields", {})

            simplified = {
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields_data.get("summary"),
                "status": fields_data.get("status", {}).get("name") if fields_data.get("status") else None,
                "assignee": fields_data.get("assignee", {}).get("displayName") if fields_data.get("assignee") else "Unassigned",
                "assignee_id": fields_data.get("assignee", {}).get("accountId") if fields_data.get("assignee") else None,
                "reporter": fields_data.get("reporter", {}).get("displayName") if fields_data.get("reporter") else None,
                "priority": fields_data.get("priority", {}).get("name") if fields_data.get("priority") else None,
                "type": fields_data.get("issuetype", {}).get("name") if fields_data.get("issuetype") else None,
                "labels": fields_data.get("labels", []),
                "created": fields_data.get("created"),
                "updated": fields_data.get("updated"),
            }
            simplified_issues.append(simplified)

        return {
            "total": data.get("total", 0),
            "count": len(simplified_issues),
            "issues": simplified_issues
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Search Jira issues using JQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Find all in-progress issues in ECD
    python -m src.tools.jira.search "project = ECD AND status = 'In Progress'"

    # Find issues assigned to current user
    python -m src.tools.jira.search "assignee = currentUser() AND sprint in openSprints()"

    # Find high priority bugs
    python -m src.tools.jira.search "project = ECD AND type = Bug AND priority = High"

    # Find recently updated issues
    python -m src.tools.jira.search "project = ECD AND updated >= -7d" --max-results 20
        """
    )
    parser.add_argument("jql", help="JQL query string")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum results (default: 50)")
    parser.add_argument("--fields", help="Comma-separated list of fields to return")

    args = parser.parse_args()

    fields = args.fields.split(",") if args.fields else None

    try:
        result = search_jira(args.jql, args.max_results, fields)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
