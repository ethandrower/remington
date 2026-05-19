#!/usr/bin/env python3
"""
PM Agent Service - Hybrid Webhook + Polling Architecture

Combines:
1. FastAPI webhook server (for Jira/Bitbucket)
2. Slack polling monitor (for Slack mentions)
3. Shared orchestrator for all events

Architecture:
┌─────────────────────────────────────┐
│  PM Agent Service                   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  FastAPI Webhook Server     │   │  ← Jira/Bitbucket push events
│  │  (Port 8000)                │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│             v                       │
│  ┌─────────────────────────────┐   │
│  │  Orchestrator (Shared)      │   │  ← Processes all events
│  └──────────▲──────────────────┘   │
│             │                       │
│  ┌──────────┴──────────────────┐   │
│  │  Slack Monitor (Polling)    │   │  ← Polls Slack every 15s
│  │  Background Thread          │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
"""

import sys
import os
import threading
import time
import signal
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitors.slack_monitor import SlackMonitor
from src.monitors.jira_monitor import JiraMonitor
from src.monitors.bitbucket_monitor import BitbucketMonitor
from src.orchestration.claude_code_orchestrator import ClaudeCodeOrchestrator
from src.utils.slack_logger import get_slack_logger
from src.agents import run_agent, run_agent_oneshot
from src.utils.checkpoint_cleanup import cleanup_old_checkpoints
from src.config import get_jira_base_url


