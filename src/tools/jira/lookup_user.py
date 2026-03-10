#!/usr/bin/env python3
"""
Jira Lookup User Tool - Find user account IDs by name or email

Mirrors: mcp__atlassian__lookupJiraAccountId

Usage:
    python -m src.tools.jira.lookup_user "ethan@citemed.com"
    python -m src.tools.jira.lookup_user "Ethan"
    python -m src.tools.jira.lookup_user "Mohamed" --max-results 5
"""

import argparse
import json
import sys

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, format_error


def lookup_jira_user(query: str, max_results: int = 10) -> dict:
    """
    Search for Jira users by name or email

    Args:
        query: Search string (name, email, or account ID)
        max_results: Maximum number of results (default 10)

    Returns:
        dict: {
            "query": "ethan",
            "count": 1,
            "users": [
                {
                    "account_id": "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e",
                    "display_name": "Ethan Drower",
                    "email": "ethan@citemed.com",
                    "active": True
                }
            ]
        }
    """
    try:
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/user/search",
            headers=get_jira_auth_headers(),
            params={
                "query": query,
                "maxResults": max_results
            },
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        users = []
        for user in data:
            users.append({
                "account_id": user.get("accountId"),
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
                "active": user.get("active", True),
                "account_type": user.get("accountType"),
            })

        return {
            "query": query,
            "count": len(users),
            "users": users
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Search for Jira users by name or email",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Search by email
    python -m src.tools.jira.lookup_user "ethan@citemed.com"

    # Search by name
    python -m src.tools.jira.lookup_user "Ethan"

    # Partial match
    python -m src.tools.jira.lookup_user "moh"

The account_id returned can be used for:
- @mentions in comments (add_comment.py)
- Assigning issues (edit_issue.py)
- Filtering by assignee in JQL
        """
    )
    parser.add_argument("query", help="Search string (name or email)")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum results (default: 10)")

    args = parser.parse_args()

    try:
        result = lookup_jira_user(args.query, args.max_results)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
