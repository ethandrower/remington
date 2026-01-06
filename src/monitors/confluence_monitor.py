#!/usr/bin/env python3
"""
Confluence Monitor - Polls Confluence for service account mentions in page comments
Uses Confluence Cloud REST API v2
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from src.config import get_jira_base_url


class ConfluenceMonitor:
    """Polls Confluence pages for service account mentions"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        print("🚀 Initializing Confluence Monitor...")

        # Get configuration from .env
        self.api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        self.cloud_id = os.getenv("ATLASSIAN_CLOUD_ID")

        # Confluence spaces to monitor (from .env or default)
        spaces_str = os.getenv("CONFLUENCE_SPACES", "ECD,COMP")
        self.spaces = [s.strip() for s in spaces_str.split(",")]

        if not all([self.api_token, self.email, self.cloud_id]):
            raise ValueError(
                "Missing Atlassian configuration. Ensure ATLASSIAN_SERVICE_ACCOUNT_TOKEN, "
                "ATLASSIAN_SERVICE_ACCOUNT_EMAIL, and ATLASSIAN_CLOUD_ID are set in .env"
            )

        # Remove quotes if present
        self.api_token = self.api_token.strip("'\"")
        self.email = self.email.strip("'\"")

        # Build base URL - Confluence uses domain-based URL, not cloud gateway
        self.base_url = get_jira_base_url()  # Same as Jira URL for Atlassian Cloud

        # Database for tracking processed mentions
        self.db_path = Path(".claude/data/bot-state/confluence_state.db")
        self.init_db()

        # Polling interval from .env or default (longer for Confluence due to stricter rate limits)
        self.polling_interval = int(os.getenv("CONFLUENCE_POLL_INTERVAL", "120"))

        print(f"✅ Confluence Monitor initialized")
        print(f"   Cloud ID: {self.cloud_id}")
        print(f"   Spaces: {', '.join(self.spaces)}")
        print(f"   Polling interval: {self.polling_interval}s")

    def init_db(self):
        """Initialize database to track processed mentions"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Processed comments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_comments (
                    page_id TEXT,
                    comment_id TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (page_id, comment_id)
                )
            """)

            # Last check timestamp
            conn.execute("""
                CREATE TABLE IF NOT EXISTS last_check (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        print(f"✅ Confluence database ready at {self.db_path}")

    def get_last_check_time(self) -> datetime:
        """Get last check timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT timestamp FROM last_check WHERE id = 1")
            result = cursor.fetchone()

            if result:
                return datetime.fromisoformat(result[0])
            else:
                # Default to 5 minutes ago
                return datetime.now() - timedelta(minutes=5)

    def set_last_check_time(self, timestamp: datetime):
        """Update last check timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO last_check (id, timestamp, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
            """,
                (timestamp.isoformat(),),
            )

    def is_processed(self, page_id: str, comment_id: str) -> bool:
        """Check if comment already processed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_comments WHERE page_id=? AND comment_id=?",
                (page_id, comment_id),
            )
            return cursor.fetchone() is not None

    def mark_processed(self, page_id: str, comment_id: str):
        """Mark comment as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_comments (page_id, comment_id) VALUES (?, ?)",
                (page_id, comment_id),
            )

    def poll_pages(self) -> List[Dict[str, Any]]:
        """
        Poll Confluence for service account mentions
        Returns list of events for EventQueue
        """
        try:
            last_check = self.get_last_check_time()

            # Confluence domain-based API uses Basic auth (email:token)
            import base64
            credentials = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            headers = {
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
            }

            # Get recently modified pages
            params = {
                "limit": 25,  # Reduced for rate limiting
                "status": "current",
                "sort": "-modified-date",
            }

            response = requests.get(
                f"{self.base_url}/wiki/api/v2/pages",
                headers=headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                print("⚠️ Confluence rate limit hit, backing off...")
                return []
            elif response.status_code != 200:
                print(f"❌ Confluence API error: {response.status_code} - {response.text}")
                return []

            data = response.json()
            pages = data.get("results", [])

            # Filter pages modified since last check
            recent_pages = []
            for page in pages:
                modified_at = datetime.fromisoformat(
                    page.get("version", {}).get("createdAt", "").replace("Z", "+00:00")
                )
                if modified_at > last_check:
                    recent_pages.append(page)

            # Check comments on recent pages
            all_events = []
            for page in recent_pages:
                page_events = self._check_page_comments(page)
                all_events.extend(page_events)

            # Update last check time
            self.set_last_check_time(datetime.now())

            return all_events

        except Exception as e:
            print(f"❌ Confluence polling error: {e}")
            return []

    def _check_page_comments(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check a specific page for mentions in comments"""
        events = []
        page_id = page["id"]
        page_title = page.get("title", "")

        # Confluence domain-based API uses Basic auth
        import base64
        credentials = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
        }

        try:
            # Get footer comments
            footer_response = requests.get(
                f"{self.base_url}/wiki/api/v2/pages/{page_id}/footer-comments",
                headers=headers,
                params={"limit": 50},
                timeout=30,
            )

            if footer_response.status_code == 200:
                footer_data = footer_response.json()
                footer_comments = footer_data.get("results", [])
                events.extend(
                    self._process_comments(page_id, page_title, footer_comments, "footer")
                )

            # Get inline comments
            inline_response = requests.get(
                f"{self.base_url}/wiki/api/v2/pages/{page_id}/inline-comments",
                headers=headers,
                params={"limit": 50},
                timeout=30,
            )

            if inline_response.status_code == 200:
                inline_data = inline_response.json()
                inline_comments = inline_data.get("results", [])
                events.extend(
                    self._process_comments(page_id, page_title, inline_comments, "inline")
                )

        except Exception as e:
            print(f"❌ Error checking comments for page {page_id}: {e}")

        return events

    def _process_comments(
        self, page_id: str, page_title: str, comments: List[Dict], comment_type: str
    ) -> List[Dict[str, Any]]:
        """Process comments for mentions"""
        events = []

        for comment in comments:
            comment_id = comment["id"]
            comment_body = comment.get("body", {}).get("storage", {}).get("value", "")

            # Check for mention
            if self._is_mentioned(comment_body):
                # Check if already processed
                if not self.is_processed(page_id, comment_id):
                    # Create event for EventQueue
                    events.append({
                        "source": "confluence",
                        "type": f"page_{comment_type}_comment_mention",
                        "page_id": page_id,
                        "page_title": page_title,
                        "comment_id": comment_id,
                        "comment_type": comment_type,
                        "comment_text": comment_body[:500],  # Truncate HTML
                        "author": comment.get("authorId", "unknown"),
                        "timestamp": comment.get("createdAt", ""),
                        "page_url": f"{self.base_url}/wiki/spaces/{page_id}",
                    })

                    # Mark as processed
                    self.mark_processed(page_id, comment_id)

        return events

    def _is_mentioned(self, text: str) -> bool:
        """Check if service account is mentioned in text"""
        text_lower = text.lower()

        # Check for various mention formats
        if "@remington" in text_lower:
            return True

        if "remington" in text_lower:
            return True

        # Check for email mention
        if self.email and self.email.lower() in text_lower:
            return True

        return False

    def add_comment(self, page_id: str, comment_text: str) -> bool:
        """Add comment to a Confluence page"""
        try:
            # Confluence domain-based API uses Basic auth
            import base64
            credentials = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
            headers = {
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {
                "body": {"representation": "storage", "value": f"<p>{comment_text}</p>"}
            }

            response = requests.post(
                f"{self.base_url}/wiki/api/v2/pages/{page_id}/footer-comments",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                print(f"✅ Posted comment to Confluence page {page_id}")
                return True
            else:
                print(f"❌ Failed to post comment: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error posting Confluence comment: {e}")
            return False
