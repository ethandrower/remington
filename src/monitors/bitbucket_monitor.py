#!/usr/bin/env python3
"""
Bitbucket Monitor - Polls Bitbucket for PR mentions using bitbucket-cli library
Leverages the existing bitbucket-cli-for-claude-code package
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

# Import bitbucket-cli library
from bitbucket_cli.api import BitbucketAPI
from bitbucket_cli.auth import load_config as load_bb_config
from bitbucket_cli.exceptions import BitbucketAPIError, RateLimitError

from src.database.connection import get_engine
from src.database.schema import (
    bb_processed_pr_comments,
    bb_last_check_per_repo,
    bb_reviewed_pr_commits,
    bb_last_pr_commit,
)


class BitbucketMonitor:
    """Polls Bitbucket PRs for service account mentions"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        engine: Optional[Engine] = None,
    ):
        print("🚀 Initializing Bitbucket Monitor...")

        # Get configuration from .env
        self.workspace = os.getenv("BITBUCKET_WORKSPACE", "")
        repos_str = os.getenv("BITBUCKET_REPOS", "")
        self.repos = [r.strip() for r in repos_str.split(",")]

        # Service account info for mention detection
        self.service_account_email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        if not self.service_account_email:
            raise ValueError("ATLASSIAN_SERVICE_ACCOUNT_EMAIL required for mention detection")
        self.service_account_name = os.getenv("SERVICE_ACCOUNT_NAME", "").lower().strip()

        # Initialize bitbucket-cli API client
        try:
            bb_config = load_bb_config()
            # Override workspace from .env
            bb_config["auth"]["workspace"] = self.workspace
            self.api = BitbucketAPI(bb_config)
            print("✅ Bitbucket API client initialized")
        except Exception as e:
            raise ValueError(f"Failed to initialize Bitbucket API: {e}")

        # Fetch our own Bitbucket nickname at startup for reliable mention detection.
        # Bitbucket @mentions use @nickname (plain text), not account ID like Jira.
        self.account_nickname = self._fetch_own_nickname()

        # Database engine — injected (tests) or auto-configured (production)
        if engine is not None:
            self.engine = engine
        else:
            self.engine = get_engine(
                default_path=".claude/data/bot-state/bitbucket_state.db"
            )
        self.init_db()

        # Polling interval from .env or default
        self.polling_interval = int(os.getenv("BITBUCKET_POLL_INTERVAL", "60"))

        print(f"✅ Bitbucket Monitor initialized")
        print(f"   Workspace: {self.workspace}")
        print(f"   Repos: {', '.join(self.repos)}")
        print(f"   Account nickname: {self.account_nickname or 'unknown (mention detection may fail)'}")
        print(f"   Polling interval: {self.polling_interval}s")

    def _fetch_own_nickname(self) -> Optional[str]:
        """Fetch the service account's own Bitbucket nickname via /user endpoint."""
        try:
            import requests
            bb_config = load_bb_config()
            auth_config = bb_config.get("auth", {})
            username = auth_config.get("username", "")
            app_password = auth_config.get("app_password", "")

            response = requests.get(
                "https://api.bitbucket.org/2.0/user",
                auth=(username, app_password),
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                nickname = data.get("nickname") or data.get("username") or data.get("display_name")
                return nickname.lower() if nickname else None
            print(f"⚠️  Could not fetch Bitbucket nickname: {response.status_code}")
            return None
        except Exception as e:
            print(f"⚠️  Error fetching Bitbucket nickname: {e}")
            return None

    def init_db(self):
        """Initialize database to track processed PR mentions"""
        for table in (
            bb_processed_pr_comments,
            bb_last_check_per_repo,
            bb_reviewed_pr_commits,
            bb_last_pr_commit,
        ):
            table.create(self.engine, checkfirst=True)
        print("✅ Bitbucket database ready")

    def get_last_check_time(self, repo: str) -> datetime:
        """Get last check timestamp for a repo"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT timestamp FROM bb_last_check_per_repo WHERE repo = :repo"),
                {"repo": repo},
            ).scalar()
            if result:
                return datetime.fromisoformat(result)
            return datetime.now() - timedelta(minutes=2)

    def set_last_check_time(self, repo: str, timestamp: datetime):
        """Update last check timestamp for a repo"""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO bb_last_check_per_repo (repo, timestamp, updated_at)
                    VALUES (:repo, :ts, :now)
                    ON CONFLICT (repo) DO UPDATE SET
                        timestamp = excluded.timestamp,
                        updated_at = excluded.updated_at
                """),
                {"repo": repo, "ts": timestamp.isoformat(), "now": datetime.now().isoformat()},
            )

    def is_processed(self, repo: str, pr_id: int, comment_id: str) -> bool:
        """Check if PR comment already processed"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 1 FROM bb_processed_pr_comments
                    WHERE repo = :repo AND pr_id = :pr_id AND comment_id = :comment_id
                """),
                {"repo": repo, "pr_id": pr_id, "comment_id": comment_id},
            ).fetchone()
            return result is not None

    def mark_processed(self, repo: str, pr_id: int, comment_id: str):
        """Mark PR comment as processed"""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO bb_processed_pr_comments (repo, pr_id, comment_id, processed_at)
                    VALUES (:repo, :pr_id, :comment_id, :now)
                    ON CONFLICT DO NOTHING
                """),
                {"repo": repo, "pr_id": pr_id, "comment_id": comment_id, "now": datetime.now().isoformat()},
            )

    def get_last_reviewed_commit(self, repo: str, pr_id: int) -> Optional[str]:
        """Get the last reviewed commit SHA for a PR"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT commit_sha FROM bb_last_pr_commit WHERE repo = :repo AND pr_id = :pr_id"),
                {"repo": repo, "pr_id": pr_id},
            ).scalar()
            return result

    def mark_commit_reviewed(self, repo: str, pr_id: int, commit_sha: str):
        """Mark a commit as reviewed for a PR"""
        now = datetime.now().isoformat()
        with self.engine.begin() as conn:
            # Add to reviewed commits log
            conn.execute(
                text("""
                    INSERT INTO bb_reviewed_pr_commits (repo, pr_id, commit_sha, reviewed_at)
                    VALUES (:repo, :pr_id, :sha, :now)
                    ON CONFLICT DO NOTHING
                """),
                {"repo": repo, "pr_id": pr_id, "sha": commit_sha, "now": now},
            )
            # Update last reviewed commit
            conn.execute(
                text("""
                    INSERT INTO bb_last_pr_commit (repo, pr_id, commit_sha, updated_at)
                    VALUES (:repo, :pr_id, :sha, :now)
                    ON CONFLICT (repo, pr_id) DO UPDATE SET
                        commit_sha = excluded.commit_sha,
                        updated_at = excluded.updated_at
                """),
                {"repo": repo, "pr_id": pr_id, "sha": commit_sha, "now": now},
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

                    # Only review on initial PR submission (first time we see this PR)
                    last_reviewed = self.get_last_reviewed_commit(repo, pr_id)

                    if last_reviewed is None:
                        # First time seeing this PR — queue initial review
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

                        print(f"   📝 New PR on {repo} PR#{pr_id} — queuing initial review")
                    elif last_reviewed != latest_commit_sha:
                        # PR updated — just record the new commit without re-reviewing
                        self.mark_commit_reviewed(repo, pr_id, latest_commit_sha)
                        print(f"   ↩️  Skipping re-review for {repo} PR#{pr_id} (commit {latest_commit_sha[:8]})")

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

                    # Skip comments posted by the service account itself to prevent self-loops
                    comment_author_name = comment.get("user", {}).get("nickname", "").lower()
                    comment_author_display = comment.get("user", {}).get("display_name", "").lower()
                    if self.service_account_name and (
                        comment_author_name == self.service_account_name
                        or (self.account_nickname and comment_author_name == self.account_nickname)
                        or comment_author_display == self.service_account_name
                    ):
                        continue

                    # Check for service account mention (requires @ prefix)
                    if self._is_mentioned(comment_text):
                        # Check if already processed
                        if not self.is_processed(repo, pr_id, comment_id):
                            # NOTE: NOT marking as processed here — only after agent
                            # responds successfully. This allows retries on failure.
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

        except Exception as e:
            print(f"❌ Error checking PR activity for {repo} PR#{pr_id}: {e}")

        return events

    def _is_mentioned(self, text: str) -> bool:
        """Check if service account is mentioned in a PR comment.

        Bitbucket @mentions are plain text: @nickname. We ONLY match with the @
        prefix to avoid triggering on comments that naturally mention the bot's
        name (e.g. the bot's own replies that say "Remington" or "CiteMed AI (Remington)").
        """
        text_lower = text.lower()

        # Primary: check by account nickname fetched at startup (requires @ prefix)
        if self.account_nickname and f"@{self.account_nickname}" in text_lower:
            return True

        # Fallback: SERVICE_ACCOUNT_NAME env var (requires @ prefix — bare name must NOT match)
        if self.service_account_name:
            if f"@{self.service_account_name}" in text_lower:
                return True

        return False

    def get_pr_context(self, repo: str, pr_id: int) -> str:
        """
        Fetch full PR context for passing to the agent: title, description,
        source/dest branches, linked Jira tickets, diffstat, and recent comments.

        Returns a formatted string to prepend to the agent message.
        """
        import re
        lines = []

        try:
            pr = self.api.get_pull_request(workspace=self.workspace, repo=repo, pr_id=pr_id)
            title = pr.get("title", "")
            description = pr.get("description", "") or ""
            source_branch = pr.get("source", {}).get("branch", {}).get("name", "")
            dest_branch = pr.get("destination", {}).get("branch", {}).get("name", "")
            author = pr.get("author", {}).get("display_name", "Unknown")
            state = pr.get("state", "")
            pr_url = pr.get("links", {}).get("html", {}).get("href", "")

            # Extract Jira ticket keys from title, branch, and description
            ticket_pattern = re.compile(r'\b[A-Z]{2,10}-\d+\b')
            tickets = sorted(set(
                ticket_pattern.findall(title)
                + ticket_pattern.findall(source_branch)
                + ticket_pattern.findall(description[:500])
            ))

            lines.append(f"=== Bitbucket PR Context ===")
            lines.append(f"Repo: {repo} | PR #{pr_id} | State: {state}")
            lines.append(f"Title: {title}")
            lines.append(f"Author: {author}")
            lines.append(f"Branch: {source_branch} → {dest_branch}")
            if pr_url:
                lines.append(f"URL: {pr_url}")
            if tickets:
                lines.append(f"Linked Jira tickets: {', '.join(tickets)}")
            if description.strip():
                lines.append(f"\nDescription:\n{description[:800].strip()}")
        except Exception as e:
            lines.append(f"[Could not fetch PR details: {e}]")

        # Diffstat — summary of changed files
        try:
            diffstat = self.api.get_diffstat(workspace=self.workspace, repo=repo, pr_id=pr_id)
            if isinstance(diffstat, list) and diffstat:
                lines.append(f"\nFiles changed ({len(diffstat)}):")
                for entry in diffstat[:20]:  # cap at 20 files
                    status = entry.get("status", "")
                    path = (
                        entry.get("new", {}) or entry.get("old", {}) or {}
                    ).get("path", "")
                    lines.append(f"  [{status}] {path}")
                if len(diffstat) > 20:
                    lines.append(f"  ... and {len(diffstat) - 20} more files")
        except Exception:
            pass

        # Actual diff — truncated to keep context manageable
        try:
            diff = self.api.get_diff(workspace=self.workspace, repo=repo, pr_id=pr_id)
            if diff:
                diff_text = diff if isinstance(diff, str) else str(diff)
                MAX_DIFF = 6000
                if len(diff_text) > MAX_DIFF:
                    diff_text = diff_text[:MAX_DIFF] + f"\n... [diff truncated — {len(diff_text) - MAX_DIFF} chars omitted]"
                lines.append(f"\nDiff:\n{diff_text}")
        except Exception:
            pass

        # Recent comments (last 20 non-deleted, non-inline)
        try:
            comments = self.api.get_comments(workspace=self.workspace, repo=repo, pr_id=pr_id)
            visible = [
                c for c in comments
                if not c.get("deleted") and not c.get("inline")
            ]
            recent = visible[-20:]  # last 20 to keep context manageable
            if recent:
                lines.append(f"\nComments ({len(visible)} total, showing last {len(recent)}):")
                for c in recent:
                    commenter = c.get("user", {}).get("display_name", "Unknown")
                    body = c.get("content", {}).get("raw", "").strip()[:300]
                    lines.append(f"\n  [{commenter}]: {body}")
        except Exception:
            pass

        lines.append("=== End PR Context ===\n")
        return "\n".join(lines)

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