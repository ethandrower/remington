#!/usr/bin/env python3
"""Quick script to check Jira tickets and associated PRs"""
import os
import sys
import requests
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from bitbucket_cli.api import BitbucketAPI
from bitbucket_cli.auth import load_config as load_bb_config

# Jira config
JIRA_BASE = "https://citemed.atlassian.net"
JIRA_TOKEN = os.getenv("ATLASSIAN_OAUTH_ACCESS_TOKEN")
CLOUD_ID = "67bbfd03-b309-414f-9640-908213f80628"

def get_jira_issue(issue_key):
    """Get Jira issue details"""
    headers = {
        "Authorization": f"Bearer {JIRA_TOKEN}",
        "Accept": "application/json"
    }

    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {issue_key}: {response.status_code}")
        return None

def search_prs_for_ticket(issue_key):
    """Search Bitbucket PRs mentioning this ticket"""
    bb_config = load_bb_config()
    bb_api = BitbucketAPI(bb_config)
    workspace = "citemed"
    repo = "citemed_web"

    try:
        # Get all PRs (open and merged)
        prs_open = bb_api.list_pull_requests(workspace, repo, state="OPEN")
        prs_merged = bb_api.list_pull_requests(workspace, repo, state="MERGED")

        all_prs = prs_open + prs_merged

        matching_prs = []
        for pr in all_prs:
            title = pr.get("title", "").upper()
            branch = pr.get("source", {}).get("branch", {}).get("name", "").upper()

            if issue_key.upper() in title or issue_key.upper() in branch:
                matching_prs.append({
                    "id": pr["id"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "branch": pr["source"]["branch"]["name"],
                    "link": pr["links"]["html"]["href"],
                    "author": pr["author"]["display_name"]
                })

        return matching_prs
    except Exception as e:
        print(f"Error searching PRs: {e}")
        return []

def main():
    tickets = ["ECD-351", "ECD-347"]

    print("=" * 80)
    print("TICKET ANALYSIS")
    print("=" * 80)

    for ticket_key in tickets:
        print(f"\n📋 {ticket_key}")
        print("-" * 80)

        # Get Jira details
        issue = get_jira_issue(ticket_key)
        if issue:
            fields = issue.get("fields", {})

            print(f"Summary: {fields.get('summary', 'N/A')}")
            print(f"Status: {fields.get('status', {}).get('name', 'N/A')}")
            print(f"Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}")

            # Sprint
            sprints = fields.get("customfield_10020", [])  # Sprint field
            if sprints:
                sprint_name = sprints[-1].split("name=")[1].split(",")[0] if "name=" in sprints[-1] else "Unknown"
                print(f"Sprint: {sprint_name}")
            else:
                print("Sprint: Not assigned")

            # Fix version
            fix_versions = fields.get("fixVersions", [])
            if fix_versions:
                print(f"Fix Version: {', '.join([v['name'] for v in fix_versions])}")
            else:
                print("Fix Version: None")

            # Story points
            story_points = fields.get("customfield_10016")  # Story points field
            print(f"Story Points: {story_points if story_points else 'None'}")

            # Epic link
            epic_link = fields.get("customfield_10014")  # Epic link field
            if epic_link:
                print(f"Epic: {epic_link}")

            # Links
            issue_links = fields.get("issuelinks", [])
            if issue_links:
                print(f"Linked Issues: {len(issue_links)}")
                for link in issue_links[:3]:
                    if "inwardIssue" in link:
                        linked = link["inwardIssue"]
                        print(f"  - {linked['key']}: {linked['fields']['summary'][:50]}...")
                    elif "outwardIssue" in link:
                        linked = link["outwardIssue"]
                        print(f"  - {linked['key']}: {linked['fields']['summary'][:50]}...")

        # Search for PRs
        print("\n🔀 Associated PRs:")
        prs = search_prs_for_ticket(ticket_key)
        if prs:
            for pr in prs:
                print(f"  PR-{pr['id']} [{pr['state']}]: {pr['title']}")
                print(f"    Branch: {pr['branch']}")
                print(f"    Author: {pr['author']}")
                print(f"    Link: {pr['link']}")
        else:
            print("  No PRs found")

        print()

    print("=" * 80)
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 80)
    print("Based on the analysis above, determine if:")
    print("1. These tickets should be combined into a single epic")
    print("2. They need to be moved to next sprint (v5.5.5)")
    print("3. Any PRs need to be updated or closed")
    print("4. Story points need adjustment")

if __name__ == "__main__":
    main()
