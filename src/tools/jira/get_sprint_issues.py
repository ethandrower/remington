#!/usr/bin/env python3
"""
Jira Get Sprint Issues Tool - Get issues in a sprint

Usage:
    python -m src.tools.jira.get_sprint_issues 123
    python -m src.tools.jira.get_sprint_issues 123 --status Done
    python -m src.tools.jira.get_sprint_issues 123 --completed-only
"""

import argparse
import json
import sys
from typing import Optional, List

import requests

from ..base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID, format_error

AGILE_BASE_URL = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}/rest/agile/1.0"


def get_sprint_issues(
    sprint_id: int,
    status: Optional[str] = None,
    issue_types: Optional[List[str]] = None,
    max_results: int = 100
) -> dict:
    """
    Get issues in a sprint

    Args:
        sprint_id: The sprint ID
        status: Filter by status (e.g., "Done", "In Progress")
        issue_types: Filter by issue types (e.g., ["Story", "Bug"])
        max_results: Maximum results to return

    Returns:
        dict: {
            "sprint_id": int,
            "total": int,
            "count": int,
            "issues": [
                {
                    "key": "ECD-123",
                    "summary": "Feature title",
                    "status": "Done",
                    "type": "Story",
                    "assignee": "Name",
                    "priority": "High",
                    "story_points": 5,
                    "resolution": "Done",
                    "labels": ["feature", "v5.5.6"]
                }
            ]
        }
    """
    try:
        url = f"{AGILE_BASE_URL}/sprint/{sprint_id}/issue"
        params = {
            "maxResults": min(max_results, 100),
            "fields": "summary,status,issuetype,assignee,priority,customfield_10016,resolution,labels,description"
        }

        # Build JQL filter
        jql_parts = []
        if status:
            jql_parts.append(f'status = "{status}"')
        if issue_types:
            types_str = ", ".join([f'"{t}"' for t in issue_types])
            jql_parts.append(f"issuetype in ({types_str})")

        if jql_parts:
            params["jql"] = " AND ".join(jql_parts)

        response = requests.get(
            url,
            headers=get_jira_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        issues = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields.get("summary"),
                "description": fields.get("description"),
                "status": fields.get("status", {}).get("name") if fields.get("status") else None,
                "type": fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "story_points": fields.get("customfield_10016"),  # Story Points field
                "resolution": fields.get("resolution", {}).get("name") if fields.get("resolution") else None,
                "labels": fields.get("labels", [])
            })

        return {
            "sprint_id": sprint_id,
            "total": data.get("total", len(issues)),
            "count": len(issues),
            "issues": issues
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def get_completed_sprint_issues(
    sprint_id: int,
    exclude_types: Optional[List[str]] = None
) -> dict:
    """
    Get only completed issues from a sprint (for release notes)

    Args:
        sprint_id: The sprint ID
        exclude_types: Issue types to exclude (e.g., ["Sub-task", "Epic"])

    Returns:
        dict: Completed issues suitable for release notes
    """
    result = get_sprint_issues(sprint_id, status="Done", max_results=100)

    if result.get("error"):
        return result

    # Filter out excluded types
    if exclude_types:
        result["issues"] = [
            issue for issue in result["issues"]
            if issue["type"] not in exclude_types
        ]
        result["count"] = len(result["issues"])

    # Categorize by type
    by_type = {}
    for issue in result["issues"]:
        issue_type = issue["type"] or "Other"
        if issue_type not in by_type:
            by_type[issue_type] = []
        by_type[issue_type].append(issue)

    result["by_type"] = by_type

    return result


def main():
    parser = argparse.ArgumentParser(description="Get issues in a Jira sprint")
    parser.add_argument("sprint_id", type=int, help="Sprint ID")
    parser.add_argument("--status", help="Filter by status (e.g., 'Done')")
    parser.add_argument("--types", nargs="+", help="Filter by issue types")
    parser.add_argument("--completed-only", action="store_true", help="Only show completed (Done) issues")
    parser.add_argument("--max-results", type=int, default=100)

    args = parser.parse_args()

    if args.completed_only:
        result = get_completed_sprint_issues(args.sprint_id)
    else:
        result = get_sprint_issues(args.sprint_id, args.status, args.types, args.max_results)

    print(json.dumps(result, indent=2))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
