"""
Confluence Direct API Tools

Provides direct REST API access to Confluence, mirroring MCP functions.
Uses service account authentication for reliability.
"""

from .get_page import get_confluence_page
from .search import search_confluence
from .create_page import create_confluence_page
from .update_page import update_confluence_page

__all__ = [
    "get_confluence_page",
    "search_confluence",
    "create_confluence_page",
    "update_confluence_page"
]
