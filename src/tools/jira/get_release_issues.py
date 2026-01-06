#!/usr/bin/env python3
"""
Jira Get Release Issues Tool - Get completed issues for release notes

Uses JQL to find completed issues by:
- Sprint (if specified)
- Fix Version (if specified)
- Recent completions (default: last 14 days)

Usage:
    python -m src.tools.jira.get_release_issues
    python -m src.tools.jira.get_release_issues --fix-version "5.5.6"
    python -m src.tools.jira.get_release_issues --days 7
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Optional, List

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def get_release_issues(
    fix_version: Optional[str] = None,
    sprint_name: Optional[str] = None,
    days: int = 14,
    project: str = "ECD",
    exclude_types: Optional[List[str]] = None,
    max_results: int = 100
) -> dict:
    """
    Get completed issues suitable for release notes

    Args:
        fix_version: Filter by fix version (e.g., "5.5.6")
        sprint_name: Filter by sprint name (e.g., "Sprint 45")
        days: Look back N days for completed issues (default 14)
        project: Project key (default "ECD")
        exclude_types: Issue types to exclude (default: ["Sub-task", "Epic"])
        max_results: Maximum results

    Returns:
        dict: {
            "total": int,
            "count": int,
            "issues": [
                {
                    "key": "ECD-123",
                    "summary": "Feature title",
                    "description": "...",
                    "status": "Complete",
                    "type": "Story",
                    "assignee": "Name",
                    "labels": [],
                    "completed_date": "2025-01-01T..."
                }
            ],
            "by_type": {
                "Story": [...],
                "Bug": [...]
            }
        }
    """
    if exclude_types is None:
        exclude_types = ["Sub-task", "Epic"]

    # Build JQL query
    jql_parts = [
        f"project = {project}",
        "statusCategory = Done"  # Covers "Complete", "Done", etc.
    ]

    if fix_version:
        jql_parts.append(f'fixVersion = "{fix_version}"')
    elif sprint_name:
        jql_parts.append(f'sprint = "{sprint_name}"')
    else:
        # Default: issues completed in last N days
        jql_parts.append(f"status CHANGED TO Complete AFTER -{days}d")

    if exclude_types:
        types_str = ", ".join([f'"{t}"' for t in exclude_types])
        jql_parts.append(f"issuetype NOT IN ({types_str})")

    jql_parts.append("ORDER BY updated DESC")
    jql = " AND ".join(jql_parts[:-1]) + " " + jql_parts[-1]

    try:
        payload = {
            "jql": jql,
            "maxResults": min(max_results, 100),
            "fields": [
                "summary", "description", "status", "issuetype",
                "assignee", "labels", "priority", "updated",
                "fixVersions", "customfield_10016"  # Story points
            ]
        }

        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        issues = []
        by_type = {}

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issue_type = fields.get("issuetype", {}).get("name") if fields.get("issuetype") else "Other"

            # Parse description (can be ADF format)
            description = ""
            if fields.get("description"):
                desc = fields["description"]
                if isinstance(desc, dict):
                    # ADF format - extract text
                    description = extract_text_from_adf(desc)
                else:
                    description = str(desc)

            issue_data = {
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields.get("summary"),
                "description": description[:500] if description else "",
                "status": fields.get("status", {}).get("name") if fields.get("status") else None,
                "type": issue_type,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "story_points": fields.get("customfield_10016"),
                "labels": fields.get("labels", []),
                "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
                "updated": fields.get("updated")
            }

            issues.append(issue_data)

            # Group by type
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue_data)

        return {
            "jql": jql,
            "total": data.get("total", len(issues)),
            "count": len(issues),
            "issues": issues,
            "by_type": by_type
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def extract_text_from_adf(adf: dict) -> str:
    """Extract plain text from Atlassian Document Format"""
    texts = []

    def extract(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                extract(child)
        elif isinstance(node, list):
            for item in node:
                extract(item)

    extract(adf)
    return " ".join(texts)


def get_current_sprint_completed(project: str = "ECD") -> dict:
    """
    Get completed issues from the current active sprint

    Args:
        project: Project key

    Returns:
        dict: Release issues from current sprint
    """
    # First try to find issues in open sprints that are complete
    jql = f"project = {project} AND sprint in openSprints() AND statusCategory = Done ORDER BY updated DESC"

    try:
        payload = {
            "jql": jql,
            "maxResults": 100,
            "fields": [
                "summary", "description", "status", "issuetype",
                "assignee", "labels", "priority", "updated",
                "fixVersions", "customfield_10016"
            ]
        }

        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            # Fall back to recent completions if sprint query fails
            return get_release_issues(days=14, project=project)

        data = response.json()

        if data.get("total", 0) == 0:
            # No completed issues in current sprint, fall back to recent
            return get_release_issues(days=14, project=project)

        # Process issues same as get_release_issues
        issues = []
        by_type = {}

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issue_type = fields.get("issuetype", {}).get("name") if fields.get("issuetype") else "Other"

            # Skip sub-tasks and epics
            if issue_type in ["Sub-task", "Epic"]:
                continue

            description = ""
            if fields.get("description"):
                desc = fields["description"]
                if isinstance(desc, dict):
                    description = extract_text_from_adf(desc)
                else:
                    description = str(desc)

            issue_data = {
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields.get("summary"),
                "description": description[:500] if description else "",
                "status": fields.get("status", {}).get("name") if fields.get("status") else None,
                "type": issue_type,
                "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
                "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                "story_points": fields.get("customfield_10016"),
                "labels": fields.get("labels", []),
                "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
                "updated": fields.get("updated")
            }

            issues.append(issue_data)

            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue_data)

        return {
            "jql": jql,
            "total": len(issues),
            "count": len(issues),
            "issues": issues,
            "by_type": by_type,
            "source": "current_sprint"
        }

    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Get completed Jira issues for release notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get recent completed issues (last 14 days)
    python -m src.tools.jira.get_release_issues

    # Get issues for specific fix version
    python -m src.tools.jira.get_release_issues --fix-version "5.5.6"

    # Get issues completed in last 7 days
    python -m src.tools.jira.get_release_issues --days 7

    # Get from current sprint
    python -m src.tools.jira.get_release_issues --current-sprint
        """
    )
    parser.add_argument("--fix-version", help="Filter by fix version")
    parser.add_argument("--sprint", help="Filter by sprint name")
    parser.add_argument("--days", type=int, default=14, help="Look back N days (default: 14)")
    parser.add_argument("--project", default="ECD", help="Project key (default: ECD)")
    parser.add_argument("--current-sprint", action="store_true", help="Get from current sprint")
    parser.add_argument("--max-results", type=int, default=100)

    args = parser.parse_args()

    if args.current_sprint:
        result = get_current_sprint_completed(args.project)
    else:
        result = get_release_issues(
            fix_version=args.fix_version,
            sprint_name=args.sprint,
            days=args.days,
            project=args.project,
            max_results=args.max_results
        )

    print(json.dumps(result, indent=2))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