class PMAgentService:
    """Unified service running webhooks (primary) + polling (backup)"""

    def __init__(self):
        self.instance_id = os.getenv("INSTANCE_ID", "local")

        print("\n" + "="*70)
        print(f" 🤖 Autonomous PM Agent Service [{self.instance_id}] ".center(70))
        print("="*70)
        print("\nInitializing hybrid webhook + polling architecture...\n")
        print("Strategy:")
        print("  - Webhooks: Primary (instant response)")
        print("  - Polling: Backup (catches missed events)")
        print(f"  - Instance: {self.instance_id}\n")

        self.running = False
        self.threads = []

        # Initialize Slack logger (for activity logging to #pm-agent-logs)
        try:
            self.slack_logger = get_slack_logger()
            print("✅ Slack logger initialized\n")
        except Exception as e:
            print(f"⚠️  Slack logger not initialized: {e}")
            print("   Activity logging to Slack will be disabled\n")
            self.slack_logger = None

        # Initialize Claude Code orchestrator (with full .claude/ context)
        try:
            self.orchestrator = ClaudeCodeOrchestrator()
        except ValueError as e:
            print(f"❌ Failed to initialize Claude Code orchestrator: {e}")
            print("\nFalling back to simple orchestrator...")
            # Fallback to simple orchestrator if Claude Code not available
            try:
                from src.orchestration.simple_orchestrator import SimpleOrchestrator
                self.orchestrator = SimpleOrchestrator()
                print("✅ Simple orchestrator initialized (limited functionality)\n")
            except Exception as e2:
                print(f"❌ Failed to initialize any orchestrator: {e2}")
                sys.exit(1)

        # Initialize Slack monitor (polling only - no webhook support)
        try:
            self.slack_monitor = SlackMonitor()
            # Override to 15 seconds for Slack (no webhook alternative)
            print("")
        except ValueError as e:
            print(f"⚠️  Slack monitor not initialized: {e}")
            print("   Slack polling will be disabled\n")
            self.slack_monitor = None

        # Initialize Jira monitor
        try:
            self.jira_monitor = JiraMonitor()
            # Default 60s — configurable via JIRA_POLL_INTERVAL in .env
            self.jira_monitor.polling_interval = int(os.getenv("JIRA_POLL_INTERVAL", "60"))
            print(f"   🔄 Jira polling interval: {self.jira_monitor.polling_interval}s\n")
        except ValueError as e:
            print(f"⚠️  Jira monitor not initialized: {e}")
            print("   Jira backup polling will be disabled\n")
            self.jira_monitor = None

        # Initialize Bitbucket monitor (backup polling - webhooks are primary)
        try:
            self.bitbucket_monitor = BitbucketMonitor()
            # Override to 1 hour for backup polling
            self.bitbucket_monitor.polling_interval = int(os.getenv("BITBUCKET_BACKUP_POLL_INTERVAL", "3600"))
            print(f"   🔄 Bitbucket backup polling: {self.bitbucket_monitor.polling_interval}s (webhooks are primary)\n")
        except ValueError as e:
            print(f"⚠️  Bitbucket monitor not initialized: {e}")
            print("   Bitbucket backup polling will be disabled\n")
            self.bitbucket_monitor = None

    def start_slack_polling(self):
        """Start Slack polling in background thread (primary - no webhook alternative)"""
        if not self.slack_monitor:
            print("⏭️  Skipping Slack polling (not configured)")
            return

        def poll_loop():
            print("🔄 Starting Slack polling thread (primary)...")
            poll_interval = self.slack_monitor.polling_interval

            while self.running:
                try:
                    # Poll for new mentions
                    events = self.slack_monitor.poll_for_mentions()

                    # Log polling activity
                    from src.activity_tracker import get_tracker
                    get_tracker().log("polling_slack", f"Polled Slack, found {len(events)} mentions")

                    # Process each event with orchestrator (same workflow as Jira)
                    for event in events:
                        try:
                            print(f"\n{'='*60}")
                            print("📥 SLACK MENTION DETECTED")
                            print(f"{'='*60}")
                            print(f"User: {event['user']}")
                            print(f"Message: {event['text'][:100]}...")
                            if event.get('thread_context'):
                                print(f"Thread Context: {len(event['thread_context'].get('replies', []))} replies")
                            print(f"{'='*60}\n")

                            # Get message text (remove bot mention for cleaner processing)
                            message_text = event.get('text', '')
                            message_text = message_text.replace(f"<@{self.slack_monitor.bot_user_id}>", "").strip()

                            # Source ID for tracking (use thread_ts if available, otherwise message ts)
                            source_id = event.get('thread_ts') or event.get('ts')

                            # FIRST: Check if this is a response to a pending PM request
                            from src.database.pm_requests_db import get_pm_requests_db
                            pm_db = get_pm_requests_db()
                            pending_request = pm_db.get_request_by_source('slack', source_id)

                            if pending_request and pending_request['status'] == 'pending':
                                # This thread has a pending PM request - check for approval response
                                print(f"📋 Checking for approval response (pending request: {pending_request['request_id'][:8]}...)")

                                approval_response = self.orchestrator.parse_approval_response(message_text)

                                if approval_response['response_type']:
                                    # Handle approval/changes/cancel
                                    print(f"✅ APPROVAL RESPONSE DETECTED: {approval_response['response_type']}")
                                    request_id = pending_request['request_id']

                                    if approval_response['response_type'] == 'approved':
                                        result = self.orchestrator.handle_pm_approval(request_id)
                                        if result['success']:
                                            response = f"✅ Created Jira ticket: {result.get('jira_ticket_key')}\n{result.get('jira_url', '')}"
                                            print(f"   ✅ Created Jira ticket: {result.get('jira_ticket_key')}")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Ticket Created",
                                                    f"Created {result.get('jira_ticket_key')} from approved PM request (Slack)",
                                                    link=result.get('jira_url')
                                                )
                                        else:
                                            response = f"❌ Failed to create ticket: {result.get('error')}"
                                            print(f"   ❌ Failed to create ticket: {result.get('error')}")

                                    elif approval_response['response_type'] == 'changes':
                                        feedback = approval_response.get('feedback', '')
                                        result = self.orchestrator.handle_pm_revision(request_id, feedback)
                                        if result['success']:
                                            response = f"✅ Generated revision {result.get('revision_number')} based on your feedback. Please review the updated draft in this thread."
                                            print(f"   ✅ Generated revision {result.get('revision_number')}")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Draft Revised",
                                                    f"Generated revision {result.get('revision_number')} for Slack thread {source_id}"
                                                )
                                        else:
                                            response = f"❌ Failed to generate revision: {result.get('error')}"
                                            print(f"   ❌ Failed to generate revision: {result.get('error')}")

                                    elif approval_response['response_type'] == 'cancel':
                                        result = self.orchestrator.handle_pm_cancellation(request_id)
                                        if result['success']:
                                            response = "✅ PM request cancelled."
                                            print(f"   ✅ Cancelled PM request")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Request Cancelled",
                                                    f"User cancelled PM request via Slack thread {source_id}"
                                                )
                                        else:
                                            response = f"❌ Failed to cancel: {result.get('error')}"
                                            print(f"   ❌ Failed to cancel: {result.get('error')}")

                                    # Send response back to Slack
                                    thread_ts = event.get('thread_ts') or event.get('ts')
                                    self.slack_monitor.send_response(response, thread_ts=thread_ts)
                                    continue  # Skip further processing

                            # LangGraph agent: conversation history is managed automatically
                            # via the per-thread checkpointer — no manual context assembly needed.
                            print("🤖 Processing with LangGraph agent...")

                            thread_ts = event.get('thread_ts') or event.get('ts')
                            response = run_agent(
                                thread_ts=thread_ts,
                                channel=event.get('channel', self.slack_monitor.target_channel),
                                author=event.get('user', 'Unknown'),
                                message=message_text,
                            )

                            # Send response back to Slack
                            success = self.slack_monitor.send_response(response, thread_ts=thread_ts)

                            if success:
                                print(f"✅ Response sent to Slack thread {thread_ts}")

                                # Mark as processed (only after successful response)
                                self.slack_monitor.mark_processed(event['ts'], response=response[:100])
                                print(f"   ✅ Marked message {event['ts']} as processed")

                                # Register this thread for continued polling
                                self.slack_monitor.register_thread(thread_ts, context=f"Request from {event.get('user')}")

                                # Log to activity tracker
                                if self.slack_logger:
                                    try:
                                        self.slack_logger.post_activity(
                                            "Slack Mention Processed",
                                            f"Responded to @mention from {event.get('user')}",
                                            link=f"https://slack.com/archives/{event['channel']}/p{source_id.replace('.', '')}"
                                        )
                                    except Exception as log_err:
                                        print(f"   ⚠️  Could not log to activity tracker: {log_err}")
                            else:
                                print(f"❌ Failed to send response to Slack - NOT marking as processed (will retry)")

                        except Exception as e:
                            print(f"❌ Error processing Slack event: {e}")
                            import traceback
                            traceback.print_exc()

                except Exception as e:
                    print(f"❌ Error in Slack polling: {e}")
                    import traceback
                    traceback.print_exc()

                # Wait before next poll
                time.sleep(poll_interval)

            print("🛑 Slack polling thread stopped")

        # Start polling thread
        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Slack polling started (interval: {self.slack_monitor.polling_interval}s)\n")

    def start_jira_polling(self):
        """Start Jira backup polling in background thread"""
        if not self.jira_monitor:
            print("⏭️  Skipping Jira backup polling (not configured)")
            return

        def poll_loop():
            print("🔄 Starting Jira backup polling thread...")
            poll_interval = self.jira_monitor.polling_interval

            while self.running:
                try:
                    # Poll for new mentions
                    events = self.jira_monitor.poll_for_mentions()

                    # Log polling activity
                    from src.activity_tracker import get_tracker
                    get_tracker().log("polling_jira", f"Polled Jira, found {len(events)} comments")

                    if events:
                        print(f"\n🔍 Jira polling found {len(events)} new mention(s)")

                    # Process each event with orchestrator
                    for event in events:
                        try:
                            print(f"\n{'='*60}")
                            print("📥 JIRA MENTION DETECTED (via backup polling)")
                            print(f"{'='*60}")
                            print(f"Issue: {event['issue_key']}")
                            comment_text = event.get('comment_text', event.get('text', ''))
                            comment_preview = comment_text[:100]
                            print(f"Comment: {comment_preview}...")
                            print(f"{'='*60}\n")

                            # FIRST: Check if this is a response to a pending PM request
                            from src.database.pm_requests_db import get_pm_requests_db
                            pm_db = get_pm_requests_db()
                            pending_request = pm_db.get_request_by_source('jira', event['issue_key'])

                            if pending_request and pending_request['status'] == 'pending':
                                # This issue has a pending PM request - check for approval response
                                print(f"📋 Checking for approval response (pending request: {pending_request['request_id'][:8]}...)")

                                approval_response = self.orchestrator.parse_approval_response(comment_text)

                                if approval_response['response_type']:
                                    # Handle approval/changes/cancel
                                    print(f"✅ APPROVAL RESPONSE DETECTED: {approval_response['response_type']}")
                                    request_id = pending_request['request_id']

                                    if approval_response['response_type'] == 'approved':
                                        result = self.orchestrator.handle_pm_approval(request_id)
                                        if result['success']:
                                            print(f"   ✅ Created Jira ticket: {result.get('jira_ticket_key')}")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Ticket Created",
                                                    f"Created {result.get('jira_ticket_key')} from approved PM request",
                                                    link=f"{get_jira_base_url()}/browse/{result.get('jira_ticket_key')}"
                                                )
                                        else:
                                            print(f"   ❌ Failed to create ticket: {result.get('error')}")

                                    elif approval_response['response_type'] == 'changes':
                                        feedback = approval_response.get('feedback', '')
                                        result = self.orchestrator.handle_pm_revision(request_id, feedback)
                                        if result['success']:
                                            print(f"   ✅ Generated revision {result.get('revision_number')}")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Draft Revised",
                                                    f"Generated revision {result.get('revision_number')} for {event['issue_key']}"
                                                )
                                        else:
                                            print(f"   ❌ Failed to generate revision: {result.get('error')}")

                                    elif approval_response['response_type'] == 'cancel':
                                        result = self.orchestrator.handle_pm_cancellation(request_id)
                                        if result['success']:
                                            print(f"   ✅ Cancelled PM request")
                                            if self.slack_logger:
                                                self.slack_logger.post_activity(
                                                    "PM Request Cancelled",
                                                    f"User cancelled PM request for {event['issue_key']}"
                                                )
                                        else:
                                            print(f"   ❌ Failed to cancel: {result.get('error')}")

                                    # Mark as processed
                                    self.jira_monitor.mark_processed(event['issue_key'], event.get('comment_id', ''))
                                    continue  # Skip further processing

                            # LangGraph agent: thread_id = Jira issue key so each ticket
                            # gets its own persistent conversation history.
                            print("🤖 Processing with LangGraph agent...")

                            # Build message with issue context so agent doesn't need
                            # an extra get_jira_ticket call for basic info.
                            issue_context = event.get('issue_context', {})
                            if issue_context:
                                ctx_header = (
                                    f"[Jira context: {event['issue_key']} — {issue_context.get('summary', '')}]\n"
                                    f"Status: {issue_context.get('status', '')} | "
                                    f"Priority: {issue_context.get('priority', '')} | "
                                    f"Assignee: {issue_context.get('assignee', 'Unassigned')}\n\n"
                                )
                                message_with_context = ctx_header + comment_text
                            else:
                                message_with_context = comment_text

                            response = run_agent_oneshot(
                                message=message_with_context,
                                author=event.get('author', 'Unknown'),
                                channel="jira",
                            )

                            # Post response back to Jira
                            if response and self.jira_monitor:
                                try:
                                    post_success = self.jira_monitor.add_comment(
                                        event['issue_key'],
                                        response
                                    )
                                    if post_success:
                                        print(f"   ✅ Posted response to Jira {event['issue_key']}")
                                    else:
                                        print(f"   ❌ Failed to post response to Jira {event['issue_key']}")
                                except Exception as post_err:
                                    print(f"   ❌ Error posting to Jira: {post_err}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"   ⚠️  No response to post or Jira monitor not available")

                            # Mark as processed
                            self.jira_monitor.mark_processed(event['issue_key'], event.get('comment_id', ''))

                            # Log to activity tracker
                            if self.slack_logger:
                                try:
                                    self.slack_logger.post_activity(
                                        "Jira Mention Processed",
                                        f"Responded to mention in {event['issue_key']}",
                                        link=event.get('issue_url', f"{get_jira_base_url()}/browse/{event['issue_key']}")
                                    )
                                except Exception as log_err:
                                    print(f"   ⚠️  Failed to log to Slack: {log_err}")

                        except Exception as e:
                            print(f"❌ Error processing Jira event: {e}")
                            import traceback
                            traceback.print_exc()

                            # Log error to Slack
                            if self.slack_logger:
                                try:
                                    self.slack_logger.post_error(
                                        "Jira Monitor",
                                        f"Failed to process Jira comment in {event.get('issue_key', 'unknown')}",
                                        details=str(e)[:200]
                                    )
                                except:
                                    pass  # Don't fail on logging failure

                except Exception as e:
                    print(f"❌ Error in Jira backup polling: {e}")
                    import traceback
                    traceback.print_exc()

                # Wait before next poll
                time.sleep(poll_interval)

            print("🛑 Jira backup polling thread stopped")

        # Start polling thread
        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Jira polling started (interval: {self.jira_monitor.polling_interval}s)\n")

    def start_bitbucket_polling(self):
        """Start Bitbucket backup polling in background thread"""
        if not self.bitbucket_monitor:
            print("⏭️  Skipping Bitbucket backup polling (not configured)")
            return

        def poll_loop():
            print("🔄 Starting Bitbucket backup polling thread...")
            poll_interval = self.bitbucket_monitor.polling_interval

            while self.running:
                try:
                    # Poll for new PR mentions
                    events = self.bitbucket_monitor.poll_pull_requests()

                    # Log polling activity
                    from src.activity_tracker import get_tracker
                    get_tracker().log("polling_bitbucket", f"Polled Bitbucket, found {len(events)} PR comments")

                    if events:
                        print(f"\n🔍 Bitbucket backup polling found {len(events)} event(s) (webhook may have missed these)")

                    # Process each event
                    for event in events:
                        try:
                            print(f"\n{'='*60}")
                            print("📥 BITBUCKET PR MENTION DETECTED (via backup polling)")
                            print(f"{'='*60}")
                            print(f"Repo: {event['repo']}")
                            print(f"PR: #{event['pr_id']}")
                            print(f"Comment: {event.get('comment_text', event.get('text', ''))[:100]}...")
                            print(f"{'='*60}\n")

                            # LangGraph agent: thread_id = repo+PR so each PR gets
                            # its own persistent conversation history.
                            print("🤖 Processing with LangGraph agent...")

                            # Prepend full PR context so the agent knows what it's working with
                            comment_text = event.get('comment_text', event.get('text', ''))
                            print(f"   📜 Fetching PR context for {event['repo']} PR#{event['pr_id']}...")
                            pr_context = self.bitbucket_monitor.get_pr_context(
                                event['repo'], event['pr_id']
                            )
                            print(f"   ✅ PR context fetched")
                            message_with_context = pr_context + comment_text

                            response = run_agent_oneshot(
                                message=message_with_context,
                                author=event.get('author', 'Unknown'),
                                channel="bitbucket",
                            )

                            # Post response back to Bitbucket PR
                            if response and self.bitbucket_monitor:
                                try:
                                    post_success = self.bitbucket_monitor.add_pr_comment(
                                        repo=event['repo'],
                                        pr_id=event['pr_id'],
                                        message=response
                                    )
                                    if post_success:
                                        print(f"   ✅ Posted response to Bitbucket PR #{event['pr_id']}")
                                        # Mark as processed only after successful response
                                        self.bitbucket_monitor.mark_processed(
                                            event['repo'], event['pr_id'], event.get('comment_id', '')
                                        )
                                    else:
                                        print(f"   ❌ Failed to post response to Bitbucket PR #{event['pr_id']}")
                                except Exception as post_err:
                                    print(f"   ❌ Error posting to Bitbucket: {post_err}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"   ⚠️  No response to post or Bitbucket monitor not available")

                            # Log to activity tracker
                            if self.slack_logger:
                                try:
                                    self.slack_logger.post_activity(
                                        "Bitbucket Mention Processed",
                                        f"Responded to @mention in {event['repo']} PR#{event['pr_id']}",
                                        link=event.get('pr_url', f"https://bitbucket.org/{self.bitbucket_monitor.workspace}/{event['repo']}/pull-requests/{event['pr_id']}")
                                    )
                                except Exception as log_err:
                                    print(f"   ⚠️  Failed to log to activity tracker: {log_err}")

                            print(f"   ✅ Processed Bitbucket mention")

                        except Exception as e:
                            print(f"❌ Error processing Bitbucket event: {e}")
                            import traceback
                            traceback.print_exc()

                    # Poll for PR updates that need review
                    try:
                        pr_updates = self.bitbucket_monitor.poll_for_pr_updates()

                        if pr_updates:
                            print(f"\n🔍 Found {len(pr_updates)} PR(s) with new commits needing review")

                        # Process each PR that needs review
                        for pr_event in pr_updates:
                            try:
                                print(f"\n{'='*60}")
                                print("📝 PR REVIEW TRIGGERED")
                                print(f"{'='*60}")
                                print(f"Repo: {pr_event['repo']}")
                                print(f"PR: #{pr_event['pr_id']} - {pr_event['pr_title']}")
                                print(f"Author: {pr_event['pr_author']}")
                                print(f"New Commit: {pr_event['latest_commit'][:8]}")
                                print(f"{'='*60}\n")

                                # Fetch full PR context (description, diff, comments, linked tickets)
                                print(f"   📜 Fetching PR context for review...")
                                pr_context = self.bitbucket_monitor.get_pr_context(
                                    pr_event['repo'], pr_event['pr_id']
                                )

                                # Run LangGraph agent to generate the review
                                review_message = (
                                    pr_context +
                                    f"This PR was just submitted for review. "
                                    f"Please do a thorough initial code review. Check for: bugs, "
                                    f"security issues, code quality, test coverage gaps, and adherence "
                                    f"to best practices. Be specific — reference file names and line "
                                    f"numbers where relevant. Post your review as a comment."
                                )

                                review_response = run_agent_oneshot(
                                    message=review_message,
                                    author="system",
                                    channel="bitbucket",
                                )

                                # Post review to Bitbucket
                                if review_response and self.bitbucket_monitor:
                                    self.bitbucket_monitor.add_pr_comment(
                                        repo=pr_event['repo'],
                                        pr_id=pr_event['pr_id'],
                                        message=review_response,
                                    )

                                # Mark commit as reviewed
                                self.bitbucket_monitor.mark_commit_reviewed(
                                    pr_event['repo'],
                                    pr_event['pr_id'],
                                    pr_event['latest_commit']
                                )

                                print(f"   ✅ PR review complete")

                                # Log to Slack
                                if self.slack_logger:
                                    try:
                                        pr_url = f"https://bitbucket.org/{os.getenv('BITBUCKET_WORKSPACE', 'workspace')}/{pr_event['repo']}/pull-requests/{pr_event['pr_id']}"
                                        self.slack_logger.post_activity(
                                            "PR Review",
                                            f"Reviewed PR #{pr_event['pr_id']} in {pr_event['repo']} by {pr_event['pr_author']}",
                                            link=pr_url
                                        )
                                    except Exception as log_err:
                                        print(f"   ⚠️  Failed to log to Slack: {log_err}")

                            except Exception as e:
                                print(f"❌ Error processing PR review: {e}")
                                import traceback
                                traceback.print_exc()

                                # Log error to Slack
                                if self.slack_logger:
                                    try:
                                        self.slack_logger.post_error(
                                            "Bitbucket Monitor",
                                            f"Failed to process PR #{pr_event.get('pr_id', 'unknown')} in {pr_event.get('repo', 'unknown')}",
                                            details=str(e)[:200]
                                        )
                                    except:
                                        pass  # Don't fail on logging failure

                    except Exception as e:
                        print(f"❌ Error polling for PR updates: {e}")
                        import traceback
                        traceback.print_exc()

                except Exception as e:
                    print(f"❌ Error in Bitbucket backup polling: {e}")
                    import traceback
                    traceback.print_exc()

                # Wait before next poll
                time.sleep(poll_interval)

            print("🛑 Bitbucket backup polling thread stopped")

        # Start polling thread
        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Bitbucket backup polling started (interval: {self.bitbucket_monitor.polling_interval}s)\n")

    def start_sla_monitoring(self):
        """Start SLA monitoring in background thread (runs hourly)"""
        def sla_loop():
            print("🔄 Starting SLA monitoring thread...")
            check_interval = 3600  # 1 hour

            while self.running:
                try:
                    import subprocess
                    from pathlib import Path

                    print(f"\n{'='*60}")
                    print("🔍 SLA MONITORING CHECK")
                    print(f"{'='*60}")
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"{'='*60}\n")

                    # Run SLA check script
                    scripts_dir = Path(__file__).parent.parent / "scripts"
                    sla_script = scripts_dir / "core" / "sla_check_working.py"

                    if sla_script.exists():
                        result = subprocess.run(
                            ["python3", str(sla_script)],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )

                        if result.returncode == 0:
                            print(result.stdout)
                            print("   ✅ SLA check completed")
                        else:
                            print(f"   ❌ SLA check failed: {result.stderr}")
                    else:
                        print(f"   ⚠️  SLA script not found: {sla_script}")

                except Exception as e:
                    print(f"❌ Error in SLA monitoring: {e}")
                    import traceback
                    traceback.print_exc()

                # Wait before next check
                time.sleep(check_interval)

            print("🛑 SLA monitoring thread stopped")

        # Start SLA thread
        thread = threading.Thread(target=sla_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ SLA monitoring started (interval: 1 hour)\n")

    def start_daily_standup(self):
        """Start daily standup workflow (runs weekdays at 9 AM)"""
        def standup_loop():
            print("🔄 Starting daily standup thread...")
            from datetime import datetime, time as dt_time
            import pytz

            # Get timezone from env or default to America/New_York
            tz_name = os.getenv("BUSINESS_TIMEZONE", "America/New_York")
            tz = pytz.timezone(tz_name)

            last_run_date = None

            while self.running:
                try:
                    now = datetime.now(tz)
                    current_date = now.date()

                    # Check if it's a weekday (Monday=0, Sunday=6)
                    if now.weekday() < 5:  # Monday-Friday
                        # Check if it's 9 AM hour and we haven't run today
                        if now.hour == 9 and last_run_date != current_date:
                            import subprocess
                            from pathlib import Path

                            print(f"\n{'='*60}")
                            print("📊 DAILY STANDUP WORKFLOW")
                            print(f"{'='*60}")
                            print(f"Date: {current_date}")
                            print(f"Time: {now.strftime('%H:%M:%S %Z')}")
                            print(f"{'='*60}\n")

                            # Run standup workflow script
                            scripts_dir = Path(__file__).parent.parent / "scripts"
                            standup_script = scripts_dir / "core" / "standup_workflow.py"

                            if standup_script.exists():
                                result = subprocess.run(
                                    ["python3", str(standup_script)],
                                    capture_output=True,
                                    text=True,
                                    timeout=600
                                )

                                if result.returncode == 0:
                                    print(result.stdout)
                                    print("   ✅ Daily standup completed")
                                else:
                                    print(f"   ❌ Daily standup failed: {result.stderr}")
                            else:
                                print(f"   ⚠️  Standup script not found: {standup_script}")

                            # Mark as run for today
                            last_run_date = current_date

                            # Log to Slack
                            if self.slack_logger:
                                try:
                                    self.slack_logger.post_activity(
                                        "Daily Standup Complete",
                                        f"Generated daily standup report for {current_date}",
                                        link="#ecd-standup"
                                    )
                                except Exception as log_err:
                                    print(f"   ⚠️  Failed to log to Slack: {log_err}")

                except Exception as e:
                    print(f"❌ Error in daily standup: {e}")
                    import traceback
                    traceback.print_exc()

                # Check every 5 minutes
                time.sleep(300)

            print("🛑 Daily standup thread stopped")

        # Start standup thread
        thread = threading.Thread(target=standup_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Daily standup scheduled (weekdays at 9 AM)\n")

    def start_blocked_ticket_monitoring(self):
        """Start blocked ticket analyzer — runs weekdays at 10 AM (after standup)"""
        def blocked_loop():
            print("🔄 Starting blocked ticket monitoring thread...")
            from datetime import datetime
            import pytz

            tz_name = os.getenv("BUSINESS_TIMEZONE", "America/New_York")
            tz = pytz.timezone(tz_name)
            last_run_date = None

            while self.running:
                try:
                    now = datetime.now(tz)
                    current_date = now.date()

                    if now.weekday() < 5 and now.hour == 10 and last_run_date != current_date:
                        import subprocess
                        from pathlib import Path

                        print(f"\n{'='*60}")
                        print("🔍 BLOCKED TICKET ANALYSIS")
                        print(f"{'='*60}")
                        print(f"Date: {current_date} | Time: {now.strftime('%H:%M:%S %Z')}")
                        print(f"{'='*60}\n")

                        result = subprocess.run(
                            ["python3", "-m", "scripts.core.blocked_ticket_analyzer"],
                            capture_output=True,
                            text=True,
                            timeout=300,
                            cwd=str(Path(__file__).parent.parent),
                        )
                        if result.returncode == 0:
                            print(result.stdout)
                            print("   ✅ Blocked ticket analysis completed")
                        else:
                            print(f"   ❌ Blocked ticket analysis failed: {result.stderr}")

                        last_run_date = current_date

                except Exception as e:
                    print(f"❌ Error in blocked ticket monitoring: {e}")
                    import traceback
                    traceback.print_exc()

                time.sleep(300)  # Check every 5 minutes

            print("🛑 Blocked ticket monitoring thread stopped")

        thread = threading.Thread(target=blocked_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Blocked ticket analysis scheduled (weekdays at 10 AM)\n")

    def start_weekly_timesheet(self):
        """Start weekly timesheet report — runs every Monday at 9:30 AM (after standup)"""
        def timesheet_loop():
            print("🔄 Starting weekly timesheet thread...")
            from datetime import datetime
            import pytz

            tz_name = os.getenv("BUSINESS_TIMEZONE", "America/New_York")
            tz = pytz.timezone(tz_name)
            last_run_date = None

            while self.running:
                try:
                    now = datetime.now(tz)
                    current_date = now.date()

                    # Only run on Mondays (weekday() == 0) at 9:30 AM
                    if now.weekday() == 0 and now.hour == 9 and now.minute >= 30 and last_run_date != current_date:
                        import subprocess
                        from pathlib import Path

                        print(f"\n{'='*60}")
                        print("📋 WEEKLY TIMESHEET REPORT")
                        print(f"{'='*60}")
                        print(f"Date: {current_date} | Time: {now.strftime('%H:%M:%S %Z')}")
                        print(f"{'='*60}\n")

                        script = Path(__file__).parent.parent / "scripts" / "core" / "timesheet_report.py"
                        result = subprocess.run(
                            ["python3", str(script)],
                            capture_output=True,
                            text=True,
                            timeout=300,
                            cwd=str(Path(__file__).parent.parent),
                        )

                        if result.returncode == 0:
                            print(result.stdout)
                            print("   ✅ Weekly timesheet completed")
                        else:
                            print(f"   ❌ Weekly timesheet failed:\n{result.stderr}")

                        # Run DB cleanup after timesheet each week
                        try:
                            cleanup_script = Path(__file__).parent.parent / "scripts" / "core" / "db_cleanup.py"
                            cleanup_result = subprocess.run(
                                ["python3", str(cleanup_script)],
                                capture_output=True,
                                text=True,
                                timeout=120,
                                cwd=str(Path(__file__).parent.parent),
                            )
                            if cleanup_result.returncode == 0:
                                print(cleanup_result.stdout)
                                print("   ✅ DB cleanup completed")
                            else:
                                print(f"   ⚠️  DB cleanup failed:\n{cleanup_result.stderr}")
                        except Exception as ce:
                            print(f"   ⚠️  DB cleanup error: {ce}")

                        last_run_date = current_date

                except Exception as e:
                    print(f"❌ Error in weekly timesheet: {e}")
                    import traceback
                    traceback.print_exc()

                time.sleep(300)  # Check every 5 minutes

            print("🛑 Weekly timesheet thread stopped")

        thread = threading.Thread(target=timesheet_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Weekly timesheet scheduled (Mondays at 9:30 AM)\n")

    def start_hourly_heartbeat(self):
        """Start hourly heartbeat logging (shows agent is alive and what it's monitoring)"""
        def heartbeat_loop():
            print("🔄 Starting hourly heartbeat thread...")
            heartbeat_interval = 3600  # 1 hour

            while self.running:
                try:
                    from datetime import datetime

                    print(f"\n{'='*60}")
                    print("💓 HOURLY HEARTBEAT")
                    print(f"{'='*60}")
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"{'='*60}\n")

                    # Query activity database for real metrics
                    from src.activity_tracker import get_tracker
                    import pytz
                    tracker = get_tracker()

                    # Generate heartbeat message with scheduled task status
                    heartbeat_msg = f"💓 *PM Agent Heartbeat* - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

                    # Show scheduled tasks status
                    heartbeat_msg += "📅 *Scheduled Tasks:*\n"

                    # 1. SLA Check (hourly)
                    sla_check = tracker.get_last_activity_details("sla_check")
                    if sla_check:
                        sla_time = datetime.fromisoformat(sla_check['timestamp'])
                        time_ago = (datetime.now() - sla_time).total_seconds() / 60
                        # Show in hours if > 60 minutes
                        if abs(time_ago) >= 60:
                            heartbeat_msg += f"• ⏰ *SLA Check*: {abs(time_ago)/60:.1f}h ago - {sla_check.get('details', 'No details')}\n"
                        else:
                            heartbeat_msg += f"• ⏰ *SLA Check*: {abs(int(time_ago))}m ago - {sla_check.get('details', 'No details')}\n"
                    else:
                        heartbeat_msg += f"• ⏰ *SLA Check*: Never run\n"

                    # 2. Daily Standup (weekdays at 9 AM)
                    standup = tracker.get_last_activity_details("standup_report")
                    tz = pytz.timezone(os.getenv("BUSINESS_TIMEZONE", "America/New_York"))
                    now = datetime.now(tz)
                    if standup:
                        standup_time = datetime.fromisoformat(standup['timestamp'])
                        hours_ago = (datetime.now() - standup_time).total_seconds() / 3600
                        heartbeat_msg += f"• 📊 *Daily Standup*: {hours_ago:.0f}h ago - {standup.get('details', 'No details')}\n"
                    else:
                        # Show next scheduled time
                        next_standup = "Tomorrow 9 AM" if now.hour >= 9 else "Today 9 AM"
                        if now.weekday() >= 5:  # Weekend
                            next_standup = "Monday 9 AM"
                        heartbeat_msg += f"• 📊 *Daily Standup*: Scheduled for {next_standup} (weekdays only)\n"

                    # 3. Continuous monitors
                    heartbeat_msg += f"\n🔄 *Continuous Monitors:*\n"
                    heartbeat_msg += f"• Slack: 15s polling\n"
                    heartbeat_msg += f"• Jira: 30s polling\n"
                    heartbeat_msg += f"• Bitbucket: 30s polling\n"

                    # Show recent activity counts
                    activity_summary = tracker.get_recent_summary(hours=1)
                    if activity_summary:
                        heartbeat_msg += f"\n📈 *Last Hour Activity:*\n"
                        # Show top 5 activities to prove monitors are working
                        for key, count in sorted(activity_summary.items(), key=lambda x: x[1], reverse=True)[:5]:
                            if count > 0 and key != 'heartbeat':  # Skip heartbeat itself
                                label = key.replace('_', ' ').title()
                                heartbeat_msg += f"• {label}: {count}\n"

                    heartbeat_msg += f"\n🟢 All systems operational"

                    # Log this heartbeat to activity tracker
                    tracker.log("heartbeat", f"Posted heartbeat with {len(activity_summary)} activity types")

                    # Log to Slack
                    if self.slack_logger:
                        try:
                            self.slack_logger.post_activity(
                                "Heartbeat",
                                heartbeat_msg,
                                link=None
                            )
                            print("   ✅ Heartbeat logged to Slack")
                        except Exception as log_err:
                            print(f"   ⚠️  Failed to log heartbeat: {log_err}")

                except Exception as e:
                    print(f"❌ Error in heartbeat: {e}")
                    import traceback
                    traceback.print_exc()

                # Wait before next heartbeat
                time.sleep(heartbeat_interval)

            print("🛑 Heartbeat thread stopped")

        # Start heartbeat thread
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Hourly heartbeat started\n")

    def start_checkpoint_cleanup(self):
        """
        Prune langgraph_agent checkpoint tables older than the retention window.

        Runs once at startup (catches anything that accumulated while down) and
        then every 24h. Retention is configurable via CHECKPOINT_RETENTION_DAYS
        (default 30). One thread total; cheap SQL deletes — no app-level locks.
        """
        retention_days = int(os.getenv("CHECKPOINT_RETENTION_DAYS", "30"))
        interval_seconds = 24 * 60 * 60

        def cleanup_loop():
            print(f"🧹 Checkpoint cleanup thread started (retention: {retention_days} days)")
            # Small delay so we don't race the rest of startup logging.
            time.sleep(60)

            while self.running:
                try:
                    deleted = cleanup_old_checkpoints(retention_days=retention_days)
                    if deleted:
                        total = sum(deleted.values())
                        print(
                            f"🧹 Checkpoint cleanup: pruned {total} rows "
                            f"({deleted})"
                        )
                    else:
                        print("🧹 Checkpoint cleanup: nothing to prune")
                except Exception as e:
                    print(f"❌ Checkpoint cleanup failed: {e}")
                    import traceback
                    traceback.print_exc()

                # Sleep in small chunks so shutdown is responsive.
                for _ in range(interval_seconds // 30):
                    if not self.running:
                        break
                    time.sleep(30)

            print("🛑 Checkpoint cleanup thread stopped")

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        self.threads.append(thread)
        print(f"✅ Checkpoint cleanup started (every 24h, retention {retention_days} days)\n")

    def start_webhook_server(self):
        """Start FastAPI webhook server"""
        # Use Heroku's dynamic PORT or default to 8001 for local dev
        port = int(os.getenv('PORT', 8001))

        print(f"🚀 Starting webhook server on port {port}...")
        print("   Endpoints:")
        print("   - POST /webhooks/jira")
        print("   - POST /webhooks/bitbucket")
        print("   - POST /webhooks/slack")
        print("   - GET  /health")
        print("   - GET  /docs\n")

        # Import and run FastAPI app using import string
        # This prevents duplicate orchestrator initialization and avoids uvicorn warnings
        import uvicorn

        # Run server (this blocks)
        uvicorn.run(
            "src.web.app:app",  # Use import string instead of importing app object
            host="0.0.0.0",
            port=port,
            log_level="info"
        )

    def start(self):
        """Start all services"""
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        print("="*70)
        print(" 🟢 PM Agent Service Starting ".center(70))
        print("="*70)
        print()

        # Start all polling threads in background
        print("Starting background polling threads...\n")
        self.start_slack_polling()              # Primary (15s) - no webhook alternative
        self.start_jira_polling()               # Backup (30s) - webhooks are primary (also checks for PM approvals)
        self.start_bitbucket_polling()          # Backup (30s) - webhooks are primary
        self.start_sla_monitoring()             # SLA checks (1 hour)
        self.start_daily_standup()              # Daily standup (weekdays 9 AM)
        self.start_blocked_ticket_monitoring()  # Blocked ticket analysis (weekdays 10 AM)
        self.start_weekly_timesheet()           # Weekly timesheet report (Mondays 9:30 AM)
        self.start_hourly_heartbeat()           # Heartbeat logging (1 hour)
        self.start_checkpoint_cleanup()         # Prune old agent checkpoints (24h)

        print("="*70)
        print(" Polling Threads Active ".center(70))
        print("="*70)
        print()

        # Start webhook server (blocks)
        try:
            self.start_webhook_server()
        except KeyboardInterrupt:
            self._handle_shutdown(None, None)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        print("\n\n" + "="*70)
        print(" 🛑 Shutting down PM Agent Service ".center(70))
        print("="*70)

        self.running = False

        # Wait for threads
        for thread in self.threads:
            thread.join(timeout=2)

        print("\n✅ Shutdown complete\n")
        sys.exit(0)


if __name__ == "__main__":
    service = PMAgentService()
    service.start()
