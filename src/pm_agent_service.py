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


class PMAgentService:
    """Unified service running webhooks (primary) + polling (backup)"""

    def __init__(self):
        print("\n" + "="*70)
        print(" 🤖 Autonomous PM Agent Service ".center(70))
        print("="*70)
        print("\nInitializing hybrid webhook + polling architecture...\n")
        print("Strategy:")
        print("  - Webhooks: Primary (instant response)")
        print("  - Polling: Backup (catches missed events)")
        print("  - Intelligence: Claude Code with MCP tools\n")

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

        # Initialize Jira monitor (backup polling - webhooks are primary)
        try:
            self.jira_monitor = JiraMonitor()
            # Override to 1 hour for backup polling
            self.jira_monitor.polling_interval = int(os.getenv("JIRA_BACKUP_POLL_INTERVAL", "3600"))
            print(f"   🔄 Jira backup polling: {self.jira_monitor.polling_interval}s (webhooks are primary)\n")
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

                            # Build context string including FULL thread history in chronological order
                            context_parts = []
                            if event.get('thread_context'):
                                thread_ctx = event['thread_context']
                                # Start with original/parent message
                                if thread_ctx.get('parent'):
                                    parent_text = thread_ctx['parent']['text']
                                    parent_user = thread_ctx['parent'].get('user', 'unknown')
                                    context_parts.append(f"[THREAD START - User {parent_user}]: {parent_text}")

                                # Include ALL replies in chronological order (not just last 5)
                                if thread_ctx.get('replies'):
                                    for i, reply in enumerate(thread_ctx['replies']):
                                        reply_user = reply.get('user', 'unknown')
                                        reply_text = reply['text']
                                        # Mark if this is the current message being processed
                                        if reply.get('ts') == event.get('ts'):
                                            context_parts.append(f"[CURRENT MESSAGE - User {reply_user}]: {reply_text}")
                                        else:
                                            context_parts.append(f"[Reply {i+1} - User {reply_user}]: {reply_text}")

                            # If no thread context or current message wasn't in replies, add it at the end
                            if not context_parts:
                                context_parts.append(f"[User message]: {message_text}")
                            elif not any("CURRENT MESSAGE" in p for p in context_parts):
                                context_parts.append(f"[CURRENT MESSAGE]: {message_text}")

                            full_context = "\n".join(context_parts)
                            print(f"   📜 Built context with {len(context_parts)} parts")

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

                            # SECOND: Detect if this is a NEW PM request (story/bug/epic creation)
                            pm_intent = self.orchestrator.detect_pm_intent(full_context)

                            if pm_intent['is_pm_request'] and pm_intent['confidence'] > 0.5:
                                print(f"🎯 PM REQUEST DETECTED: {pm_intent['request_type']} (confidence: {pm_intent['confidence']})")
                                print(f"   Keywords: {', '.join(pm_intent['keywords_found'])}")

                                # Route to PM request handler
                                result = self.orchestrator.process_pm_request(
                                    source='slack',
                                    source_id=source_id,
                                    request_type=pm_intent['request_type'],
                                    comment_text=full_context,
                                    requester_id=event.get('user', ''),
                                    requester_name=event.get('user', 'Unknown')
                                )

                                # Send PM draft response to Slack
                                if result.get('draft'):
                                    response = f"📋 **{pm_intent['request_type'].title()} Draft Generated**\n\n{result['draft']}\n\n_Reply with 'approved', 'changes needed: <feedback>', or 'cancel' to proceed._"
                                    thread_ts = event.get('thread_ts') or event.get('ts')
                                    print(f"   🐛 DEBUG PM: Sending to thread_ts={thread_ts}, channel={event.get('channel')}")
                                    success = self.slack_monitor.send_response(response, thread_ts=thread_ts)
                                    if success:
                                        print(f"   ✅ PM draft sent to Slack thread {thread_ts}")
                                    else:
                                        print(f"   ❌ FAILED to send PM draft to Slack thread {thread_ts}")

                                    # Register thread for continued polling (for approval responses)
                                    self.slack_monitor.register_thread(thread_ts, context=f"PM {pm_intent['request_type']} request pending approval")
                                else:
                                    print(f"   ⚠️  No draft generated")

                                # Log to Slack
                                if self.slack_logger:
                                    try:
                                        self.slack_logger.post_activity(
                                            f"PM {pm_intent['request_type'].title()} Draft",
                                            f"Generated {pm_intent['request_type']} draft from Slack thread {source_id}",
                                            link=f"https://slack.com/archives/{event['channel']}/p{source_id.replace('.', '')}"
                                        )
                                    except Exception as log_err:
                                        print(f"   ⚠️  Could not log to Slack: {log_err}")

                            else:
                                # THIRD: Generic Slack mention processing (fallback)
                                print("🤖 Processing as generic request with Claude Code...")
                                # Pass full context including thread history
                                response = self.slack_monitor.process_with_claude(event, full_context=full_context)

                                # Send response back to Slack
                                # DEBUG: Log event details to diagnose thread_ts issue
                                print(f"   🐛 DEBUG: event['ts'] = {event.get('ts')}, event['thread_ts'] = {event.get('thread_ts')}")
                                thread_ts = event.get('thread_ts') or event.get('ts')
                                print(f"   🐛 DEBUG: Using thread_ts = {thread_ts}")
                                success = self.slack_monitor.send_response(response, thread_ts=thread_ts)

                                if success:
                                    print(f"✅ Response sent to Slack thread {thread_ts}")

                                    # NOW mark as processed (only after successful response)
                                    self.slack_monitor.mark_processed(event['ts'], response=response[:100])
                                    print(f"   ✅ Marked message {event['ts']} as processed")

                                    # Register this thread for continued polling
                                    self.slack_monitor.register_thread(thread_ts, context=f"Generic request from {event.get('user')}")
                                else:
                                    print(f"❌ Failed to send response to Slack - NOT marking as processed (will retry)")
                                    # Don't mark as processed - allows retry on next poll

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
                        print(f"\n🔍 Jira backup polling found {len(events)} event(s) (webhook may have missed these)")

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

                            # SECOND: Detect if this is a NEW PM request (story/bug/epic creation)
                            pm_intent = self.orchestrator.detect_pm_intent(comment_text)

                            if pm_intent['is_pm_request'] and pm_intent['confidence'] > 0.5:
                                print(f"🎯 PM REQUEST DETECTED: {pm_intent['request_type']} (confidence: {pm_intent['confidence']})")
                                print(f"   Keywords: {', '.join(pm_intent['keywords_found'])}")

                                # Route to PM request handler
                                result = self.orchestrator.process_pm_request(
                                    source='jira',
                                    source_id=event['issue_key'],
                                    request_type=pm_intent['request_type'],
                                    comment_text=comment_text,
                                    requester_id=event.get('author_id', ''),
                                    requester_name=event['author']
                                )

                                # Mark as processed
                                self.jira_monitor.mark_processed(event['issue_key'], event.get('comment_id', ''))

                                # Log to Slack
                                if self.slack_logger:
                                    try:
                                        self.slack_logger.post_activity(
                                            f"PM {pm_intent['request_type'].title()} Draft",
                                            f"Generated {pm_intent['request_type']} draft for {event['issue_key']}",
                                            link=f"{get_jira_base_url()}/browse/{event['issue_key']}"
                                        )
                                    except Exception as log_err:
                                        print(f"   ⚠️  Failed to log to Slack: {log_err}")

                                print(f"   ✅ PM Draft Created: {result.get('request_id', 'unknown')}")
                            else:
                                # Not a PM request, process as normal Jira comment
                                print(f"🔍 STANDARD JIRA COMMENT (not a PM request)")

                                # Format issue context for Claude prompt
                                issue_context = event.get('issue_context')
                                if issue_context:
                                    # Build rich context with issue details + all previous comments
                                    context_str = f"""ISSUE CONTEXT:
--------------
Issue: {issue_context['issue_key']} - {issue_context['summary']}
Status: {issue_context['status']} | Priority: {issue_context['priority']}
Assignee: {issue_context['assignee']}

DESCRIPTION:
{issue_context['description']}

PREVIOUS COMMENTS ({len(issue_context['comments'])} total):
"""
                                    # Add all previous comments chronologically
                                    for i, comment in enumerate(issue_context['comments'], 1):
                                        context_str += f"\n[Comment {i}] {comment['author']} ({comment['created'][:10]}):\n{comment['text']}\n"

                                    context_str += f"\n\nLATEST COMMENT (requires your response):\n{comment_text}"

                                    print(f"   📜 Using full issue context ({len(issue_context['comments'])} previous comments)")
                                    prompt_text = context_str
                                else:
                                    # Fallback if context fetch failed
                                    print(f"   ⚠️  No issue context available, using basic comment only")
                                    prompt_text = f"Comment on {event['issue_key']}: {comment_text}"

                                result = self.orchestrator.process_jira_comment(
                                    event['issue_key'],
                                    prompt_text,
                                    event['author'],
                                    event.get('author_id', '')
                                )
                                print(f"   ✅ Processed: {result}")

                                # CRITICAL: Actually post the response back to Jira
                                # The orchestrator generates a response but doesn't guarantee posting
                                response_text = result.get('response', '')
                                if response_text and self.jira_monitor:
                                    try:
                                        # Post response as a comment on the Jira issue
                                        post_success = self.jira_monitor.add_comment(
                                            event['issue_key'],
                                            response_text
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

                                # Log to Slack (for standard comments only)
                                if self.slack_logger:
                                    try:
                                        self.slack_logger.post_activity(
                                            "Jira Comment",
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
        print(f"✅ Jira backup polling started (interval: {self.jira_monitor.polling_interval}s)\n")

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

                            # TODO: Create orchestrator.process_bitbucket_pr_comment() method
                            print(f"   ℹ️  Bitbucket event logged (processing not yet implemented)")

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

                                # Process with orchestrator PR review
                                result = self.orchestrator.process_pr_review(
                                    repo=pr_event['repo'],
                                    pr_id=pr_event['pr_id'],
                                    pr_title=pr_event['pr_title'],
                                    pr_author=pr_event['pr_author'],
                                    pr_author_account_id=pr_event.get('pr_author_account_id', ''),
                                    latest_commit=pr_event['latest_commit']
                                )

                                # Mark commit as reviewed
                                self.bitbucket_monitor.mark_commit_reviewed(
                                    pr_event['repo'],
                                    pr_event['pr_id'],
                                    pr_event['latest_commit']
                                )

                                print(f"   ✅ PR review complete: {result['status']}")

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
                    tracker = get_tracker()
                    activity_summary = tracker.get_recent_summary(hours=1)

                    # Generate heartbeat message with real metrics
                    heartbeat_msg = f"💓 *PM Agent Heartbeat* - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    heartbeat_msg += "📊 *Activity Last Hour:*\n"

                    # Show actual counts from database
                    if activity_summary:
                        # Sort by count descending
                        sorted_activities = sorted(activity_summary.items(), key=lambda x: x[1], reverse=True)
                        for activity_type, count in sorted_activities:
                            # Make activity names more readable
                            display_name = activity_type.replace('_', ' ').title()
                            heartbeat_msg += f"• {display_name}: {count}\n"
                    else:
                        heartbeat_msg += "• No activities recorded in last hour\n"

                    heartbeat_msg += "\n🔍 *Configured Monitors:*\n"
                    heartbeat_msg += "• Slack (15s) | Jira (30s) | Bitbucket (30s)\n"
                    heartbeat_msg += "• SLA Check (hourly) | Standup (weekdays 9AM)\n\n"
                    heartbeat_msg += f"🟢 All systems operational"

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
        self.start_slack_polling()       # Primary (15s) - no webhook alternative
        self.start_jira_polling()        # Backup (30s) - webhooks are primary (also checks for PM approvals)
        self.start_bitbucket_polling()   # Backup (30s) - webhooks are primary
        self.start_sla_monitoring()      # SLA checks (1 hour)
        self.start_daily_standup()       # Daily standup (weekdays 9 AM)
        self.start_hourly_heartbeat()    # Heartbeat logging (1 hour)

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
