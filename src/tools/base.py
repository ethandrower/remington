"""
Base utilities for Atlassian API tools

Provides authentication headers and configuration for Jira, Confluence, and Bitbucket.
Uses service account credentials that don't expire (unlike OAuth tokens).
"""

import base64
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Atlassian Cloud Configuration
ATLASSIAN_CLOUD_ID = os.getenv("ATLASSIAN_CLOUD_ID", "67bbfd03-b309-414f-9640-908213f80628")

# API Base URLs
JIRA_BASE_URL = f"https://api.atlassian.com/ex/jira/{ATLASSIAN_CLOUD_ID}"
CONFLUENCE_BASE_URL = f"https://api.atlassian.com/ex/confluence/{ATLASSIAN_CLOUD_ID}"
BITBUCKET_BASE_URL = "https://api.bitbucket.org/2.0"

# Bitbucket workspace
BITBUCKET_WORKSPACE = os.getenv("BITBUCKET_WORKSPACE", "citemed")


def get_jira_auth_headers() -> dict:
    """
    Get authentication headers for Jira REST API

    Uses Basic Auth with service account email and API token.
    This is more reliable than OAuth as tokens don't expire.

    Returns:
        dict: Headers with Authorization, Content-Type, Accept

    Raises:
        ValueError: If credentials are missing
    """
    email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
    token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")

    if not email or not token:
        raise ValueError(
            "Missing credentials. Set ATLASSIAN_SERVICE_ACCOUNT_EMAIL and "
            "ATLASSIAN_SERVICE_ACCOUNT_TOKEN environment variables."
        )

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def get_confluence_auth_headers() -> dict:
    """
    Get authentication headers for Confluence REST API

    Uses the same credentials as Jira (Atlassian service account).

    Returns:
        dict: Headers with Authorization, Content-Type, Accept
    """
    return get_jira_auth_headers()


def get_bitbucket_auth_headers() -> dict:
    """
    Get authentication headers for Bitbucket REST API

    Uses app password authentication.

    Returns:
        dict: Headers with Authorization, Content-Type, Accept

    Raises:
        ValueError: If credentials are missing
    """
    username = os.getenv("BITBUCKET_USERNAME")
    app_password = os.getenv("BITBUCKET_APP_PASSWORD")

    if not username or not app_password:
        # Fall back to Atlassian credentials if Bitbucket-specific ones aren't set
        email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")

        if email and token:
            username = email
            app_password = token
        else:
            raise ValueError(
                "Missing Bitbucket credentials. Set BITBUCKET_USERNAME and "
                "BITBUCKET_APP_PASSWORD, or ATLASSIAN_SERVICE_ACCOUNT_* variables."
            )

    auth = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def build_adf_comment(text: str, mentions: Optional[list] = None) -> dict:
    """
    Build Atlassian Document Format (ADF) comment body with optional @mentions

    Args:
        text: Plain text comment (use @Name as placeholder for mentions)
        mentions: List of dicts with 'id' (account ID) and 'name' (display name)

    Returns:
        dict: ADF document structure

    Example:
        build_adf_comment(
            "Hi @Ethan, please review this.",
            mentions=[{"id": "712020:xxx", "name": "Ethan"}]
        )
    """
    content = []

    if mentions:
        # Split text by @mentions and build nodes
        parts = text
        for mention in mentions:
            placeholder = f"@{mention['name']}"
            if placeholder in parts:
                before, after = parts.split(placeholder, 1)
                if before:
                    content.append({"type": "text", "text": before})
                content.append({
                    "type": "mention",
                    "attrs": {
                        "id": mention["id"],
                        "text": f"@{mention['name']}",
                        "accessLevel": ""
                    }
                })
                parts = after

        # Add remaining text
        if parts:
            content.append({"type": "text", "text": parts})
    else:
        content.append({"type": "text", "text": text})

    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": content
            }
        ]
    }


def format_error(status_code: int, message: str) -> dict:
    """
    Format a standardized error response

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        dict: Error response structure
    """
    return {
        "error": True,
        "status_code": status_code,
        "message": message
    }
