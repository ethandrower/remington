#!/usr/bin/env python3
"""
Slack Monitor - Polls Slack for service account mentions
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_engine
from src.database.schema import (
    slack_processed_messages,
    slack_tracked_threads,
    slack_sla_alerts,
)


class SlackMonitor:
    """Polls Slack for bot mentions and generates events"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        engine: Optional[Engine] = None,
    ):
        print("🚀 Initializing Slack Monitor...")

        # Slack configuration from .env
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.target_channel = os.getenv("SLACK_CHANNEL_STANDUP")
        self.bot_user_id = os.getenv("SLACK_BOT_USER_ID")

        if not all([self.slack_token, self.target_channel, self.bot_user_id]):
            raise ValueError(
                "Missing Slack configuration. Ensure SLACK_BOT_TOKEN, "
                "SLACK_CHANNEL_STANDUP, and SLACK_BOT_USER_ID are set in .env"
            )

        # Database engine — injected (tests) or auto-configured (production)
        if engine is not None:
            self.engine = engine
        else:
            self.engine = get_engine(
                default_path=".claude/data/bot-state/slack_state.db"
            )
        self.init_db()

        # Polling interval from .env or default (strip comments)
        poll_interval_str = os.getenv("SLACK_POLL_INTERVAL", "15")
        # Handle .env files with comments (e.g., "15 # comment")
        if '#' in poll_interval_str:
            poll_interval_str = poll_interval_str.split('#')[0].strip()
        self.polling_interval = int(poll_interval_str)

        print(f"✅ Slack Monitor initialized")
        print(f"   Channel: {self.target_channel}")
        print(f"   Bot User ID: {self.bot_user_id}")
        print(f"   Polling interval: {self.polling_interval}s")

    def init_db(self):
        """Create tables if they don't already exist."""
        for table in (slack_processed_messages, slack_tracked_threads, slack_sla_alerts):
            table.create(self.engine, checkfirst=True)
        print("✅ Slack database ready")

    def get_last_processed_ts(self) -> float:
        """Get timestamp of last processed message."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT MAX(ts) FROM slack_processed_messages WHERE channel = :channel"),
                {"channel": self.target_channel},
            ).scalar()
            return float(result) if result else 0.0

    def register_thread(self, thread_ts: str, context: str = ""):
        """Register a thread to monitor for replies (e.g., SLA violations)."""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO slack_tracked_threads (thread_ts, channel, context, last_checked_ts)
                    VALUES (:thread_ts, :channel, :context, '0')
                    ON CONFLICT (thread_ts) DO UPDATE SET
                        context = excluded.context,
                        channel = excluded.channel
                """),
                {"thread_ts": thread_ts, "channel": self.target_channel, "context": context},
            )

    def get_thread_context(self, thread_ts: str) -> Dict[str, Any]:
        """Fetch full thread context (parent message + all replies)"""
        headers = {"Authorization": f"Bearer {self.slack_token}"}
        params = {"channel": self.target_channel, "ts": thread_ts, "limit": 50}

        try:
            response = requests.get(
                "https://slack.com/api/conversations.replies",
                headers=headers,
                params=params,
                timeout=10,
            )

            if not response.json().get("ok"):
                return {"parent": None, "replies": []}

            messages = response.json().get("messages", [])
            if not messages:
                return {"parent": None, "replies": []}

            # First message is the parent
            parent = messages[0]
            replies = messages[1:] if len(messages) > 1 else []

            return {
                "parent": {
                    "text": parent.get("text", ""),
                    "user": parent.get("user", "unknown"),
                    "ts": parent.get("ts", ""),
                    "timestamp": datetime.fromtimestamp(float(parent["ts"])).isoformat() if parent.get("ts") else "",
                },
                "replies": [
                    {
                        "text": reply.get("text", ""),
                        "user": reply.get("user", "unknown"),
                        "ts": reply.get("ts", ""),
                        "timestamp": datetime.fromtimestamp(float(reply["ts"])).isoformat() if reply.get("ts") else "",
                    }
                    for reply in replies
                ],
            }

        except Exception as e:
            print(f"⚠️  Error fetching thread context {thread_ts}: {e}")
            return {"parent": None, "replies": []}

    def poll_thread_replies(self, thread_ts: str) -> List[Dict[str, Any]]:
        """Poll a specific thread for new replies"""
        headers = {"Authorization": f"Bearer {self.slack_token}"}

        # Get last checked timestamp for this thread
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT last_checked_ts FROM slack_tracked_threads WHERE thread_ts = :ts"),
                {"ts": thread_ts},
            ).fetchone()
            last_checked = float(row[0]) if row and row[0] else 0.0

        params = {"channel": self.target_channel, "ts": thread_ts, "limit": 20}
        if last_checked > 0:
            params["oldest"] = str(last_checked)

        try:
            response = requests.get(
                "https://slack.com/api/conversations.replies",
                headers=headers,
                params=params,
                timeout=10,
            )

            if not response.json().get("ok"):
                return []

            messages = response.json().get("messages", [])
            events = []

            for message in messages:
                # Skip the parent message and bot messages
                if message.get("ts") == thread_ts:
                    continue

                if message.get("bot_id") or message.get("user") == self.bot_user_id:
                    continue

                # Only process if message is newer than last checked
                if float(message["ts"]) <= last_checked:
                    continue

                # Check for bot mention
                msg_text = message.get("text", "")
                if f"<@{self.bot_user_id}>" in msg_text:
                    # Skip if already processed (prevents duplicate handling)
                    if self.is_processed(message["ts"]):
                        print(f"   ⏭️  Skipping already processed message {message['ts']}")
                        continue

                    # NOTE: Message is NOT marked as processed here - only after successful response
                    # This allows retries if Claude times out or errors

                    # Send immediate acknowledgment in thread
                    try:
                        self.send_response("👀 On it! Processing your request...", thread_ts=thread_ts)
                        print(f"   ✅ Sent immediate acknowledgment to thread {thread_ts}")
                    except Exception as ack_error:
                        print(f"   ⚠️  Could not send acknowledgment: {ack_error}")

                    # Update last_checked_ts for this thread
                    with self.engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO slack_tracked_threads
                                    (thread_ts, channel, context, last_checked_ts)
                                VALUES (:ts, :channel, 'Auto-tracked from reply', :msg_ts)
                                ON CONFLICT (thread_ts) DO UPDATE SET
                                    last_checked_ts = excluded.last_checked_ts,
                                    channel = excluded.channel
                            """),
                            {"ts": thread_ts, "channel": self.target_channel, "msg_ts": message["ts"]},
                        )

                    # Fetch full thread context for Claude
                    thread_context = self.get_thread_context(thread_ts)

                    # Create event with full thread context
                    events.append({
                        "source": "slack",
                        "type": "mention",
                        "ts": message["ts"],
                        "channel": self.target_channel,
                        "user": message.get("user", "unknown"),
                        "text": msg_text,
                        "thread_ts": thread_ts,
                        "thread_context": thread_context,  # CRITICAL: Full conversation context
                        "timestamp": datetime.fromtimestamp(float(message["ts"])).isoformat(),
                    })

            return events

        except Exception as e:
            print(f"❌ Error polling thread {thread_ts}: {e}")
            return []

    def poll_for_mentions(self) -> List[Dict[str, Any]]:
        """
        Poll Slack for new mentions
        Returns list of events for EventQueue
        """
        headers = {"Authorization": f"Bearer {self.slack_token}"}

        # Get messages since last processed
        last_ts = self.get_last_processed_ts()
        params = {"channel": self.target_channel, "limit": 100}  # Increased limit for catchup

        # ALWAYS poll at least the last hour to catch recent messages
        # This prevents missing messages if the service was down or database is stale
        one_hour_ago = time.time() - (1 * 3600)
        twenty_four_hours_ago = time.time() - (24 * 3600)

        # Use the MOST RECENT of: last_ts, one_hour_ago, or twenty_four_hours_ago
        if last_ts == 0:
            # Never run before - poll past 24 hours
            params["oldest"] = str(twenty_four_hours_ago)
            print(f"   ℹ️  First run - polling past 24 hours")
        elif last_ts < twenty_four_hours_ago:
            # Last check was >24h ago - poll past 24 hours
            params["oldest"] = str(twenty_four_hours_ago)
            print(f"   ℹ️  Stale timestamp detected - polling past 24 hours (last check: {datetime.fromtimestamp(last_ts).isoformat()})")
        elif last_ts < one_hour_ago:
            # Last check was between 1h-24h ago - poll from last_ts (normal catchup)
            params["oldest"] = str(last_ts)
            print(f"   ℹ️  Catching up from {datetime.fromtimestamp(last_ts).isoformat()}")
        else:
            # Last check was <1h ago - poll from last_ts (normal incremental)
            params["oldest"] = str(last_ts)

        try:
            response = requests.get(
                "https://slack.com/api/conversations.history",
                headers=headers,
                params=params,
                timeout=10,
            )

            if not response.json().get("ok"):
                print(f"❌ Slack API error: {response.json()}")
                return []

            messages = response.json().get("messages", [])
            events = []

            for message in messages:
                # Skip bot messages
                if message.get("bot_id") or message.get("user") == self.bot_user_id:
                    continue

                # Only process if message is newer than last processed
                if float(message["ts"]) <= last_ts:
                    continue

                # Check for direct bot mention
                msg_text = message.get("text", "")
                if f"<@{self.bot_user_id}>" in msg_text:
                    # Skip if already processed (prevents duplicate handling)
                    if self.is_processed(message["ts"]):
                        print(f"   ⏭️  Skipping already processed message {message['ts']}")
                        continue

                    # NOTE: Message is NOT marked as processed here - only after successful response
                    # This allows retries if Claude times out or errors

                    # Send immediate acknowledgment
                    thread_ts_for_reply = message.get("thread_ts") or message["ts"]
                    try:
                        self.send_response("👀 On it! Processing your request...", thread_ts=thread_ts_for_reply)
                        print(f"   ✅ Sent immediate acknowledgment (ts: {thread_ts_for_reply})")
                    except Exception as ack_error:
                        print(f"   ⚠️  Could not send acknowledgment: {ack_error}")

                    # Fetch thread context if this is in a thread
                    thread_context = None
                    if message.get("thread_ts"):
                        thread_context = self.get_thread_context(message["thread_ts"])
                        print(f"   📜 Fetched thread context: {len(thread_context.get('replies', []))} replies")

                    # Create event for EventQueue
                    events.append({
                        "source": "slack",
                        "type": "mention",
                        "ts": message["ts"],
                        "channel": self.target_channel,
                        "user": message.get("user", "unknown"),
                        "text": msg_text,
                        "thread_ts": message.get("thread_ts"),
                        "thread_context": thread_context,  # Include thread context for all mentions
                        "timestamp": datetime.fromtimestamp(float(message["ts"])).isoformat(),
                    })

            # Also check threads for any messages that have thread_ts
            # This catches replies to bot messages (like SLA violations)
            try:
                # Get unique thread_ts values from recent messages
                thread_timestamps = set()
                for msg in messages:
                    if msg.get("thread_ts"):
                        thread_timestamps.add(msg["thread_ts"])

                # ALSO poll ALL tracked threads from database (for ongoing conversations)
                with self.engine.connect() as conn:
                    rows = conn.execute(
                        text("SELECT thread_ts FROM slack_tracked_threads")
                    ).fetchall()
                    for row in rows:
                        thread_timestamps.add(row[0])

                print(f"   📊 Polling {len(thread_timestamps)} threads (recent + tracked)")

                # Poll each unique thread for mentions
                for thread_ts in thread_timestamps:
                    thread_events = self.poll_thread_replies(thread_ts)
                    events.extend(thread_events)

            except Exception as thread_error:
                print(f"⚠️  Error polling threads: {thread_error}")

            return events

        except Exception as e:
            print(f"❌ Slack polling error: {e}")
            return []

    def is_processed(self, ts: str) -> bool:
        """Check if message has already been processed."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM slack_processed_messages WHERE ts = :ts"),
                {"ts": ts},
            ).fetchone()
            return result is not None

    def mark_processed(self, ts: str, response: str = ""):
        """Mark message as processed in database."""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO slack_processed_messages (ts, channel, response, processed_at)
                    VALUES (:ts, :channel, :response, :now)
                    ON CONFLICT (ts) DO UPDATE SET
                        response = excluded.response
                """),
                {
                    "ts": ts,
                    "channel": self.target_channel,
                    "response": response[:1000],
                    "now": datetime.now().isoformat(),
                },
            )

    def send_response(self, text: str, thread_ts: Optional[str] = None) -> bool:
        """Send response to Slack"""
        headers = {"Authorization": f"Bearer {self.slack_token}"}

        payload = {"channel": self.target_channel, "text": text}

        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            response = requests.post(
                "https://slack.com/api/chat.postMessage", headers=headers, json=payload, timeout=10
            )

            result = response.json()
            if result.get("ok"):
                print("✅ Sent response to Slack")
                return True
            else:
                print(f"❌ Failed to send Slack response: {result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ Error sending Slack response: {e}")
            return False

    # DEPRECATED: process_with_claude() method removed
    # Now using unified orchestrator.process_mention() instead
    # See: src/orchestration/claude_code_orchestrator.py:process_mention()

    def post_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> bool:
        """Alias for send_response() - for compatibility with response_dispatcher"""
        return self.send_response(text, thread_ts)