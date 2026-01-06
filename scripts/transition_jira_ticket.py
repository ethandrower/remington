#!/usr/bin/env python3
"""
Transition Jira Ticket - Simple script to change Jira ticket status
Usage: python scripts/transition_jira_ticket.py <TICKET_KEY> <TARGET_STATUS>
Example: python scripts/transition_jira_ticket.py ECD-123 "Done"
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use Atlassian OAuth token (same as MCP tools and comment script)
ATLASSIAN_TOKEN = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
ATLASSIAN_CLOUD_ID = os.getenv("ATLASSIAN_CLOUD_ID", "67bbfd03-b309-414f-9640-908213f80628")
JIRA_URL = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"


def get_available_transitions(ticket_key):
    """Get all available transitions for a ticket"""
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_key}/transitions"

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {ATLASSIAN_TOKEN}",
            "Accept": "application/json"
        }
    )

    if response.status_code != 200:
        raise Exception(f"Failed to get transitions: {response.text}")

    return response.json()["transitions"]


def transition_ticket(ticket_key, target_status):
    """Transition a ticket to the target status"""
    # Get available transitions
    transitions = get_available_transitions(ticket_key)

    # Find the transition that matches the target status (case-insensitive)
    target_transition = None
    for transition in transitions:
        if transition["to"]["name"].lower() == target_status.lower():
            target_transition = transition
            break

    if not target_transition:
        available = [t["to"]["name"] for t in transitions]
        raise Exception(
            f"Status '{target_status}' not available for {ticket_key}. "
            f"Available statuses: {', '.join(available)}"
        )

    # Execute the transition
    url = f"{JIRA_URL}/rest/api/3/issue/{ticket_key}/transitions"
    payload = {
        "transition": {
            "id": target_transition["id"]
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {ATLASSIAN_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    )

    if response.status_code not in [200, 204]:
        raise Exception(f"Failed to transition ticket: {response.text}")

    return {
        "success": True,
        "ticket": ticket_key,
        "from_status": target_transition["to"]["name"],  # API doesn't return old status easily
        "to_status": target_transition["to"]["name"],
        "transition_id": target_transition["id"]
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python transition_jira_ticket.py <TICKET_KEY> <TARGET_STATUS>")
        print('Example: python transition_jira_ticket.py ECD-123 "Done"')
        sys.exit(1)

    ticket_key = sys.argv[1]
    target_status = sys.argv[2]

    # Check credentials
    if not ATLASSIAN_TOKEN:
        print("ERROR: ATLASSIAN_SERVICE_ACCOUNT_TOKEN must be set in .env file")
        sys.exit(1)

    try:
        print(f"Transitioning {ticket_key} to '{target_status}'...")
        result = transition_ticket(ticket_key, target_status)
        print(f"✅ Success! {ticket_key} transitioned to '{result['to_status']}'")
        print(f"   Transition ID: {result['transition_id']}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
