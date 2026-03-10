#!/usr/bin/env python3
"""
Jira Get Sprints Tool - List sprints for a board

Usage:
    python -m src.tools.jira.get_sprints 1
    python -m src.tools.jira.get_sprints 1 --state active
    python -m src.tools.jira.get_sprints 1 --state closed --max-results 5
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, ATLASSIAN_CLOUD_ID, format_error

AGILE_BASE_URL = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}/rest/agile/1.0"


def get_sprints(
    board_id: int,
    state: Optional[str] = None,
    max_results: int = 50
) -> dict:
    """
    Get sprints for a Jira Agile board

    Args:
        board_id: The board ID
        state: Filter by state ("active", "closed", "future")
        max_results: Maximum results to return

    Returns:
        dict: {
            "count": int,
            "sprints": [
                {
                    "id": 1,
                    "name": "Sprint 45",
                    "state": "active",
                    "start_date": "2025-01-01T...",
                    "end_date": "2025-01-14T...",
                    "goal": "Complete feature X"
                }
            ]
        }
    """
    try:
        url = f"{AGILE_BASE_URL}/board/{board_id}/sprint"
        params = {
            "maxResults": min(max_results, 100)
        }

        if state:
            params["state"] = state

        response = requests.get(
            url,
            headers=get_jira_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        sprints = []
        for sprint in data.get("values", []):
            sprints.append({
                "id": sprint.get("id"),
                "name": sprint.get("name"),
                "state": sprint.get("state"),
                "start_date": sprint.get("startDate"),
                "end_date": sprint.get("endDate"),
                "complete_date": sprint.get("completeDate"),
                "goal": sprint.get("goal")
            })

        return {
            "board_id": board_id,
            "count": len(sprints),
            "sprints": sprints
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def get_active_sprint(board_id: int) -> dict:
    """
    Get the currently active sprint for a board

    Args:
        board_id: The board ID

    Returns:
        dict: Sprint details or error
    """
    result = get_sprints(board_id, state="active", max_results=1)

    if result.get("error"):
        return result

    if result.get("sprints"):
        return {
            "found": True,
            "sprint": result["sprints"][0]
        }

    return {
        "found": False,
        "message": "No active sprint found"
    }


def main():
    parser = argparse.ArgumentParser(description="List sprints for a Jira board")
    parser.add_argument("board_id", type=int, help="Board ID")
    parser.add_argument("--state", choices=["active", "closed", "future"], help="Filter by state")
    parser.add_argument("--max-results", type=int, default=50)

    args = parser.parse_args()

    result = get_sprints(args.board_id, args.state, args.max_results)
    print(json.dumps(result, indent=2))

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
