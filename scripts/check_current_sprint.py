#!/usr/bin/env python3
"""Check current sprint tickets"""
import os
import requests

JIRA_TOKEN = os.getenv("ATLASSIAN_OAUTH_ACCESS_TOKEN")
CLOUD_ID = "67bbfd03-b309-414f-9640-908213f80628"

def search_jql(jql):
    """Search Jira using JQL"""
    headers = {
        "Authorization": f"Bearer {JIRA_TOKEN}",
        "Accept": "application/json"
    }

    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql"
    params = {
        "jql": jql,
        "fields": "summary,status,assignee,fixVersions",
        "maxResults": 100
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Search error: {response.status_code}")
        print(response.text)
        return None

print("🔍 Searching for tickets in current sprint...")
result = search_jql("project = ECD AND sprint in openSprints() ORDER BY key DESC")

if result:
    issues = result.get("issues", [])
    print(f"\n✅ Found {len(issues)} tickets in current sprint\n")

    # Show highest numbered tickets
    print("📋 Recent tickets (highest numbers):")
    for issue in issues[:20]:
        fields = issue["fields"]
        status = fields['status']['name']
        assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
        fix_version = ', '.join([v['name'] for v in fields.get('fixVersions', [])]) if fields.get('fixVersions') else 'None'

        print(f"\n  {issue['key']}: {fields['summary'][:60]}")
        print(f"    Status: {status} | Assignee: {assignee} | Fix: {fix_version}")

    # Check for tickets in weird states
    print("\n\n⚠️  Checking for tickets in non-standard states...")
    weird_states = ["In Progress", "To Do", "Blocked"]
    for state in weird_states:
        state_result = search_jql(f"project = ECD AND sprint in openSprints() AND status = '{state}' ORDER BY key DESC")
        if state_result:
            state_issues = state_result.get("issues", [])
            if state_issues:
                print(f"\n📌 {len(state_issues)} tickets in '{state}':")
                for issue in state_issues[:10]:
                    fields = issue["fields"]
                    assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
                    print(f"  {issue['key']}: {fields['summary'][:50]} ({assignee})")

print("\n\n💡 Did you mean different ticket numbers?")
