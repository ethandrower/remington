#!/usr/bin/env python3
"""
Team Roster - Centralized mapping of team members across platforms
Maps each team member's IDs across Jira, Slack, Bitbucket, and email

Loads from team_roster.json for easy manual editing
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional


def load_team_roster() -> Dict:
    """Load team roster from JSON file"""
    roster_file = Path(__file__).parent.parent / "team_roster.json"

    if not roster_file.exists():
        print(f"⚠️  Team roster file not found: {roster_file}")
        return {}

    with open(roster_file, 'r') as f:
        data = json.load(f)

    # Convert list to dict keyed by name
    roster = {}
    for member in data.get("team_members", []):
        name = member.pop("name")
        roster[name] = member

    return roster


# Load team roster from JSON file
TEAM_ROSTER = load_team_roster()


def get_team_member_by_jira_id(jira_id: str) -> Optional[Dict]:
    """Look up team member by Jira account ID"""
    for name, member in TEAM_ROSTER.items():
        if member["jira_id"] == jira_id:
            return {"name": name, **member}
    return None


def get_team_member_by_slack_id(slack_id: str) -> Optional[Dict]:
    """Look up team member by Slack user ID"""
    for name, member in TEAM_ROSTER.items():
        if member.get("slack_id") == slack_id:
            return {"name": name, **member}
    return None


def get_team_member_by_name(name: str) -> Optional[Dict]:
    """Look up team member by short name (case-insensitive)"""
    name_lower = name.lower()
    for member_name, member in TEAM_ROSTER.items():
        if member_name.lower() == name_lower:
            return {"name": member_name, **member}
        # Also check display name
        if member["display_name"].lower() == name_lower:
            return {"name": member_name, **member}
    return None


def get_slack_mention(jira_id: str) -> Optional[str]:
    """
    Get Slack mention tag for a team member by their Jira ID
    Returns: <@U12345678> or None if not found
    """
    member = get_team_member_by_jira_id(jira_id)
    if member and member.get("slack_id"):
        return f"<@{member['slack_id']}>"
    return None


def get_slack_mention_by_name(name: str) -> Optional[str]:
    """
    Get Slack mention tag for a team member by their name
    Returns: <@U12345678> or None if not found
    """
    member = get_team_member_by_name(name)
    if member and member.get("slack_id"):
        return f"<@{member['slack_id']}>"
    return None


def get_jira_mention(jira_id: str) -> str:
    """
    Get Jira ADF mention structure for a team member
    Returns: ADF mention dict or plain text if no match
    """
    member = get_team_member_by_jira_id(jira_id)
    if member:
        return {
            "type": "mention",
            "attrs": {
                "id": jira_id,
                "text": f"@{member['display_name']}"
            }
        }
    else:
        # Fallback to plain text
        return {
            "type": "text",
            "text": f"@{jira_id}"
        }


def get_all_team_members() -> Dict:
    """Get all team members"""
    return TEAM_ROSTER


def load_slack_ids_from_env():
    """
    Load Slack IDs from environment variables (if set)
    Useful for quick config without code changes
    """
    for name in TEAM_ROSTER.keys():
        env_var = f"DEVELOPER_{name.upper()}_SLACK"
        slack_id = os.getenv(env_var)
        if slack_id:
            TEAM_ROSTER[name]["slack_id"] = slack_id.strip("'\"")


# Auto-load Slack IDs from env on import
load_slack_ids_from_env()
