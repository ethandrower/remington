#!/usr/bin/env python3
"""
Release Notes Generator

Generates customer-facing release notes in Confluence from completed Jira issues.

Features:
1. Finds or creates release notes page for current version
2. Gets completed issues from current sprint or recent completions
3. Adds marketing-style writeups for new features
4. Runs as daily reconciliation or on-demand

Usage:
    python scripts/generate_release_notes.py
    python scripts/generate_release_notes.py --version 5.5.6
    python scripts/generate_release_notes.py --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.confluence.search import search_confluence
from src.tools.confluence.get_page import get_confluence_page
from src.tools.confluence.create_page import create_confluence_page
from src.tools.confluence.update_page import update_confluence_page, add_feature_to_release_notes
from src.tools.jira.get_release_issues import get_release_issues, get_current_sprint_completed

# Configuration
RELEASE_NOTES_PARENT_ID = "125566979"  # "Customer Release Notes" parent page in ECD space
RELEASE_NOTES_SPACE = "ECD"  # Evidence Cloud Documentation space
ENGINEERING_SPACE = "Engineerin"  # Engineering space for drafts
ENGINEERING_RELEASE_OPS_PARENT_ID = "258048005"  # "Release Ops" parent in Engineering space


def get_current_version() -> str:
    """
    Determine current version from Jira fix versions or default

    Returns:
        str: Version string like "5.5.6"
    """
    # Try to find most common fix version in recent completed issues
    issues = get_release_issues(days=14)

    if issues.get("error"):
        return "5.5.6"  # Default fallback

    version_counts = {}
    for issue in issues.get("issues", []):
        for v in issue.get("fix_versions", []):
            if v.startswith("v"):
                v = v[1:]  # Remove 'v' prefix
            version_counts[v] = version_counts.get(v, 0) + 1

    if version_counts:
        # Return most common version
        return max(version_counts, key=version_counts.get)

    return "5.5.6"  # Default


def find_release_notes_page(version: str, space: str = RELEASE_NOTES_SPACE) -> Optional[Dict]:
    """
    Find existing release notes page for a version

    Args:
        version: Version string (e.g., "5.5.6")
        space: Confluence space key

    Returns:
        dict: Page info or None if not found
    """
    # Search for page with version in title
    cql = f'title ~ "Release Notes" AND title ~ "{version}" AND space = "{space}" AND type = page'

    result = search_confluence(cql, limit=5)

    if result.get("error"):
        print(f"Error searching for release notes: {result.get('message')}")
        return None

    # Find exact match
    for page in result.get("results", []):
        if version in page.get("title", ""):
            # Get full page content
            return get_confluence_page(page["id"])

    return None


def create_release_notes_page(version: str, space: str = RELEASE_NOTES_SPACE) -> Dict:
    """
    Create a new release notes page

    Args:
        version: Version string
        space: Confluence space key

    Returns:
        dict: Created page info
    """
    title = f"Customer Release Notes – Evidence Cloud v{version}"

    initial_content = f"""
<h2>Overview</h2>
<p>Evidence Cloud <strong>v{version}</strong> brings new features and improvements to enhance your research workflow.</p>

<h2>What's New</h2>
<p><em>This section will be updated as features are completed.</em></p>

<h2>Features by Module</h2>
<table>
<colgroup>
<col style="width: 15%;" />
<col style="width: 25%;" />
<col style="width: 45%;" />
<col style="width: 15%;" />
</colgroup>
<thead>
<tr>
<th>Module</th>
<th>Feature</th>
<th>Description</th>
<th>Reference</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

<h2>Bug Fixes</h2>
<p><em>Bug fixes will be documented here.</em></p>

<h2>Known Issues</h2>
<p>No known issues at this time.</p>

<hr />
<p><em>Last updated: {datetime.now().strftime('%B %d, %Y')}</em></p>
"""

    # Use correct parent ID based on space
    parent_id = ENGINEERING_RELEASE_OPS_PARENT_ID if space == ENGINEERING_SPACE else RELEASE_NOTES_PARENT_ID

    result = create_confluence_page(
        title=title,
        body=initial_content,
        space_key=space,
        parent_id=parent_id
    )

    return result


def generate_feature_writeup(issue: Dict) -> str:
    """
    Generate marketing-style feature writeup from Jira issue

    Args:
        issue: Issue data from Jira

    Returns:
        str: Marketing-style HTML writeup
    """
    summary = issue.get("summary", "")
    description = issue.get("description", "")
    issue_type = issue.get("type", "Feature")
    key = issue.get("key", "")

    # Determine benefit/value proposition
    if issue_type == "Bug":
        # Bug fixes are about reliability
        benefit = "improves system stability and reliability"
        intro = "We've resolved an issue that"
    elif "performance" in summary.lower() or "fast" in summary.lower():
        benefit = "saves you time and improves your workflow efficiency"
        intro = "This enhancement"
    elif "ui" in summary.lower() or "design" in summary.lower() or "ux" in summary.lower():
        benefit = "makes the interface more intuitive and user-friendly"
        intro = "This update"
    elif "export" in summary.lower() or "pdf" in summary.lower():
        benefit = "gives you more flexibility in how you share and present your work"
        intro = "This feature"
    elif "search" in summary.lower() or "filter" in summary.lower():
        benefit = "helps you find exactly what you need, faster"
        intro = "This enhancement"
    else:
        benefit = "enhances your Evidence Cloud experience"
        intro = "This feature"

    # Build the writeup
    writeup = f"""
