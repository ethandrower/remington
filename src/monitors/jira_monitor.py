#!/usr/bin/env python3
"""
Jira Monitor - Polls Jira for service account mentions in comments
Uses Jira Cloud REST API v3 with JQL queries
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from src.config import get_jira_base_url, get_atlassian_config


class JiraMonitor:
    """Polls Jira issues for service account mentions"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        print("🚀 Initializing Jira Monitor...")

        # Get configuration from .env via src/config
        self.api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")

        atlassian_config = get_atlassian_config()
        self.cloud_id = atlassian_config['cloud_id']
        self.jira_base_url = get_jira_base_url()

        # Support comma-separated project keys (e.g., "PROJ,DEV")
        self.project_key = atlassian_config['project_key']
        self.project_keys = [k.strip() for k in self.project_key.split(",")]

        if not all([self.api_token, self.email, self.cloud_id]):
            raise ValueError(
                "Missing Atlassian configuration. Ensure ATLASSIAN_SERVICE_ACCOUNT_TOKEN, "
                "ATLASSIAN_SERVICE_ACCOUNT_EMAIL, and ATLASSIAN_CLOUD_ID are set in .env"
            )

        # Remove quotes if present
        self.api_token = self.api_token.strip("'\"")
        self.email = self.email.strip("'\"")

        # Build base URL
        self.base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"

        # Database for tracking processed mentions
        self.db_path = Path(".claude/data/bot-state/jira_state.db")
        self.init_db()

        # Polling interval from .env or default
        self.polling_interval = int(os.getenv("JIRA_POLL_INTERVAL", "60"))

        print(f"✅ Jira Monitor initialized")
        print(f"   Cloud ID: {self.cloud_id}")
        print(f"   Projects: {', '.join(self.project_keys)}")
        print(f"   Polling interval: {self.polling_interval}s")

    def init_db(self):
        """Initialize database to track processed mentions"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Processed mentions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_mentions (
                    issue_key TEXT,
                    comment_id TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (issue_key, comment_id)
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

        print(f"✅ Jira database ready at {self.db_path}")

    def get_last_check_time(self) -> datetime:
        """Get last check timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT timestamp FROM last_check WHERE id = 1")
            result = cursor.fetchone()

            if result:
                return datetime.fromisoformat(result[0])
            else:
                # Default to 2 minutes ago
                return datetime.now() - timedelta(minutes=2)

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

    def is_processed(self, issue_key: str, comment_id: str) -> bool:
        """Check if comment already processed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_mentions WHERE issue_key=? AND comment_id=?",
                (issue_key, comment_id),
            )
            return cursor.fetchone() is not None

    def mark_processed(self, issue_key: str, comment_id: str):
        """Mark comment as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_mentions (issue_key, comment_id) VALUES (?, ?)",
                (issue_key, comment_id),
            )

    def poll_for_mentions(self) -> List[Dict[str, Any]]:
        """
        Poll Jira for service account mentions
        Returns list of events for EventQueue
        """
        try:
            # Build JQL query for recently updated issues
            # Look for issues updated in last 3 days (database prevents reprocessing)
            # Support multiple projects (e.g., "ECD,MDP" becomes "project IN (ECD, MDP)")
            if len(self.project_keys) == 1:
                project_filter = f'project = {self.project_keys[0]}'
            else:
                project_list = ', '.join(self.project_keys)
                project_filter = f'project IN ({project_list})'

            jql = f'{project_filter} AND updated >= -3d ORDER BY updated DESC'

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            params = {
                "jql": jql,
                "fields": "summary,comment,updated,status,assignee,priority",
                "maxResults": 50,
                "expand": "renderedFields",
            }

            response = requests.get(
                f"{self.base_url}/rest/api/3/search/jql", headers=headers, params=params, timeout=30
            )

            if response.status_code == 429:
                print("⚠️ Jira rate limit hit, backing off...")
                return []
            elif response.status_code != 200:
                print(f"❌ Jira API error: {response.status_code} - {response.text}")
                return []

            data = response.json()
            issues = data.get("issues", [])

            # Filter for new mentions
            events = self._filter_new_mentions(issues)

            # Update last check time
            self.set_last_check_time(datetime.now())

            return events

        except Exception as e:
            print(f"❌ Jira polling error: {e}")
            return []

    def _filter_new_mentions(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter issues for new service account mentions"""
        new_events = []

        for issue in issues:
            issue_key = issue["key"]
            fields = issue.get("fields", {})
            comments = fields.get("comment", {}).get("comments", [])

            for comment in comments:
                comment_id = str(comment["id"])
                comment_body = comment.get("body", {})

                # Extract text from ADF (Atlassian Document Format) or plain text
                comment_text = self._extract_comment_text(comment_body)

                # Check if service account is mentioned
                if self._is_service_account_mentioned(comment_text):
                    # Check if we've already processed this comment
                    if not self.is_processed(issue_key, comment_id):
                        # Fetch complete issue context (description + all comments)
                        print(f"   📜 Fetching issue context for {issue_key}...")
                        issue_context = self.get_issue_context(issue_key)

                        if issue_context:
                            print(f"   ✅ Context fetched: {len(issue_context.get('comments', []))} comments")
                        else:
                            print(f"   ⚠️  Could not fetch context, proceeding with basic info")

                        # Create event for EventQueue
                        new_events.append({
                            "source": "jira",
                            "type": "comment_mention",
                            "issue_key": issue_key,
                            "issue_summary": fields.get("summary", ""),
                            "issue_status": fields.get("status", {}).get("name", ""),
                            "issue_priority": fields.get("priority", {}).get("name", ""),
                            "comment_id": comment_id,
                            "comment_text": comment_text,
                            "author": comment.get("author", {}).get("displayName", "unknown"),
                            "author_id": comment.get("author", {}).get("accountId", ""),
                            "timestamp": comment.get("created", ""),
                            "issue_url": f"{self.jira_base_url}/browse/{issue_key}",
                            "issue_context": issue_context,  # NEW - Include full context
                        })

                        # Mark as processed
                        self.mark_processed(issue_key, comment_id)

        if new_events:
            print(f"✅ Found {len(new_events)} new Jira mentions")

        return new_events

    def _extract_comment_text(self, comment_body: Any) -> str:
        """Extract text from Jira comment (handles ADF format)"""
        if isinstance(comment_body, str):
            return comment_body

        if isinstance(comment_body, dict):
            # ADF (Atlassian Document Format)
            if "content" in comment_body:
                text_parts = []
                for content_block in comment_body["content"]:
                    if content_block.get("type") == "paragraph":
                        for item in content_block.get("content", []):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "mention":
                                # Handle mentions
                                text_parts.append(f"@{item.get('attrs', {}).get('text', '')}")
                return " ".join(text_parts)

        return str(comment_body)

    def _is_service_account_mentioned(self, text: str) -> bool:
        """Check if service account is mentioned in comment"""
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

    def get_issue_context(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete issue context: summary, description, and all comments

        Returns:
            {
                "issue_key": "PROJ-862",
                "summary": "Implement user authentication",
                "description": "Add OAuth2 authentication...",
                "status": "In Progress",
                "priority": "High",
                "assignee": "Mohamed",
                "comments": [
                    {
                        "id": "12345",
                        "author": "Ethan",
                        "text": "What's the status?",
                        "created": "2026-01-04T10:30:00Z"
                    }
                ]
            }
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
            }

            # Fetch issue with expanded fields
            response = requests.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                params={
                    "fields": "summary,description,status,priority,assignee,comment",
                    "expand": "renderedFields"
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"⚠️ Failed to fetch issue context for {issue_key}: {response.status_code}")
                return None

            data = response.json()
            fields = data.get("fields", {})

            # Extract all comments in chronological order
            comments = []
            for comment in fields.get("comment", {}).get("comments", []):
                comments.append({
                    "id": comment["id"],
                    "author": comment.get("author", {}).get("displayName", "Unknown"),
                    "author_id": comment.get("author", {}).get("accountId", ""),
                    "text": self._extract_comment_text(comment.get("body", {})),
                    "created": comment.get("created", "")
                })

            # Extract description text (handle ADF format)
            description_raw = fields.get("description", "")
            if isinstance(description_raw, dict):
                # ADF format - extract text
                description = self._extract_comment_text(description_raw)
            else:
                description = str(description_raw) if description_raw else ""

            return {
                "issue_key": issue_key,
                "summary": fields.get("summary", ""),
                "description": description,
                "status": fields.get("status", {}).get("name", "Unknown"),
                "priority": fields.get("priority", {}).get("name", "None"),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned",
                "comments": comments
            }

        except Exception as e:
            print(f"❌ Error fetching issue context for {issue_key}: {e}")
            return None

    def add_comment(self, issue_key: str, comment_text: str) -> bool:
        """Add comment to a Jira issue"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            # Build ADF format comment
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment_text}],
                        }
                    ],
                }
            }

            response = requests.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                print(f"✅ Posted comment to {issue_key}")
                return True
            else:
                print(f"❌ Failed to post comment: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error posting Jira comment: {e}")
            return False

    def add_comment_with_adf(self, issue_key: str, adf_content: Dict[str, Any]) -> bool:
        """
        Add comment to a Jira issue using full ADF (Atlassian Document Format)

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123")
            adf_content: Complete ADF content array (the "content" field of the doc)
                         This allows mentions, formatting, lists, etc.

        Example for mentions:
            adf_content = [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hi "},
                        {"type": "mention", "attrs": {"id": "account_id", "text": "@Name"}},
                        {"type": "text", "text": ", here is my response."}
                    ]
                }
            ]
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            # Build ADF format comment with custom content
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": adf_content,
                }
            }

            response = requests.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                comment_id = response.json().get("id", "unknown")
                print(f"✅ Posted ADF comment to {issue_key} (comment ID: {comment_id})")
                return True
            else:
                print(f"❌ Failed to post ADF comment: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error posting ADF comment: {e}")
            return False

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """Update a Jira issue"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {"fields": fields}

            response = requests.put(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 204:
                print(f"✅ Updated {issue_key}")
                return True
            else:
                print(f"❌ Failed to update issue: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error updating Jira issue: {e}")
            return False