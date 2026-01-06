#!/usr/bin/env python3
"""
Sync Team Roster from Confluence
Reads team roster from Confluence page and syncs to local JSON file
"""

import os
import sys
import json
import re
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

import requests


def get_confluence_page_content(page_id: str) -> dict:
    """Fetch Confluence page content via API"""
    api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
    email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
    cloud_id = os.getenv("ATLASSIAN_CLOUD_ID")

    if not all([api_token, email, cloud_id]):
        raise ValueError("Missing Atlassian credentials in .env")

    api_token = api_token.strip("'\"")
    email = email.strip("'\"")

    # Confluence API endpoint
    base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }

    # Get page content with body expanded
    url = f"{base_url}/wiki/api/v2/pages/{page_id}?body-format=storage"

    print(f"📖 Fetching Confluence page: {page_id}")
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        print(f"❌ Page not found: {page_id}")
        return None
    elif response.status_code != 200:
        print(f"❌ API error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    print(f"✅ Fetched page: {data.get('title', 'Unknown')}")

    return data


def parse_team_roster_from_html(html_content: str) -> list:
    """
    Parse team roster from Confluence HTML content
    Looks for tables, lists, or structured content with names
    """
    team_members = []

    # Print the HTML for debugging
    print("\n" + "="*60)
    print("CONFLUENCE PAGE CONTENT:")
    print("="*60)
    print(html_content[:2000])  # First 2000 chars
    print("="*60 + "\n")

    # Try to extract team member names
    # Common patterns:
    # - Tables with Name, Email, Role columns
    # - Lists with @mentions
    # - Headings with developer names

    # Pattern 1: Look for @mentions (Confluence user mentions)
    mention_pattern = r'<ri:user[^>]*ri:account-id="([^"]+)"[^>]*>([^<]+)</ri:user>'
    mentions = re.findall(mention_pattern, html_content)

    for account_id, display_name in mentions:
        team_members.append({
            "display_name": display_name.strip(),
            "jira_id": account_id,
        })

    # Pattern 2: Look for table rows
    # This is more complex, would need HTML parsing

    return team_members


def sync_from_confluence(confluence_page_id: str):
    """Main sync function"""
    print("\n🔄 Syncing team roster from Confluence...\n")

    # Fetch page
    page_data = get_confluence_page_content(confluence_page_id)

    if not page_data:
        print("❌ Failed to fetch Confluence page")
        return

    # Get page body
    body = page_data.get("body", {}).get("storage", {}).get("value", "")

    if not body:
        print("❌ No content found in Confluence page")
        return

    # Parse team members
    team_members = parse_team_roster_from_html(body)

    if not team_members:
        print("⚠️  No team members found in page")
        print("   The page might use a different format.")
        print("   Please check the HTML output above to see the structure.\n")
        return

    print(f"\n✅ Found {len(team_members)} team members from Confluence")

    # Now lookup Slack IDs for each
    from scripts.lookup_slack_ids import lookup_slack_users

    # TODO: Merge with existing roster and add Slack IDs

    # For now, just print what we found
    print("\n" + "="*60)
    print("TEAM MEMBERS FROM CONFLUENCE:")
    print("="*60)
    for member in team_members:
        print(f"  - {member['display_name']} (Jira: {member['jira_id']})")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Extract page ID from URL or use directly
    # URL format: https://citemed.atlassian.net/wiki/x/y4HUAQ
    # Page ID: y4HUAQ (the part after /wiki/x/)

    confluence_url = "https://citemed.atlassian.net/wiki/x/y4HUAQ"
    page_id = confluence_url.split("/wiki/x/")[-1] if "/wiki/x/" in confluence_url else confluence_url

    sync_from_confluence(page_id)
