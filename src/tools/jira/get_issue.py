#!/usr/bin/env python3
"""
Jira Get Issue Tool - Get full details of a Jira issue

Mirrors: mcp__atlassian__getJiraIssue

Usage:
    python -m src.tools.jira.get_issue ECD-123
    python -m src.tools.jira.get_issue ECD-123 --fields summary,status,comments
    python -m src.tools.jira.get_issue ECD-123 --include-comments
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def get_jira_issue(
    issue_key: str,
    fields: Optional[list] = None,
    expand: Optional[list] = None,
    include_comments: bool = False
) -> dict:
    """
    Get full details of a Jira issue

    Args:
        issue_key: Issue key (e.g., "ECD-123") or issue ID
        fields: List of fields to return (default: all)
        expand: List of expansions (e.g., ["changelog", "renderedFields"])
        include_comments: Whether to include comments (default: False)

    Returns:
        dict: Issue details with simplified structure
    """
    params = {}

    if fields:
        params["fields"] = ",".join(fields)

    expand_list = expand or []
    if include_comments and "renderedFields" not in expand_list:
        expand_list.append("renderedFields")

    if expand_list:
        params["expand"] = ",".join(expand_list)

    try:
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
            headers=get_jira_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()
        fields_data = data.get("fields", {})

        # Build simplified response
        result = {
            "key": data.get("key"),
            "id": data.get("id"),
            "self": data.get("self"),
            "summary": fields_data.get("summary"),
            "description": _extract_text_from_adf(fields_data.get("description")),
            "status": fields_data.get("status", {}).get("name") if fields_data.get("status") else None,
            "status_category": fields_data.get("status", {}).get("statusCategory", {}).get("name") if fields_data.get("status") else None,
            "assignee": {
                "name": fields_data.get("assignee", {}).get("displayName") if fields_data.get("assignee") else "Unassigned",
                "account_id": fields_data.get("assignee", {}).get("accountId") if fields_data.get("assignee") else None,
                "email": fields_data.get("assignee", {}).get("emailAddress") if fields_data.get("assignee") else None,
            },
            "reporter": {
                "name": fields_data.get("reporter", {}).get("displayName") if fields_data.get("reporter") else None,
                "account_id": fields_data.get("reporter", {}).get("accountId") if fields_data.get("reporter") else None,
            },
            "priority": fields_data.get("priority", {}).get("name") if fields_data.get("priority") else None,
            "type": fields_data.get("issuetype", {}).get("name") if fields_data.get("issuetype") else None,
            "labels": fields_data.get("labels", []),
            "created": fields_data.get("created"),
            "updated": fields_data.get("updated"),
            "resolution": fields_data.get("resolution", {}).get("name") if fields_data.get("resolution") else None,
            "sprint": _extract_sprint_info(fields_data),
            "epic_key": fields_data.get("parent", {}).get("key") if fields_data.get("parent") else None,
            "story_points": fields_data.get("customfield_10016"),  # Common story points field
        }

        # Include comments if requested
        if include_comments:
            result["comments"] = _get_issue_comments(issue_key)

        return result

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def _extract_text_from_adf(adf: Optional[dict]) -> Optional[str]:
    """Extract plain text from Atlassian Document Format"""
    if not adf:
        return None

    text_parts = []

    def extract_recursive(content):
        if isinstance(content, dict):
            if content.get("type") == "text":
                text_parts.append(content.get("text", ""))
            for child in content.get("content", []):
                extract_recursive(child)
        elif isinstance(content, list):
            for item in content:
                extract_recursive(item)

    extract_recursive(adf)
    return " ".join(text_parts) if text_parts else None


def _extract_sprint_info(fields_data: dict) -> Optional[dict]:
    """Extract sprint information from fields"""
    # Sprint is often in customfield_10020
    sprint_field = fields_data.get("customfield_10020")
    if sprint_field and isinstance(sprint_field, list) and len(sprint_field) > 0:
        sprint = sprint_field[0]
        if isinstance(sprint, dict):
            return {
                "id": sprint.get("id"),
                "name": sprint.get("name"),
                "state": sprint.get("state"),
            }
    return None


def _get_issue_comments(issue_key: str, max_results: int = 20) -> list:
    """Get comments for an issue"""
    try:
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment",
            headers=get_jira_auth_headers(),
            params={"maxResults": max_results, "orderBy": "-created"},
            timeout=30
        )

        if response.status_code != 200:
            return []

        data = response.json()
        comments = []

        for comment in data.get("comments", []):
            comments.append({
                "id": comment.get("id"),
                "author": comment.get("author", {}).get("displayName"),
                "author_id": comment.get("author", {}).get("accountId"),
                "body": _extract_text_from_adf(comment.get("body")),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
            })

        return comments

    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Get full details of a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get issue details
    python -m src.tools.jira.get_issue ECD-123

    # Get issue with comments
    python -m src.tools.jira.get_issue ECD-123 --include-comments

    # Get specific fields only
    python -m src.tools.jira.get_issue ECD-123 --fields summary,status,assignee
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("--fields", help="Comma-separated list of fields")
    parser.add_argument("--include-comments", action="store_true", help="Include comments")

    args = parser.parse_args()

    fields = args.fields.split(",") if args.fields else None

    try:
        result = get_jira_issue(
            args.issue_key,
            fields=fields,
            include_comments=args.include_comments
        )
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
