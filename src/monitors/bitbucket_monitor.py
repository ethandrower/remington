#!/usr/bin/env python3
"""
Bitbucket Monitor - Polls Bitbucket for PR mentions using bitbucket-cli library
Leverages the existing bitbucket-cli-for-claude-code package
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import bitbucket-cli library
from bitbucket_cli.api import BitbucketAPI
from bitbucket_cli.auth import load_config as load_bb_config
from bitbucket_cli.exceptions import BitbucketAPIError, RateLimitError


class BitbucketMonitor:
    """Polls Bitbucket PRs for service account mentions"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        print("🚀 Initializing Bitbucket Monitor...")

        # Get configuration from .env
        self.workspace = os.getenv("BITBUCKET_WORKSPACE", "citemed")
        repos_str = os.getenv("BITBUCKET_REPOS", "citemed_web,word_addon")
        self.repos = [r.strip() for r in repos_str.split(",")]

        # Service account info for mention detection
        self.service_account_email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        if not self.service_account_email:
            raise ValueError("ATLASSIAN_SERVICE_ACCOUNT_EMAIL required for mention detection")

        # Initialize bitbucket-cli API client
        try:
            bb_config = load_bb_config()
            # Override workspace from .env
            bb_config["auth"]["workspace"] = self.workspace
            self.api = BitbucketAPI(bb_config)
            print("✅ Bitbucket API client initialized")
        except Exception as e:
            raise ValueError(f"Failed to initialize Bitbucket API: {e}")

        # Database for tracking processed mentions
        self.db_path = Path(".claude/data/bot-state/bitbucket_state.db")
        self.init_db()

        # Polling interval from .env or default
        self.polling_interval = int(os.getenv("BITBUCKET_POLL_INTERVAL", "60"))

        print(f"✅ Bitbucket Monitor initialized")
        print(f"   Workspace: {self.workspace}")
        print(f"   Repos: {', '.join(self.repos)}")
        print(f"   Polling interval: {self.polling_interval}s")

    def init_db(self):
        """Initialize database to track processed PR mentions"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Processed PR comments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_pr_comments (
                    repo TEXT,
                    pr_id INTEGER,
                    comment_id TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo, pr_id, comment_id)
                )
            """)

            # Last check timestamp per repo
            conn.execute("""
                CREATE TABLE IF NOT EXISTS last_check_per_repo (
                    repo TEXT PRIMARY KEY,
                    timestamp TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Reviewed PR commits (for PR review tracking)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviewed_pr_commits (
                    repo TEXT,
                    pr_id INTEGER,
                    commit_sha TEXT,
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo, pr_id, commit_sha)
                )
            """)

            # Last reviewed commit per PR
            conn.execute("""
                CREATE TABLE IF NOT EXISTS last_pr_commit (
                    repo TEXT,
                    pr_id INTEGER,
                    commit_sha TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo, pr_id)
                )
            """)

        print(f"✅ Bitbucket database ready at {self.db_path}")

    def get_last_check_time(self, repo: str) -> datetime:
        """Get last check timestamp for a repo"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT timestamp FROM last_check_per_repo WHERE repo = ?", (repo,)
            )
            result = cursor.fetchone()

            if result:
                return datetime.fromisoformat(result[0])
            else:
                # Default to 2 minutes ago
                return datetime.now() - timedelta(minutes=2)

    def set_last_check_time(self, repo: str, timestamp: datetime):
        """Update last check timestamp for a repo"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO last_check_per_repo (repo, timestamp, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (repo, timestamp.isoformat()),
            )

    def is_processed(self, repo: str, pr_id: int, comment_id: str) -> bool:
        """Check if PR comment already processed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_pr_comments WHERE repo=? AND pr_id=? AND comment_id=?",
                (repo, pr_id, comment_id),
            )
            return cursor.fetchone() is not None

    def mark_processed(self, repo: str, pr_id: int, comment_id: str):
        """Mark PR comment as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_pr_comments (repo, pr_id, comment_id) VALUES (?, ?, ?)",
                (repo, pr_id, comment_id),
            )

    def get_last_reviewed_commit(self, repo: str, pr_id: int) -> Optional[str]:
        """Get the last reviewed commit SHA for a PR"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT commit_sha FROM last_pr_commit WHERE repo=? AND pr_id=?",
                (repo, pr_id),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def mark_commit_reviewed(self, repo: str, pr_id: int, commit_sha: str):
        """Mark a commit as reviewed for a PR"""
        with sqlite3.connect(self.db_path) as conn:
            # Add to reviewed commits log
            conn.execute(
                "INSERT OR IGNORE INTO reviewed_pr_commits (repo, pr_id, commit_sha) VALUES (?, ?, ?)",
                (repo, pr_id, commit_sha),
            )
            # Update last reviewed commit
            conn.execute(
                """
                INSERT OR REPLACE INTO last_pr_commit (repo, pr_id, commit_sha, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (repo, pr_id, commit_sha),
            )

    def poll_pull_requests(self) -> List[Dict[str, Any]]:
        """
        Poll Bitbucket for PR mentions across all repositories
        Returns list of events for EventQueue
        """
        all_events = []

        for repo in self.repos:
            try:
                events = self._check_repo(repo)
                all_events.extend(events)
            except RateLimitError as e:
                print(f"⚠️ Rate limit hit for {repo}: {e}")
                break  # Stop checking other repos if rate limited
            except BitbucketAPIError as e:
                print(f"❌ Bitbucket API error for {repo}: {e}")
                continue
            except Exception as e:
                print(f"❌ Unexpected error checking {repo}: {e}")
                continue

        return all_events

    def poll_for_pr_updates(self) -> List[Dict[str, Any]]:
        """
        Poll Bitbucket for PRs with new commits that need review
        Returns list of PR review events
        """
        review_events = []

        for repo in self.repos:
            try:
                # Get all open PRs
                prs = self.api.list_pull_requests(
                    workspace=self.workspace, repo=repo, state="OPEN", fetch_all=False
                )

                for pr in prs:
                    pr_id = pr["id"]
                    pr_title = pr.get("title", "")
                    pr_author_obj = pr.get("author", {})
                    pr_author = pr_author_obj.get("display_name", "")
                    pr_author_account_id = pr_author_obj.get("account_id", "")

                    # Get latest commit hash from PR source branch
                    # PR data includes source branch with commit info
                    source = pr.get("source", {})
                    source_commit = source.get("commit", {})
                    latest_commit_sha = source_commit.get("hash", "")

                    if not latest_commit_sha:
                        # Try alternate path in PR structure
                        branch = source.get("branch", {})
                        latest_commit_sha = branch.get("target", {}).get("hash", "")

                    if not latest_commit_sha:
                        continue

                    # Check if this commit has been reviewed
                    last_reviewed = self.get_last_reviewed_commit(repo, pr_id)

                    if last_reviewed != latest_commit_sha:
                        # New commit detected - needs review
                        pr_url = pr.get("links", {}).get("html", {}).get("href", "")
                        commit_message = source_commit.get("message", "")
                        commit_author = source_commit.get("author", {}).get("raw", "")

                        review_events.append({
                            "source": "bitbucket",
                            "type": "pr_review_needed",
                            "repo": repo,
                            "pr_id": pr_id,
                            "pr_title": pr_title,
                            "pr_author": pr_author,
                            "pr_author_account_id": pr_author_account_id,
                            "pr_url": pr_url,
                            "latest_commit": latest_commit_sha,
                            "commit_message": commit_message,
                            "commit_author": commit_author,
                            "previous_commit": last_reviewed,
                            "timestamp": datetime.now().isoformat(),
                        })

                        print(f"   📝 New commit on {repo} PR#{pr_id}: {latest_commit_sha[:8]}")

            except RateLimitError as e:
                print(f"⚠️ Rate limit hit for {repo}: {e}")
                break
            except BitbucketAPIError as e:
                print(f"❌ Bitbucket API error for {repo}: {e}")
                continue
            except Exception as e:
                # Skip repos that don't exist or aren't accessible
                if "not found" in str(e).lower() or "404" in str(e):
                    continue
                print(f"❌ Unexpected error checking {repo} for PR updates: {e}")
                continue

        return review_events

    def _check_repo(self, repo: str) -> List[Dict[str, Any]]:
        """Check a specific repository for PR mentions"""
        events = []

        # Get recently updated PRs using bitbucket-cli
        try:
            prs = self.api.list_pull_requests(
                workspace=self.workspace, repo=repo, state="OPEN", fetch_all=False
            )
        except Exception as e:
            # Skip repos that don't exist or aren't accessible
            if "not found" in str(e).lower() or "404" in str(e):
                print(f"⏭️  Skipping {repo} (not found or not accessible)")
                return []
            raise

        try:

            for pr in prs:
                pr_id = pr["id"]

                # Check PR activity for mentions using bitbucket-cli
                activity_events = self._check_pr_activity(repo, pr_id, pr)
                events.extend(activity_events)

            # Update last check time
            self.set_last_check_time(repo, datetime.now())

        except Exception as e:
            print(f"❌ Error listing PRs for {repo}: {e}")

        return events

    def _check_pr_activity(
        self, repo: str, pr_id: int, pr_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check PR activity for service account mentions"""
        events = []

        try:
            # Get PR activity using bitbucket-cli
            activities = self.api.get_activity(workspace=self.workspace, repo=repo, pr_id=pr_id)

            for activity in activities:
                if activity.get("comment"):
                    comment = activity["comment"]
                    comment_id = str(comment["id"])
                    comment_text = comment.get("content", {}).get("raw", "")

                    # Check for service account mention
                    if self._is_mentioned(comment_text):
                        # Check if already processed
                        if not self.is_processed(repo, pr_id, comment_id):
                            # Create event for EventQueue
                            events.append({
                                "source": "bitbucket",
                                "type": "pr_comment_mention",
                                "repo": repo,
                                "pr_id": pr_id,
                                "pr_title": pr_data.get("title", ""),
                                "pr_author": pr_data.get("author", {}).get("display_name", ""),
                                "comment_id": comment_id,
                                "comment_text": comment_text,
                                "author": comment.get("user", {}).get("display_name", "unknown"),
                                "timestamp": comment.get("created_on", ""),
                                "pr_url": pr_data.get("links", {})
                                .get("html", {})
                                .get("href", ""),
                            })

                            # Mark as processed
                            self.mark_processed(repo, pr_id, comment_id)

        except Exception as e:
            print(f"❌ Error checking PR activity for {repo} PR#{pr_id}: {e}")

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
        if self.service_account_email and self.service_account_email.lower() in text_lower:
            return True

        return False

    def add_pr_comment(self, repo: str, pr_id: int, message: str) -> bool:
        """Add comment to a PR using bitbucket-cli"""
        try:
            self.api.add_comment(
                workspace=self.workspace, repo=repo, pr_id=pr_id, message=message
            )
            print(f"✅ Posted comment to {repo} PR#{pr_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to post PR comment: {e}")
            return False

    def approve_pr(self, repo: str, pr_id: int) -> bool:
        """Approve a PR using bitbucket-cli"""
        try:
            self.api.approve_pull_request(workspace=self.workspace, repo=repo, pr_id=pr_id)
            print(f"✅ Approved {repo} PR#{pr_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to approve PR: {e}")
            return False