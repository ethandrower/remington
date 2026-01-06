#!/usr/bin/env python3
"""
Lookup Slack User IDs - Fetch Slack user IDs for team members
Run this once to populate team roster with Slack IDs
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

import requests
from src.team_roster import TEAM_ROSTER


def lookup_slack_users():
    """Look up Slack user IDs by display name"""
    slack_token = os.getenv("SLACK_BOT_TOKEN")

    if not slack_token:
        print("❌ SLACK_BOT_TOKEN not found in .env")
        return

    slack_token = slack_token.strip("'\"")

    print("\n🔍 Looking up Slack user IDs...\n")

    try:
        # Get all users from Slack
        headers = {"Authorization": f"Bearer {slack_token}"}
        response = requests.get(
            "https://slack.com/api/users.list",
            headers=headers,
            timeout=10
        )

        result = response.json()

        if not result.get("ok"):
            print(f"❌ Slack API error: {result.get('error')}")
            return

        slack_users = result.get("members", [])
        print(f"✅ Found {len(slack_users)} Slack users\n")

        # Match team members
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("TEAM MEMBER SLACK ID LOOKUP")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        env_vars = []

        for name, member in TEAM_ROSTER.items():
            display_name = member["display_name"]

            # Try to find match by display name or real name
            matched_user = None
            for slack_user in slack_users:
                if slack_user.get("deleted") or slack_user.get("is_bot"):
                    continue

                profile = slack_user.get("profile", {})
                real_name = profile.get("real_name", "").lower()
                display_name_slack = profile.get("display_name", "").lower()

                if (display_name.lower() in real_name or
                    display_name.lower() in display_name_slack or
                    real_name in display_name.lower()):
                    matched_user = slack_user
                    break

            if matched_user:
                slack_id = matched_user["id"]
                slack_name = matched_user.get("profile", {}).get("real_name", "")

                print(f"✅ {name} ({display_name})")
                print(f"   Slack: {slack_name}")
                print(f"   ID: {slack_id}")
                print(f"   Jira ID: {member['jira_id']}\n")

                env_vars.append(f"DEVELOPER_{name.upper()}_SLACK={slack_id}")
            else:
                print(f"❌ {name} ({display_name}) - NOT FOUND")
                print(f"   Jira ID: {member['jira_id']}\n")

        # Print .env variables to add
        if env_vars:
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("ADD THESE LINES TO YOUR .env FILE:")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            for var in env_vars:
                print(var)
            print("\n")

    except Exception as e:
        print(f"❌ Error looking up Slack users: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    lookup_slack_users()
