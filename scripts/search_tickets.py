#!/usr/bin/env python3
"""Search for tickets using JQL"""
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
        "fields": "summary,status,assignee,customfield_10020,fixVersions,customfield_10016,customfield_10014"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Search error: {response.status_code}")
        print(response.text)
        return None

# Search for tickets
print("Searching for ECD-351 and ECD-347...")
result = search_jql("key in (ECD-351, ECD-347)")

if result:
    issues = result.get("issues", [])
    print(f"\nFound {len(issues)} tickets\n")

    if not issues:
        print("❌ No tickets found with those keys")
        print("\nLet me search for similar numbers...")

        # Try searching in current sprint
        result2 = search_jql("project = ECD AND (key ~ '351' OR key ~ '347') ORDER BY created DESC")
        if result2:
            issues2 = result2.get("issues", [])
            if issues2:
                print(f"\n🔍 Found {len(issues2)} tickets with similar numbers:")
                for issue in issues2[:10]:
                    print(f"  {issue['key']}: {issue['fields']['summary']}")
    else:
        for issue in issues:
            fields = issue["fields"]
            print(f"📋 {issue['key']}: {fields['summary']}")
            print(f"   Status: {fields['status']['name']}")
            print(f"   Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}")
            print()
else:
    print("Failed to search")
