#!/usr/bin/env python3
"""
Confluence Get Page Tool - Retrieve page content by ID

Mirrors: mcp__atlassian__getConfluencePage

Usage:
    python -m src.tools.confluence.get_page 217088023
    python -m src.tools.confluence.get_page 217088023 --format adf
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_confluence_auth_headers, CONFLUENCE_BASE_URL, format_error


def get_confluence_page(
    page_id: str,
    content_format: str = "storage",
    include_version: bool = True
) -> dict:
    """
    Get a Confluence page by ID

    Args:
        page_id: The numeric page ID
        content_format: Format for body content - "storage" (HTML), "view", or "export_view"
        include_version: Include version info (needed for updates)

    Returns:
        dict: {
            "id": "217088023",
            "title": "Customer Release Notes – Evidence Cloud v5.5.5",
            "space_key": "ECD",
            "space_id": "123456",
            "version": 5,
            "body": "...",  # HTML content
            "url": "https://citemed.atlassian.net/wiki/...",
            "created_at": "2025-01-01T...",
            "updated_at": "2025-01-02T...",
            "created_by": "Name",
            "updated_by": "Name"
        }
    """
    try:
        # Use v1 API which has broader permissions with service account
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
        params = {
            "expand": f"body.{content_format},version,space,history,ancestors"
        }

        response = requests.get(
            url,
            headers=get_confluence_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        # Extract body content
        body_content = ""
        if "body" in data and content_format in data["body"]:
            body_content = data["body"][content_format].get("value", "")

        # Get parent ID from ancestors
        parent_id = None
        if data.get("ancestors"):
            parent_id = data["ancestors"][-1].get("id")

        result = {
            "id": data.get("id"),
            "title": data.get("title"),
            "space_key": data.get("space", {}).get("key"),
            "space_id": data.get("space", {}).get("id"),
            "parent_id": parent_id,
            "version": data.get("version", {}).get("number"),
            "body": body_content,
            "status": data.get("status"),
            "created_at": data.get("history", {}).get("createdDate"),
            "updated_at": data.get("version", {}).get("when"),
            "created_by": data.get("history", {}).get("createdBy", {}).get("displayName"),
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


def main():
    parser = argparse.ArgumentParser(
        description="Get a Confluence page by ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get page in storage format (HTML)
    python -m src.tools.confluence.get_page 217088023

    # Get page in ADF format
    python -m src.tools.confluence.get_page 217088023 --format atlas_doc_format

    # Get page in view format (rendered)
    python -m src.tools.confluence.get_page 217088023 --format view
        """
    )
    parser.add_argument("page_id", help="The numeric page ID")
    parser.add_argument(
        "--format",
        choices=["storage", "atlas_doc_format", "view"],
        default="storage",
        help="Body content format (default: storage)"
    )

    args = parser.parse_args()

    try:
        result = get_confluence_page(args.page_id, args.format)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
