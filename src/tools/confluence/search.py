#!/usr/bin/env python3
"""
Confluence Search Tool - Search pages using CQL

Mirrors: mcp__atlassian__searchConfluenceUsingCql

Usage:
    python -m src.tools.confluence.search "title ~ 'Release Notes'"
    python -m src.tools.confluence.search "space = ECD AND type = page" --limit 20
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_confluence_auth_headers, CONFLUENCE_BASE_URL, format_error


def search_confluence(
    cql: str,
    limit: int = 25,
    start: int = 0,
    expand: Optional[list] = None
) -> dict:
    """
    Search Confluence using CQL (Confluence Query Language)

    Args:
        cql: CQL query string (e.g., "title ~ 'Release Notes' AND space = ECD")
        limit: Maximum results to return (default 25, max 250)
        start: Starting index for pagination
        expand: List of properties to expand (e.g., ["body.storage", "version"])

    Returns:
        dict: {
            "total": int,
            "count": int,
            "results": [
                {
                    "id": "217088023",
                    "title": "Customer Release Notes...",
                    "space_key": "ECD",
                    "type": "page",
                    "url": "https://...",
                    "excerpt": "..."
                }
            ]
        }
    """
    try:
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/search"
        params = {
            "cql": cql,
            "limit": min(limit, 250),
            "start": start
        }

        if expand:
            params["expand"] = ",".join(expand)

        response = requests.get(
            url,
            headers=get_confluence_auth_headers(),
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return format_error(response.status_code, response.text)

        data = response.json()

        # Simplify results
        simplified_results = []
        for result in data.get("results", []):
            simplified = {
                "id": result.get("id"),
                "title": result.get("title"),
                "type": result.get("type"),
                "status": result.get("status"),
                "space_key": result.get("space", {}).get("key") if result.get("space") else None,
                "url": result.get("_links", {}).get("webui", "")
            }

            # Add base URL to relative links
            if simplified["url"] and not simplified["url"].startswith("http"):
                simplified["url"] = f"https://citemed.atlassian.net/wiki{simplified['url']}"

            # Include excerpt if available
            if result.get("excerpt"):
                simplified["excerpt"] = result.get("excerpt")

            simplified_results.append(simplified)

        return {
            "total": data.get("totalSize", len(simplified_results)),
            "count": len(simplified_results),
            "results": simplified_results
        }

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def search_pages_by_title(title: str, space_key: Optional[str] = None, limit: int = 10) -> dict:
    """
    Convenience function to search pages by title

    Args:
        title: Title to search for (partial match)
        space_key: Optional space key to limit search
        limit: Maximum results

    Returns:
        dict: Search results
    """
    cql = f'title ~ "{title}" AND type = page'
    if space_key:
        cql += f' AND space = "{space_key}"'

    return search_confluence(cql, limit=limit)


def main():
    parser = argparse.ArgumentParser(
        description="Search Confluence using CQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Search for release notes pages
    python -m src.tools.confluence.search "title ~ 'Release Notes'"

    # Search in specific space
    python -m src.tools.confluence.search "space = ECD AND type = page"

    # Search by label
    python -m src.tools.confluence.search "label = 'release-notes'"

    # Search recently modified
    python -m src.tools.confluence.search "lastModified >= now('-7d')" --limit 20
        """
    )
    parser.add_argument("cql", help="CQL query string")
    parser.add_argument("--limit", type=int, default=25, help="Maximum results (default: 25)")
    parser.add_argument("--start", type=int, default=0, help="Starting index for pagination")

    args = parser.parse_args()

    try:
        result = search_confluence(args.cql, args.limit, args.start)
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
