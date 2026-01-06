"""
Direct API Tools for Jira, Confluence, and Bitbucket

These tools provide direct REST API access without MCP OAuth dependencies.
Each tool can be called via CLI or imported as a Python function.

Usage:
    # CLI
    python -m src.tools.jira.search "project = ECD"

    # Python
    from src.tools.jira.search import search_jira
    results = search_jira("project = ECD")
"""

from .base import (
    get_jira_auth_headers,
    get_confluence_auth_headers,
    get_bitbucket_auth_headers,
    ATLASSIAN_CLOUD_ID,
    JIRA_BASE_URL,
    CONFLUENCE_BASE_URL,
    BITBUCKET_BASE_URL,
    BITBUCKET_WORKSPACE,
)

__all__ = [
    "get_jira_auth_headers",
    "get_confluence_auth_headers",
    "get_bitbucket_auth_headers",
    "ATLASSIAN_CLOUD_ID",
    "JIRA_BASE_URL",
    "CONFLUENCE_BASE_URL",
    "BITBUCKET_BASE_URL",
    "BITBUCKET_WORKSPACE",
]
