#!/usr/bin/env python3
"""
Team Roster - Centralized mapping of team members across platforms.

Primary source: team_members table in DashboardDB (managed via the web UI).
Fallback:       team_roster.json (legacy, for environments without a DB).

Provides lookup functions used by the SLA check and blocked ticket analyzer
to resolve Jira assignee display names → Slack mention tags (<@UXXXXXXX>).
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_from_db() -> Dict:
    """
    Load active team members from DashboardDB.

    Returns a dict keyed by display_name, each value containing:
        jira_id, slack_id, display_name, jira_display_name,
        slack_display_name, email, role
    Returns {} on any error (DB not configured, table empty, etc.)
    """
    try:
        from src.database.dashboard_db import get_dashboard_db
        members = get_dashboard_db().get_team_members(active_only=True)
        roster = {}
        for m in members:
            name = m["display_name"]
            roster[name] = {
                "jira_id":            m.get("jira_account_id") or "",
                "slack_id":           m.get("slack_user_id") or "",
                "display_name":       m.get("display_name", name),
                "jira_display_name":  m.get("jira_display_name") or "",
                "slack_display_name": m.get("slack_display_name") or "",
                "email":              m.get("email") or "",
                "role":               m.get("role") or "",
            }
        return roster
    except Exception as e:
        print(f"⚠️  team_roster: could not load from DB: {e}")
        return {}


def load_from_json() -> Dict:
    """Load team roster from legacy team_roster.json (fallback only)."""
    roster_file = Path(__file__).parent.parent / "team_roster.json"
    if not roster_file.exists():
        return {}
    try:
        with open(roster_file) as f:
            data = json.load(f)
        roster = {}
        for member in data.get("team_members", []):
            member = dict(member)
            name = member.pop("name")
            roster[name] = member
        return roster
    except Exception as e:
        print(f"⚠️  team_roster: could not load from JSON: {e}")
        return {}


def load_team_roster() -> Dict:
    """
    Load team roster from DB (primary) or JSON file (fallback).
    DB takes precedence when it contains at least one member.
    """
    db_roster = load_from_db()
    if db_roster:
        return db_roster

    json_roster = load_from_json()
    if json_roster:
        return json_roster

    print("⚠️  team_roster: no members found in DB or team_roster.json — "
          "Slack mentions will fall back to plain text")
    return {}


# Module-level roster loaded at import time
TEAM_ROSTER = load_team_roster()


def refresh_from_db():
    """
    Reload TEAM_ROSTER from the DB.
    Call this in long-running processes after adding new members via the UI.
    """
    global TEAM_ROSTER
    TEAM_ROSTER = load_team_roster()


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _name_matches(member_name: str, member: Dict, query: str) -> bool:
    """
    Return True if query matches any of the name fields for this member
    (case-insensitive). Checks: dict key, display_name, jira_display_name,
    slack_display_name — because Jira often returns lowercase or abbreviated names.
    """
    q = query.lower()
    return (
        member_name.lower() == q
        or member.get("display_name", "").lower() == q
        or member.get("jira_display_name", "").lower() == q
        or member.get("slack_display_name", "").lower() == q
    )


def get_team_member_by_jira_id(jira_id: str) -> Optional[Dict]:
    """Look up a team member by their Jira account ID."""
    for name, member in TEAM_ROSTER.items():
        if member.get("jira_id") == jira_id:
            return {"name": name, **member}
    return None


def get_team_member_by_slack_id(slack_id: str) -> Optional[Dict]:
    """Look up a team member by their Slack user ID."""
    for name, member in TEAM_ROSTER.items():
        if member.get("slack_id") == slack_id:
            return {"name": name, **member}
    return None


def get_team_member_by_name(name: str) -> Optional[Dict]:
    """
    Look up a team member by any name variant (case-insensitive).
    Matches against display_name, jira_display_name, and slack_display_name.
    """
    for member_name, member in TEAM_ROSTER.items():
        if _name_matches(member_name, member, name):
            return {"name": member_name, **member}
    return None


def get_slack_mention(jira_id: str) -> Optional[str]:
    """
    Get a Slack mention tag (<@UXXXXXXX>) for a team member by Jira account ID.
    Returns None if not found or Slack ID not set.
    """
    member = get_team_member_by_jira_id(jira_id)
    if member and member.get("slack_id"):
        return f"<@{member['slack_id']}>"
    return None


def get_slack_mention_by_name(name: str) -> Optional[str]:
    """
    Get a Slack mention tag (<@UXXXXXXX>) for a team member by any name variant.
    Returns None if not found or Slack ID not set.
    """
    member = get_team_member_by_name(name)
    if member and member.get("slack_id"):
        return f"<@{member['slack_id']}>"
    return None


def get_jira_mention(jira_id: str) -> dict:
    """
    Build a Jira ADF mention node for a team member.
    Falls back to a plain-text node if the member isn't in the roster.
    """
    member = get_team_member_by_jira_id(jira_id)
    display = member["display_name"] if member else jira_id
    if member:
        return {"type": "mention", "attrs": {"id": jira_id, "text": f"@{display}"}}
    return {"type": "text", "text": f"@{display}"}


def get_all_team_members() -> Dict:
    """Return the full roster dict."""
    return TEAM_ROSTER


# ---------------------------------------------------------------------------
# Legacy env-var loader (kept for backward compatibility)
# ---------------------------------------------------------------------------

def load_slack_ids_from_env():
    """
    Override Slack IDs from DEVELOPER_{NAME}_SLACK env vars.
    Runs automatically on import so env-var-only setups still work.
    """
    for name in TEAM_ROSTER.keys():
        env_var = f"DEVELOPER_{name.upper()}_SLACK"
        slack_id = os.getenv(env_var)
        if slack_id:
            TEAM_ROSTER[name]["slack_id"] = slack_id.strip("'\"")


# Auto-apply env overrides on import
load_slack_ids_from_env()
