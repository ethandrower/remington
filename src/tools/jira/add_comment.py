#!/usr/bin/env python3
"""
Jira Add Comment Tool - Post a comment to a Jira issue with @mentions

Mirrors: mcp__atlassian__addCommentToJiraIssue

Usage:
    python -m src.tools.jira.add_comment ECD-123 "Comment text"
    python -m src.tools.jira.add_comment ECD-123 "Hi @Ethan!" --mention "712020:xxx" "Ethan"
    python -m src.tools.jira.add_comment ECD-123 "Hi @A and @B" --mention "id1" "A" --mention "id2" "B"
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_jira_auth_headers, JIRA_BASE_URL, build_adf_comment, format_error


def add_jira_comment(
    issue_key: str,
    comment_text: str,
    mentions: Optional[list] = None,
    visibility: Optional[dict] = None
) -> dict:
    """
    Add a comment to a Jira issue with optional @mentions

    Args:
        issue_key: Issue key (e.g., "ECD-123")
        comment_text: Comment text (use @Name as placeholder for mentions)
        mentions: List of dicts with 'id' (account ID) and 'name' (display name)
                  Example: [{"id": "712020:xxx", "name": "Ethan"}]
        visibility: Optional visibility restriction
                    Example: {"type": "role", "value": "Developers"}

    Returns:
        dict: {
            "success": True,
            "comment_id": "12345",
            "issue_key": "ECD-123",
            "author": "Remington",
            "created": "2025-01-01T..."
        }
    """
    # Build ADF comment body with mentions
    body = build_adf_comment(comment_text, mentions)

    payload = {"body": body}

    if visibility:
        payload["visibility"] = visibility

    try:
        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment",
            headers=get_jira_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code not in [200, 201]:
            return format_error(response.status_code, response.text)

        data = response.json()

        return {
            "success": True,
            "comment_id": data.get("id"),
            "issue_key": issue_key,
            "author": data.get("author", {}).get("displayName"),
            "author_id": data.get("author", {}).get("accountId"),
            "created": data.get("created"),
            "self": data.get("self"),
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Add a comment to a Jira issue with @mentions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Simple comment
    python -m src.tools.jira.add_comment ECD-123 "This looks good!"

    # Comment with single mention
    python -m src.tools.jira.add_comment ECD-123 "Hi @Ethan, please review." \\
        --mention "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e" "Ethan"

    # Comment with multiple mentions
    python -m src.tools.jira.add_comment ECD-123 "Hi @Mohamed and @Ahmed" \\
        --mention "712020:27a3f2fe-9037-455d-9392-fb80ba1705c0" "Mohamed" \\
        --mention "5f1879a11a26ad00147b315c" "Ahmed"

Note: Use --mention with two arguments: account_id and display_name
      The @Name in the text will be replaced with a clickable mention.
        """
    )
    parser.add_argument("issue_key", help="Issue key (e.g., ECD-123)")
    parser.add_argument("comment", help="Comment text (use @Name for mentions)")
    parser.add_argument(
        "--mention", nargs=2, action="append", metavar=("ACCOUNT_ID", "NAME"),
        help="Add mention: --mention account_id display_name"
    )

    args = parser.parse_args()

    # Build mentions list from args
    mentions = None
    if args.mention:
        mentions = [{"id": m[0], "name": m[1]} for m in args.mention]

    try:
        result = add_jira_comment(args.issue_key, args.comment, mentions)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)
        else:
            # Print success message to stderr for visibility
            print(f"Posted comment to {args.issue_key} (ID: {result.get('comment_id')})", file=sys.stderr)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
