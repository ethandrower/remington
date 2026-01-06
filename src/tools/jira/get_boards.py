#!/usr/bin/env python3
"""
Jira Get Boards Tool - List Agile boards

Usage:
    python -m src.tools.jira.get_boards
    python -m src.tools.jira.get_boards --project ECD
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID, format_error

# Agile API uses a different base URL
AGILE_BASE_URL = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}/rest/agile/1.0"


def get_boards(
    project_key: Optional[str] = None,
    board_type: Optional[str] = None,
    max_results: int = 50
) -> dict:
    """
    Get Jira Agile boards

    Args:
        project_key: Filter by project key (e.g., "ECD")
        board_type: Filter by type ("scrum" or "kanban")
        max_results: Maximum results to return

    Returns:
        dict: {
            "total": int,
            "count": int,
            "boards": [
                {
                    "id": 1,
                    "name": "ECD Board",
                    "type": "scrum",
                    "project_key": "ECD"
                }
            ]
        }
    """
    try:
        url = f"{AGILE_BASE_URL}/board"
        params = {
            "maxResults": min(max_results, 100)
        }

        if project_key:
            params["projectKeyOrId"] = project_key

        if board_type:
            params["type"] = board_type

        response = requests.get(
            url,
            headers=get_jira_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        boards = []
        for board in data.get("values", []):
            boards.append({
                "id": board.get("id"),
                "name": board.get("name"),
                "type": board.get("type"),
                "project_key": board.get("location", {}).get("projectKey") if board.get("location") else None
            })

        return {
            "total": data.get("total", len(boards)),
            "count": len(boards),
            "boards": boards
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(description="List Jira Agile boards")
    parser.add_argument("--project", help="Filter by project key")
    parser.add_argument("--type", choices=["scrum", "kanban"], help="Filter by board type")
    parser.add_argument("--max-results", type=int, default=50)

    args = parser.parse_args()

    result = get_boards(args.project, args.type, args.max_results)
    print(json.dumps(result, indent=2))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
