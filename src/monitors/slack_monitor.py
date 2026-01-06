#!/usr/bin/env python3
"""
Slack Monitor - Polls Slack for service account mentions
"""

import os
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests


class SlackMonitor:
    """Polls Slack for bot mentions and generates events"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
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

        # Database for tracking processed messages
        self.db_path = Path(".claude/data/bot-state/slack_state.db")
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
        """Initialize database to track processed messages and monitored threads"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    ts TEXT PRIMARY KEY,
                    channel TEXT,
                    user_id TEXT,
                    text TEXT,
                    response TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Track threads we need to monitor for replies (SLA violations, etc.)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_threads (
                    thread_ts TEXT PRIMARY KEY,
                    channel TEXT,
                    context TEXT,
                    last_checked_ts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Track SLA alerts to prevent duplicate notifications within 24 hours
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sla_alerts (
                    violation_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    last_alerted_at TIMESTAMP NOT NULL,
                    alert_count INTEGER DEFAULT 1,
                    current_escalation_level INTEGER DEFAULT 1,
                    slack_thread_ts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster SLA alert lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_item_id_type
                ON sla_alerts(item_id, violation_type)
            """)

        print(f"✅ Slack database ready at {self.db_path}")

    def get_last_processed_ts(self) -> float:
        """Get timestamp of last processed message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT MAX(ts) FROM processed_messages WHERE channel = ?",
                (self.target_channel,),
            )
            result = cursor.fetchone()[0]
            return float(result) if result else 0.0

    def register_thread(self, thread_ts: str, context: str = ""):
        """Register a thread to monitor for replies (e.g., SLA violations)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tracked_threads
                (thread_ts, channel, context, last_checked_ts)
                VALUES (?, ?, ?, ?)
                """,
                (thread_ts, self.target_channel, context, "0"),
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT last_checked_ts FROM tracked_threads WHERE thread_ts = ?",
                (thread_ts,),
            )
            row = cursor.fetchone()
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

                # DEBUG: Log message details to diagnose bot loop
                msg_user = message.get("user")
                msg_bot_id = message.get("bot_id")
                msg_text_preview = message.get("text", "")[:50]
                print(f"   🐛 DEBUG: msg ts={message.get('ts')}, user={msg_user}, bot_id={msg_bot_id}, text={msg_text_preview}")

                if message.get("bot_id") or message.get("user") == self.bot_user_id:
                    print(f"   ⏭️  Skipping bot message (user={msg_user}, bot_id={msg_bot_id})")
                    continue

                # Only process if message is newer than last checked
                if float(message["ts"]) <= last_checked:
                    continue

                # Check for bot mention
                text = message.get("text", "")
                if f"<@{self.bot_user_id}>" in text:
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

                    # Update last_checked_ts for this thread (INSERT OR REPLACE to handle unregistered threads)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO tracked_threads
                            (thread_ts, channel, context, last_checked_ts)
                            VALUES (?, ?, ?, ?)
                            """,
                            (thread_ts, self.target_channel, f"Auto-tracked from reply", message["ts"]),
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
                        "text": text,
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
                text = message.get("text", "")
                if f"<@{self.bot_user_id}>" in text:
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
                        "text": text,
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
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT thread_ts FROM tracked_threads")
                    for row in cursor.fetchall():
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
        """Check if message has already been processed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT ts FROM processed_messages WHERE ts = ?",
                (ts,)
            )
            return cursor.fetchone() is not None

    def mark_processed(self, ts: str, response: str = ""):
        """Mark message as processed in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_messages
                (ts, channel, response)
                VALUES (?, ?, ?)
            """,
                (ts, self.target_channel, response[:1000]),
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

    def process_with_claude(self, event: Dict[str, Any], full_context: str = None) -> str:
        """
        Process Slack mention with Claude using local command
        (Maintains existing working_bot.py behavior)
        """
        user = event.get("user", "unknown")
        text = full_context or event.get("text", "")

        # Use full_context if provided (already has complete thread history)
        # Otherwise fall back to basic text
        context_display = text
        if full_context and full_context != text:
            context_display = full_context
        elif event.get('thread_context'):
            # Fallback: format thread context if full_context wasn't provided
            thread_ctx = event['thread_context']
            context_parts = []
            if thread_ctx.get('parent'):
                context_parts.append(f"[THREAD START]: {thread_ctx['parent']['text']}")
            if thread_ctx.get('replies'):
                for i, reply in enumerate(thread_ctx['replies']):  # Include ALL replies
                    context_parts.append(f"[Reply {i+1}]: {reply['text']}")
            if context_parts:
                context_display = "\n".join(context_parts)

        # Build action-oriented prompt
        prompt = f"""You are the AI project management assistant responding to a Slack message. You MUST take concrete actions using Python CLI tools and report back exactly what you did.

SLACK MESSAGE CONTEXT:
- User: {user}
- Channel: {channel_name if channel_name else "workspace"}
- Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

FULL CONVERSATION THREAD:
{context_display}

MANDATORY ACTION-FIRST WORKFLOW:

1. **IMMEDIATE TOOL USAGE REQUIRED** - You MUST use these Python tools based on message type:

   **For ANY message**: Start by searching Jira and Confluence for relevant content
   - Use searchJiraIssuesUsingJql with keywords from the user's message
   - Use searchConfluenceUsingCql to find related documentation

   **For Bug Reports**:
   - Search Jira for similar existing bugs
   - CREATE a new bug ticket using createJiraIssue with full details
   - Link to related issues if found

   **For Questions**:
   - Search Confluence for relevant documentation using searchConfluenceUsingCql
   - READ specific pages using getConfluencePage
   - Search Jira for related discussions/tickets

   **For Feature Requests**:
   - Search existing feature requests in Jira
   - CREATE new feature ticket using createJiraIssue if not duplicate
   - Add proper labels and components

   **For Ticket References (ECD-123, PM-456, etc.)**:
   - GET the specific ticket using getJiraIssue
   - UPDATE if requested using editJiraIssue
   - READ current status and provide details

2. **DOCUMENTATION ACTIONS**:
   - If user provides new info → UPDATE Confluence page using updateConfluencePage
   - If process unclear → CREATE documentation using createConfluencePage
   - If solution found → DOCUMENT in knowledge base

3. **MANDATORY RESPONSE FORMAT** - Structure your response in two parts:

**PART 1: CONVERSATIONAL ANSWER (Top - what users see first)**
Write 1-3 paragraphs in natural, friendly language directly answering the user's question or request. This should be clear, concise, and actionable without technical jargon.

Example:
"I checked PROJ-862 - it's currently in the 'In Progress' status and assigned to John Doe. The ticket was created on Dec 15th for implementing the new export feature. Based on the latest comment from yesterday, John is working on the backend API and expects to have a PR ready by end of week."

---

**PART 2: TECHNICAL DETAILS** _(optional - for troubleshooting)_

```
📋 DETAILED ACTION LOG

🎯 Actions Taken:
- [List every tool call made with specific details]
- [Include exact ticket numbers created/updated (e.g., "Created ECD-789")]
- [Include exact Confluence page titles accessed/updated]

🔍 Research Performed:
- [List specific Jira searches with JQL queries used]
- [List specific Confluence searches with keywords]
- [Include what was found and not found]

📋 Issues/Pages Referenced:
- [List specific ticket numbers and their current status]
- [List specific Confluence page titles and relevance]
- [Include direct links or identifiers]

📝 Documentation Updates:
- [Any Confluence pages created/updated with titles]
- [Any new knowledge captured]

➡️ Next Steps/Recommendations:
- [Specific actionable recommendations]
```

CRITICAL REQUIREMENTS:
- You MUST use Python tools - never respond without taking action
- You MUST provide specific ticket numbers (e.g., "ECD-123") when creating/referencing
- You MUST include exact Confluence page titles
- You MUST search before creating to avoid duplicates
- You MUST be specific about what tools you used and what results you got

AVAILABLE PYTHON CLI TOOLS (USE THESE ACTIVELY):

**Jira Tools:**
- python -m src.tools.jira.search "project = ECD AND status = 'In Progress'" --max-results 10
- python -m src.tools.jira.get_issue ECD-123
- python -m src.tools.jira.add_comment ECD-123 "Your comment text here"
- python -m src.tools.jira.edit_issue ECD-123 --summary "New summary" --priority "High"
- python -m src.tools.jira.list_projects --max-results 5
- python -m src.tools.jira.lookup_user "username"

**Confluence Tools:**
- python -m src.tools.confluence.search "keywords" --max-results 5
- python -m src.tools.confluence.get_page PAGE_ID
- python -m src.tools.confluence.create_page "Page Title" "Page content" SPACE_KEY
- python -m src.tools.confluence.update_page PAGE_ID "Updated content"

**Example Usage:**
```bash
# Search for tickets assigned to a developer
python -m src.tools.jira.search "assignee = john.doe AND status != Done" --max-results 10

# Get specific ticket details
python -m src.tools.jira.get_issue ECD-862

# Add a comment to a ticket
python -m src.tools.jira.add_comment ECD-862 "Updated priority per team discussion"
```

Remember: Your value is in DOING the work and providing specific evidence of what you accomplished. Use the tools actively and report concrete results with ticket numbers, page titles, and specific actions taken."""

        print("🤖 Processing Slack mention with Claude...")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🤖 Calling Claude (attempt {attempt + 1}/{max_retries}, timeout: 10 minutes)")

                result = subprocess.run(
                    [
                        "claude",
                        "-p",
                        "--output-format",
                        "text",
                        "--settings",
                        ".claude/settings.local.json",
                    ],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minutes timeout for complex MCP operations
                    cwd=str(Path(__file__).parent.parent.parent),  # Project root for full MCP access
                )

                if result.returncode == 0:
                    response = result.stdout.strip()
                    if response:
                        print(f"✅ Claude response received ({len(response)} chars)")
                        return response
                    else:
                        print("⚠️ Claude returned empty response")
                        return "I processed your request but didn't generate a response."
                else:
                    error_msg = result.stderr.strip()
                    print(f"❌ Claude error (code {result.returncode}): {error_msg}")
                    if attempt < max_retries - 1:
                        print("🔄 Retrying in 2 seconds...")
                        time.sleep(2)
                        continue
                    return "Sorry, I encountered an error processing your request. Please try rephrasing."

            except subprocess.TimeoutExpired:
                print(
                    f"⏱️ Claude timed out after 10 minutes (attempt {attempt + 1}/{max_retries})"
                )
                if attempt < max_retries - 1:
                    print("🔄 Retrying...")
                    time.sleep(5)
                    continue
                # After all retries failed - return user-friendly error
                # NOTE: Message is NOT marked processed, so it will retry on next poll
                return "⏳ Your request is taking longer than expected (10+ min timeout after 2 retries). This might be due to:\n" \
                       "• Complex Jira queries taking too long\n" \
                       "• Multiple MCP operations needed\n" \
                       "• System under heavy load\n\n" \
                       "💡 Try simplifying your request or I'll automatically retry on the next polling cycle."

            except FileNotFoundError:
                print("❌ Claude command not found - please ensure Claude Code is installed")
                return (
                    "Sorry, the Claude Code CLI is not available. Please contact the administrator."
                )

            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if attempt < max_retries - 1:
                    print("🔄 Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                return "Sorry, I encountered an unexpected error. Please try again later."

        # If we get here, all retries failed
        return "I'm unable to process your request right now. Please try again later."

    def post_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> bool:
        """Alias for send_response() - for compatibility with response_dispatcher"""
        return self.send_response(text, thread_ts)