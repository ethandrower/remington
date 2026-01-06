#!/usr/bin/env python3
"""
Jira List Projects Tool - Get visible Jira projects

Mirrors: mcp__atlassian__getVisibleJiraProjects

Usage:
    python -m src.tools.jira.list_projects
    python -m src.tools.jira.list_projects --search "ECD"
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def list_jira_projects(
    search: Optional[str] = None,
    max_results: int = 50
) -> dict:
    """
    Get list of visible Jira projects

    Args:
        search: Optional search string to filter projects
        max_results: Maximum number of results (default 50)

    Returns:
        dict: {
            "count": 2,
            "projects": [
                {
                    "key": "ECD",
                    "name": "Evidence Cloud Development",
                    "id": "10000",
                    "project_type": "software"
                }
            ]
        }
    """
    params = {
        "maxResults": max_results,
        "expand": "description"
    }

    if search:
        params["query"] = search

    try:
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/project/search",
            headers=get_jira_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        projects = []
        for project in data.get("values", []):
            projects.append({
                "key": project.get("key"),
                "name": project.get("name"),
                "id": project.get("id"),
                "project_type": project.get("projectTypeKey"),
                "description": project.get("description"),
                "lead": project.get("lead", {}).get("displayName") if project.get("lead") else None,
            })

        return {
            "count": len(projects),
            "total": data.get("total", len(projects)),
            "projects": projects
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="List visible Jira projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List all projects
    python -m src.tools.jira.list_projects

    # Search for specific project
    python -m src.tools.jira.list_projects --search "ECD"
    python -m src.tools.jira.list_projects --search "Evidence"
        """
    )
    parser.add_argument("--search", help="Filter projects by name/key")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum results (default: 50)")

    args = parser.parse_args()

    try:
        result = list_jira_projects(args.search, args.max_results)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
