#!/usr/bin/env python3
"""
Confluence Update Page Tool - Update existing pages

Mirrors: mcp__atlassian__updateConfluencePage

Usage:
    python -m src.tools.confluence.update_page 217088023 --body "<p>New content</p>" --version 5
    python -m src.tools.confluence.update_page 217088023 --title "New Title" --body "<p>Content</p>"
"""

import argparse
import json
import sys
from typing import Optional

import requests

from ..base import get_confluence_auth_headers, CONFLUENCE_BASE_URL, format_error
from .get_page import get_confluence_page


def update_confluence_page(
    page_id: str,
    body: str,
    title: Optional[str] = None,
    version: Optional[int] = None,
    content_format: str = "storage",
    version_message: Optional[str] = None
) -> dict:
    """
    Update an existing Confluence page

    Args:
        page_id: The numeric page ID
        body: New page content (HTML)
        title: Optional new title (keeps existing if not provided)
        version: Current version number (auto-fetched if not provided)
        content_format: "storage" for HTML (default)
        version_message: Optional message describing the update

    Returns:
        dict: {
            "id": "217088023",
            "title": "Page Title",
            "version": 6,
            "url": "https://..."
        }
    """
    try:
        # If version not provided, fetch current page to get it
        if version is None or title is None:
            current_page = get_confluence_page(page_id)
            if current_page.get("error"):
                return current_page
            if version is None:
                version = current_page.get("version", 1)
            if title is None:
                title = current_page.get("title", "Untitled")

        # Use v1 API which has broader permissions with service account
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"

        payload = {
            "type": "page",
            "title": title,
            "body": {
                content_format: {
                    "value": body,
                    "representation": content_format
                }
            },
            "version": {
                "number": version + 1
            }
        }

        if version_message:
            payload["version"]["message"] = version_message

        response = requests.put(
            url,
            headers=get_confluence_auth_headers(),
            json=payload,
            timeout=30
        )

        if response.status_code not in [200, 204]:
            return format_error(response.status_code, response.text)

        data = response.json()

        result = {
            "id": data.get("id"),
            "title": data.get("title"),
            "version": data.get("version", {}).get("number", version + 1),
            "space_key": data.get("space", {}).get("key"),
            "url": data.get("_links", {}).get("webui", "")
        }

        if result["url"] and not result["url"].startswith("http"):
            result["url"] = f"https://citemed.atlassian.net/wiki{result['url']}"

        return result

    except requests.exceptions.Timeout:
        return format_error(408, "Request timed out")
    except requests.exceptions.RequestException as e:
        return format_error(500, str(e))


def append_to_page(
    page_id: str,
    content_to_append: str,
    section_marker: Optional[str] = None
) -> dict:
    """
    Append content to an existing page, optionally at a specific section

    Args:
        page_id: The numeric page ID
        content_to_append: HTML content to append
        section_marker: Optional HTML marker to insert before (e.g., "<h2>Known Issues</h2>")

    Returns:
        dict: Updated page info
    """
    # Get current page content
    current_page = get_confluence_page(page_id, content_format="storage")
    if current_page.get("error"):
        return current_page

    current_body = current_page.get("body", "")
    current_version = current_page.get("version", 1)
    title = current_page.get("title")

    # Insert content
    if section_marker and section_marker in current_body:
        # Insert before the section marker
        new_body = current_body.replace(
            section_marker,
            f"{content_to_append}\n\n{section_marker}"
        )
    else:
        # Append to end
        new_body = f"{current_body}\n\n{content_to_append}"

    return update_confluence_page(
        page_id=page_id,
        body=new_body,
        title=title,
        version=current_version,
        version_message="Added new content"
    )


def add_feature_to_release_notes(
    page_id: str,
    jira_key: str,
    feature_title: str,
    description: str,
    module: str = "General"
) -> dict:
    """
    Add a feature entry to a release notes page

    Args:
        page_id: Release notes page ID
        jira_key: Jira ticket key (e.g., "ECD-123")
        feature_title: Short feature title
        description: Marketing-style description of the feature
        module: Which module/area the feature belongs to

    Returns:
        dict: Updated page info
    """
    # Get current page
    current_page = get_confluence_page(page_id, content_format="storage")
    if current_page.get("error"):
        return current_page

    current_body = current_page.get("body", "")

    # Check if this Jira key is already in the page
    if jira_key in current_body:
        return {
            "skipped": True,
            "message": f"{jira_key} already exists in the release notes",
            "page_id": page_id
        }

    # Create the feature entry HTML
    feature_html = f"""
<h3>{feature_title}</h3>
<p><strong>Jira:</strong> <a href="https://citemed.atlassian.net/browse/{jira_key}">{jira_key}</a></p>
<p>{description}</p>
"""

    # Also add to the table if it exists
    table_row = f"""<tr>
<td>{module}</td>
<td>{feature_title}</td>
<td>{description[:100]}{'...' if len(description) > 100 else ''}</td>
<td><a href="https://citemed.atlassian.net/browse/{jira_key}">{jira_key}</a></td>
</tr>"""

    # Try to insert into "What's New" section
    if "<h2>What's New</h2>" in current_body:
        # Find the next h2 after "What's New"
        whats_new_idx = current_body.index("<h2>What's New</h2>")
        rest_of_page = current_body[whats_new_idx + len("<h2>What's New</h2>"):]

        # Find next section header
        next_h2 = rest_of_page.find("<h2>")
        if next_h2 != -1:
            insert_point = whats_new_idx + len("<h2>What's New</h2>") + next_h2
            new_body = current_body[:insert_point] + feature_html + "\n" + current_body[insert_point:]
        else:
            new_body = current_body.replace(
                "<h2>What's New</h2>",
                f"<h2>What's New</h2>\n{feature_html}"
            )
    else:
        # Append before Known Issues if exists, otherwise at end
        if "<h2>Known Issues</h2>" in current_body:
            new_body = current_body.replace(
                "<h2>Known Issues</h2>",
                f"{feature_html}\n\n<h2>Known Issues</h2>"
            )
        else:
            new_body = f"{current_body}\n\n{feature_html}"

    # Add table row if table exists
    if "</table>" in new_body:
        new_body = new_body.replace("</table>", f"{table_row}\n</table>")

    return update_confluence_page(
        page_id=page_id,
        body=new_body,
        title=current_page.get("title"),
        version=current_page.get("version"),
        version_message=f"Added feature: {jira_key} - {feature_title}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Update a Confluence page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Update page content
    python -m src.tools.confluence.update_page 217088023 --body "<p>New content</p>"

    # Update with new title
    python -m src.tools.confluence.update_page 217088023 --title "New Title" --body "<p>Content</p>"

    # Update with version message
    python -m src.tools.confluence.update_page 217088023 --body "<p>Content</p>" --message "Fixed typo"
        """
    )
    parser.add_argument("page_id", help="The numeric page ID")
    parser.add_argument("--body", required=True, help="New page body content (HTML)")
    parser.add_argument("--title", help="New page title (optional)")
    parser.add_argument("--version", type=int, help="Current version number (auto-fetched if not provided)")
    parser.add_argument("--format", choices=["storage", "atlas_doc_format"], default="storage")
    parser.add_argument("--message", help="Version message describing the update")

    args = parser.parse_args()

    try:
        result = update_confluence_page(
            page_id=args.page_id,
            body=args.body,
            title=args.title,
            version=args.version,
            content_format=args.format,
            version_message=args.message
        )
        print(json.dumps(result, indent=2))

        if result.get("error"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