<h3>{summary}</h3>
<p><strong>Reference:</strong> <a href="https://citemed.atlassian.net/browse/{key}">{key}</a></p>
<p>{intro} {benefit}.</p>
"""

    # Add description excerpt if available
    if description and len(description) > 50:
        # Clean up description for customer view
        clean_desc = description[:300]
        if len(description) > 300:
            clean_desc += "..."
        writeup += f"<p><em>{clean_desc}</em></p>\n"

    return writeup


def generate_table_row(issue: Dict, module: str = "General") -> str:
    """
    Generate table row HTML for feature

    Args:
        issue: Issue data
        module: Module/area name

    Returns:
        str: Table row HTML
    """
    summary = issue.get("summary", "")
    description = issue.get("description", "")[:100] if issue.get("description") else ""
    key = issue.get("key", "")

    return f"""<tr>
<td>{module}</td>
<td>{summary}</td>
<td>{description}{'...' if len(issue.get('description', '')) > 100 else ''}</td>
<td><a href="https://citemed.atlassian.net/browse/{key}">{key}</a></td>
</tr>"""


def determine_module(issue: Dict) -> str:
    """
    Determine which module/area an issue belongs to

    Args:
        issue: Issue data

    Returns:
        str: Module name
    """
    summary = issue.get("summary", "").lower()
    labels = [l.lower() for l in issue.get("labels", [])]

    if any(x in summary for x in ["search", "filter", "query"]):
        return "Search & Discovery"
    elif any(x in summary for x in ["export", "pdf", "download"]):
        return "Export & Reporting"
    elif any(x in summary for x in ["extract", "ai", "nlp", "llm"]):
        return "AI Extraction"
    elif any(x in summary for x in ["admin", "user", "permission"]):
        return "Administration"
    elif any(x in summary for x in ["ui", "ux", "design", "sidebar", "menu"]):
        return "User Interface"
    elif any(x in summary for x in ["api", "backend", "database"]):
        return "Platform"
    else:
        return "General"


def reconcile_release_notes(
    version: Optional[str] = None,
    space: str = RELEASE_NOTES_SPACE,
    dry_run: bool = False
) -> Dict:
    """
    Main reconciliation function - finds/creates page and adds missing issues

    Args:
        version: Version string (auto-detected if not provided)
        space: Confluence space key
        dry_run: If True, don't actually make changes

    Returns:
        dict: Summary of actions taken
    """
    results = {
        "version": None,
        "page_created": False,
        "page_id": None,
        "issues_checked": 0,
        "issues_added": 0,
        "issues_skipped": 0,
        "errors": []
    }

    # Determine version
    if not version:
        version = get_current_version()
    results["version"] = version

    print(f"Reconciling release notes for version {version}...")

    # Find or create release notes page
    page = find_release_notes_page(version, space)

    if page and not page.get("error"):
        print(f"Found existing release notes page: {page.get('title')}")
        results["page_id"] = page.get("id")
    else:
        print(f"Creating new release notes page for v{version}...")
        if not dry_run:
            page = create_release_notes_page(version, space)
            if page.get("error"):
                results["errors"].append(f"Failed to create page: {page.get('message')}")
                return results
            results["page_created"] = True
            results["page_id"] = page.get("id")
            print(f"Created page: {page.get('url')}")
        else:
            print("[DRY RUN] Would create release notes page")
            return results

    # Get completed issues
    print("Fetching completed issues...")
    issues_result = get_release_issues(days=30)

    if issues_result.get("error"):
        results["errors"].append(f"Failed to fetch issues: {issues_result.get('message')}")
        return results

    issues = issues_result.get("issues", [])
    results["issues_checked"] = len(issues)
    print(f"Found {len(issues)} completed issues")

    # Get current page content
    current_page = get_confluence_page(results["page_id"])
    current_body = current_page.get("body", "")

    # Check each issue
    for issue in issues:
        key = issue.get("key")

        # Skip if already in page
        if key in current_body:
            print(f"  Skipping {key} - already in release notes")
            results["issues_skipped"] += 1
            continue

        # Add to release notes
        print(f"  Adding {key}: {issue.get('summary')[:50]}...")

        if not dry_run:
            module = determine_module(issue)
            add_result = add_feature_to_release_notes(
                page_id=results["page_id"],
                jira_key=key,
                feature_title=issue.get("summary"),
                description=generate_feature_writeup(issue),
                module=module
            )

            if add_result.get("error"):
                results["errors"].append(f"Failed to add {key}: {add_result.get('message')}")
            elif add_result.get("skipped"):
                results["issues_skipped"] += 1
            else:
                results["issues_added"] += 1
                # Refresh current body to avoid duplicates
                current_body += key
        else:
            print(f"  [DRY RUN] Would add {key}")
            results["issues_added"] += 1

    print(f"\nReconciliation complete:")
    print(f"  - Checked: {results['issues_checked']} issues")
    print(f"  - Added: {results['issues_added']} new entries")
    print(f"  - Skipped: {results['issues_skipped']} (already present)")
    if results["errors"]:
        print(f"  - Errors: {len(results['errors'])}")
        for err in results["errors"]:
            print(f"    - {err}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate customer-facing release notes from Jira issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Auto-detect version and reconcile
    python scripts/generate_release_notes.py

    # Specify version
    python scripts/generate_release_notes.py --version 5.5.6

    # Dry run (no changes)
    python scripts/generate_release_notes.py --dry-run

    # Use Engineering space for drafts
    python scripts/generate_release_notes.py --space Engineerin
        """
    )
    parser.add_argument("--version", help="Version string (e.g., 5.5.6)")
    parser.add_argument("--space", default=RELEASE_NOTES_SPACE, help="Confluence space key")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, just report")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    result = reconcile_release_notes(
        version=args.version,
        space=args.space,
        dry_run=args.dry_run
    )

    if args.json:
        print(json.dumps(result, indent=2))

    sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
