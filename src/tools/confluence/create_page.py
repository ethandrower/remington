#!/usr/bin/env python3
"""
Confluence Create Page Tool - Create new pages

Mirrors: mcp__atlassian__createConfluencePage

Usage:
    python -m src.tools.confluence.create_page "My Page Title" --space-id 123456 --body "<p>Content</p>"
    python -m src.tools.confluence.create_page "Child Page" --parent-id 217088023 --body "<p>Content</p>"
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_confluence_auth_headers, CONFLUENCE_BASE_URL, format_error


def create_confluence_page(
    title: str,
    body: str,
    space_key: str,
    parent_id: Optional[str] = None,
    content_format: str = "storage",
    status: str = "current"
) -> dict:
    """
    Create a new Confluence page

    Args:
        title: Page title
        body: Page content (HTML in storage format)
        space_key: Space key (e.g., "ECD", "Engineerin")
        parent_id: Optional parent page ID for hierarchy
        content_format: "storage" for HTML (default)
        status: "current" for published, "draft" for draft

    Returns:
        dict: {
            "id": "217088024",
            "title": "My Page Title",
            "url": "https://citemed.atlassian.net/wiki/...",
            "version": 1,
            "space_key": "ECD"
        }
    """
    try:
        # Use v1 API which has broader permissions with service account
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content"

        # Build the request body for v1 API
        payload = {
            "type": "page",
            "title": title,
            "space": {
                "key": space_key
            },
            "status": status,
            "body": {
                content_format: {
                    "value": body,
                    "representation": content_format
                }
            }
        }

        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        response = requests.post(
            url,
            headers=get_confluence_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code not in [200, 201]:
            return format_error(response.status_code, response.text)

        data = response.json()

        result = {
            "id": data.get("id"),
            "title": data.get("title"),
            "space_key": data.get("space", {}).get("key"),
            "version": data.get("version", {}).get("number", 1),
            "status": data.get("status"),
            "url": data.get("_links", {}).get("webui", "")
        }

        # Add base URL to relative links
        if result["url"] and not result["url"].startswith("http"):
            result["url"] = f"https://citemed.atlassian.net/wiki{result['url']}"

        return result

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def create_release_notes_page(
    version: str,
    space_key: str,
    parent_id: str,
    initial_content: Optional[str] = None
) -> dict:
    """
    Convenience function to create a customer release notes page

    Args:
        version: Version string (e.g., "v5.5.6")
        space_key: Space key for the page (e.g., "ECD")
        parent_id: Parent page ID (Customer Release Notes parent)
        initial_content: Optional initial HTML content

    Returns:
        dict: Created page info
    """
    title = f"Customer Release Notes – Evidence Cloud {version}"

    if initial_content is None:
        initial_content = f"""
<h2>Overview</h2>
<p>This release includes new features and improvements to Evidence Cloud.</p>

<h2>What's New</h2>
<p><em>Features will be added as they are completed during the sprint.</em></p>

<h2>Details by Module</h2>
<table>
<tr>
<th>Module</th>
<th>Feature</th>
<th>Description</th>
<th>Jira Key</th>
</tr>
</table>

<h2>Known Issues</h2>
<p>None reported.</p>
"""

    return create_confluence_page(
        title=title,
        body=initial_content,
        space_key=space_key,
        parent_id=parent_id,
        content_format="storage"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Create a Confluence page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create a page in a space
    python -m src.tools.confluence.create_page "My Page" --space-id 123456 --body "<p>Hello</p>"

    # Create a child page
    python -m src.tools.confluence.create_page "Child" --space-id 123456 --parent-id 789 --body "<p>Content</p>"

    # Create as draft
    python -m src.tools.confluence.create_page "Draft" --space-id 123456 --body "<p>WIP</p>" --status draft
        """
    )
    parser.add_argument("title", help="Page title")
    parser.add_argument("--space-key", required=True, help="Space key (e.g., ECD)")
    parser.add_argument("--body", required=True, help="Page body content (HTML)")
    parser.add_argument("--parent-id", help="Parent page ID")
    parser.add_argument("--format", choices=["storage"], default="storage")
    parser.add_argument("--status", choices=["current", "draft"], default="current")

    args = parser.parse_args()

    try:
        result = create_confluence_page(
            title=args.title,
            body=args.body,
            space_key=args.space_key,
            parent_id=args.parent_id,
            content_format=args.format,
            status=args.status
        )
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
