# CiteMed PM Agent - Slack + Atlassian Integration Plan

**Created:** 2025-10-19
**Status:** Research Complete - Ready for Implementation
**Goal:** Unified bot service monitoring Slack + Atlassian (Jira, Bitbucket, Confluence) with autonomous agent responses

---

## Executive Summary

This plan integrates the existing CiteMed Slackbot with Atlassian polling to create a unified monitoring service that:
1. **Monitors Slack** for direct mentions in #citemed-development
2. **Polls Atlassian services** for mentions/tags of the service account (remington)
3. **Orchestrates responses** via run_agent.py based on context
4. **Runs locally** without requiring public webhook endpoints

### Feasibility Verdict: **✅ CONFIRMED FEASIBLE**

Polling is fully supported by Atlassian APIs with the following considerations:
- **Rate Limits:** Manageable with 30-60 second polling intervals
- **API Coverage:** All required endpoints available (Jira, Bitbucket, Confluence)
- **Local Development:** No ngrok/public endpoint needed for polling approach
- **Webhooks Available:** Can be added later for production optimization

---

## 1. Technical Research Summary

### 1.1 Jira Cloud API (Polling)

**Endpoint:** `/rest/api/3/search/jql`

**Polling Strategy:**
```jql
# Get issues updated in last 2 minutes with service account mentioned
updated >= -2m AND (comment ~ "remington" OR comment ~ "@remington")
```

**Key Findings:**
- ✅ JQL supports time-based queries (`updated >= -Xm`)
- ✅ Can search comment text for mentions
- ✅ Returns full issue + comment data
- ⚠️ Must use `/rest/api/3/search/jql` (new endpoint, old ones deprecated Aug 2025)
- ⚠️ Account ID format: `[~accountid:{ACCOUNT_ID}]` in comments

**Rate Limits:**
- General API: ~100-300 requests per minute (varies by plan)
- Recommended polling: Every 30-60 seconds
- Use `maxResults=50` to minimize API calls

**Example Request:**
```bash
curl -X GET 'https://citemed.atlassian.net/rest/api/3/search/jql?jql=updated>=-2m' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### 1.2 Bitbucket Cloud API (Polling)

**Endpoints:**
1. **Pull Request Activities:** `/2.0/repositories/{workspace}/{repo}/pullrequests/{pr_id}/activity`
2. **Pull Request Comments:** `/2.0/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments`
3. **Repository Activity:** `/2.0/repositories/{workspace}/{repo}/pullrequests?state=OPEN&updated_on>=2025-10-19T10:00:00Z`

**Polling Strategy:**
```python
# 1. Get recently updated PRs
GET /2.0/repositories/{workspace}/{repo}/pullrequests?state=OPEN&updated_on>={last_check_timestamp}

# 2. For each PR, check activity for mentions
GET /2.0/repositories/{workspace}/{repo}/pullrequests/{pr_id}/activity?pagelen=50

# 3. Filter for comments mentioning service account
# Mention format: @{ATLASSIAN_ACCOUNT_ID}
```

**Key Findings:**
- ✅ Supports timestamp-based filtering (`updated_on>=TIMESTAMP`)
- ✅ Activity feed includes comments, reviews, approvals
- ✅ Can filter by action type (e.g., "COMMENTED")
- ⚠️ Mention format: `@{accountId}` in comment bodies
- ⚠️ Must check multiple repositories

**Rate Limits:**
- Standard: 1000 requests per hour per user
- Recommended polling: Every 60 seconds across all repos
- Use pagination (`pagelen=50`) efficiently

### 1.3 Confluence Cloud API (Polling)

**Endpoints:**
1. **Content Search:** `/wiki/api/v2/pages?limit=50&modified-from={timestamp}`
2. **Page Comments:** `/wiki/api/v2/pages/{page_id}/footer-comments`
3. **Inline Comments:** `/wiki/api/v2/pages/{page_id}/inline-comments`

**Polling Strategy:**
```python
# 1. Get recently updated pages
GET /wiki/api/v2/pages?limit=50&modified-from={last_check_iso_timestamp}&sort=modified-date

# 2. For each page, get comments
GET /wiki/api/v2/pages/{page_id}/footer-comments
GET /wiki/api/v2/pages/{page_id}/inline-comments

# 3. Filter comments for service account mentions
# Mention format: @{username} or accountId reference
```

**Key Findings:**
- ✅ Supports timestamp filtering (`modified-from=ISO8601`)
- ✅ Separate endpoints for footer and inline comments
- ⚠️ No unified "activity feed" API (must poll pages + comments separately)
- ⚠️ Limited mention detection in API (may need text search for "@remington")
- ⚠️ Rate limits stricter than Jira/Bitbucket

**Rate Limits:**
- Confluence Cloud: ~100-200 requests per minute
- Recommended polling: Every 60-120 seconds
- Focus on specific spaces to reduce API calls

### 1.4 Rate Limit Summary (2025 Updates)

**Effective Dates:**
- **Aug 18, 2025:** Free app rate limits enforced
- **Aug 28, 2025:** Burst API rate limiting enforced
- **Nov 22, 2025:** API token rate limits implemented

**Best Practices:**
1. ✅ **Use webhooks when possible** (Atlassian's recommendation)
2. ✅ **Sequential requests** instead of concurrent
3. ✅ **Exponential backoff** on 429 responses (Retry-After header)
4. ✅ **Cache responses** to minimize duplicate calls
5. ✅ **Batch operations** where API supports it

**Polling vs Webhooks:**
| Feature | Polling (Proposed) | Webhooks (Future) |
|---------|-------------------|-------------------|
| Local Dev | ✅ Easy (no ngrok) | ⚠️ Requires ngrok/tunnel |
| Rate Limits | ⚠️ ~100-300 req/min | ✅ No limits |
| Latency | ⚠️ 30-60s delay | ✅ Real-time (< 1s) |
| Complexity | ✅ Simple loops | ⚠️ Flask server + signature validation |
| Reliability | ⚠️ Miss events if down | ✅ Retry mechanisms |
| **Recommendation** | **Phase 1: Local Dev** | **Phase 2: Production** |

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    CiteMed PM Bot Service                        │
│                  (Unified Monitoring Service)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼──────┐ ┌───▼────────┐ ┌─▼──────────────┐
        │ Slack Poller │ │Jira Poller │ │Bitbucket Poller│
        │  (15s loop)  │ │(60s loop)  │ │  (60s loop)    │
        └───────┬──────┘ └───┬────────┘ └─┬──────────────┘
                │            │             │
                │            │             │
        ┌───────▼────────────▼─────────────▼──────────────┐
        │         Event Queue & Classifier                 │
        │  - Deduplicates events                          │
        │  - Classifies by type (bug/feature/question)    │
        │  - Routes to appropriate handler                │
        └───────────────────┬──────────────────────────────┘
                            │
                ┌───────────▼───────────────┐
                │   Agent Orchestrator      │
                │   (run_agent.py)          │
                │                           │
                │  Routes to subagents:     │
                │  - SLA Monitor            │
                │  - Developer Auditor      │
                │  - Sprint Analyzer        │
                │  - Jira Manager           │
                └───────────┬───────────────┘
                            │
                ┌───────────▼───────────────┐
                │   Response Dispatcher     │
                │  - Posts to Slack threads │
                │  - Comments on Jira       │
                │  - Comments on PRs        │
                │  - Updates Confluence     │
                └───────────────────────────┘
```

### 2.2 File Structure

```
project-manager/
├── bot_service.py                     # Main service entrypoint (NEW)
├── run_agent.py                       # Agent orchestration (EXISTS)
├── .env                               # Configuration (EXISTS)
├── .mcp.json                          # MCP servers (EXISTS)
│
├── bots/                              # Bot modules (NEW)
│   ├── __init__.py
│   ├── slack_monitor.py               # Slack polling (adapted from working_bot.py)
│   ├── jira_monitor.py                # Jira polling (NEW)
│   ├── bitbucket_monitor.py           # Bitbucket polling (NEW)
│   ├── confluence_monitor.py          # Confluence polling (NEW)
│   ├── event_queue.py                 # Event deduplication & routing (NEW)
│   └── response_dispatcher.py         # Multi-channel responses (NEW)
│
├── .claude/
│   ├── INTEGRATION_PLAN.md            # This file
│   ├── agents/                        # Subagent definitions (EXISTS)
│   ├── workflows/                     # PM workflows (EXISTS)
│   └── data/
│       └── bot-state/                 # Bot state tracking (NEW)
│           ├── slack_state.db
│           ├── jira_state.db
│           ├── bitbucket_state.db
│           └── confluence_state.db
```

---

## 3. Implementation Plan

### Phase 1: Slack Bot Migration (Week 1)

**Goal:** Migrate and enhance existing slackbot to project-manager repo

**Tasks:**
1. ✅ Copy `working_bot.py` to `bots/slack_monitor.py`
2. ✅ Refactor to use shared configuration from `.env`
3. ✅ Add event queue integration instead of direct Claude processing
4. ✅ Update database path to `.claude/data/bot-state/slack_state.db`
5. ✅ Integrate with `run_agent.py` for agent orchestration

**Deliverables:**
- `bots/slack_monitor.py` - Slack polling service
- `bots/event_queue.py` - Event deduplication and routing
- Unit tests for Slack monitor

**Success Criteria:**
- Bot responds to Slack mentions in #citemed-development
- Events properly queued and deduplicated
- Agent responses posted back to Slack threads

---

### Phase 2: Jira Polling Service (Week 2)

**Goal:** Monitor Jira for service account mentions in comments

**Implementation Details:**

```python
# bots/jira_monitor.py

import requests
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

class JiraMonitor:
    def __init__(self):
        self.api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        self.cloud_id = os.getenv("ATLASSIAN_CLOUD_ID")
        self.base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"

        self.db_path = Path(".claude/data/bot-state/jira_state.db")
        self.polling_interval = 60  # seconds

    def poll_for_mentions(self):
        """Poll Jira for service account mentions in last 2 minutes"""

        # JQL query for recently updated issues with mentions
        jql = 'updated >= -2m AND (comment ~ "remington" OR comment ~ "@remington")'

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }

        params = {
            "jql": jql,
            "fields": "summary,comment,updated,status,assignee",
            "maxResults": 50,
            "expand": "renderedFields"
        }

        response = requests.get(
            f"{self.base_url}/rest/api/3/search/jql",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            issues = response.json().get("issues", [])
            return self.filter_new_mentions(issues)
        else:
            print(f"Jira API error: {response.status_code}")
            return []

    def filter_new_mentions(self, issues):
        """Filter out already processed comments"""
        new_events = []

        for issue in issues:
            issue_key = issue["key"]
            comments = issue["fields"].get("comment", {}).get("comments", [])

            for comment in comments:
                # Check if comment mentions service account
                if self.is_service_account_mentioned(comment["body"]):
                    # Check if we've already processed this comment
                    if not self.is_processed(issue_key, comment["id"]):
                        new_events.append({
                            "source": "jira",
                            "type": "comment_mention",
                            "issue_key": issue_key,
                            "comment_id": comment["id"],
                            "comment_text": comment["body"],
                            "author": comment["author"]["displayName"],
                            "timestamp": comment["created"],
                            "issue_summary": issue["fields"]["summary"]
                        })

                        # Mark as processed
                        self.mark_processed(issue_key, comment["id"])

        return new_events

    def is_service_account_mentioned(self, text):
        """Check if service account is mentioned in text"""
        # Check for @mention format or username
        return "@remington" in text.lower() or "remington" in text.lower()

    def is_processed(self, issue_key, comment_id):
        """Check if comment already processed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_mentions WHERE issue_key=? AND comment_id=?",
                (issue_key, comment_id)
            )
            return cursor.fetchone() is not None

    def mark_processed(self, issue_key, comment_id):
        """Mark comment as processed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_mentions (issue_key, comment_id, processed_at) VALUES (?, ?, ?)",
                (issue_key, comment_id, datetime.now().isoformat())
            )
```

**Tasks:**
1. ✅ Implement `JiraMonitor` class with JQL polling
2. ✅ Database schema for tracking processed mentions
3. ✅ Integration with event queue
4. ✅ Rate limit handling (exponential backoff on 429)
5. ✅ Unit tests

**Success Criteria:**
- Detects mentions in Jira comments within 60 seconds
- No duplicate processing of same mention
- Properly handles rate limits
- Agent can respond to Jira mentions with ticket updates

---

### Phase 3: Bitbucket Polling Service (Week 3)

**Goal:** Monitor Bitbucket pull requests for mentions and activity

**Implementation Details:**

```python
# bots/bitbucket_monitor.py

class BitbucketMonitor:
    def __init__(self):
        self.workspace = "citemed"
        self.repos = ["citemed_web", "word_addon"]  # From .env
        self.api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.base_url = "https://api.bitbucket.org/2.0"

        self.polling_interval = 60  # seconds
        self.db_path = Path(".claude/data/bot-state/bitbucket_state.db")

    def poll_pull_requests(self):
        """Poll for PR mentions across all repositories"""
        new_events = []

        for repo in self.repos:
            # Get recently updated PRs
            last_check = self.get_last_check_time(repo)

            headers = {"Authorization": f"Bearer {self.api_token}"}
            params = {
                "state": "OPEN",
                "updated_on": f">={last_check.isoformat()}",
                "pagelen": 50
            }

            response = requests.get(
                f"{self.base_url}/repositories/{self.workspace}/{repo}/pullrequests",
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                prs = response.json().get("values", [])

                for pr in prs:
                    # Check PR activity for mentions
                    pr_events = self.check_pr_activity(repo, pr["id"])
                    new_events.extend(pr_events)

        return new_events

    def check_pr_activity(self, repo, pr_id):
        """Check specific PR for mentions in comments/activity"""
        events = []

        # Get PR activity
        response = requests.get(
            f"{self.base_url}/repositories/{self.workspace}/{repo}/pullrequests/{pr_id}/activity",
            headers={"Authorization": f"Bearer {self.api_token}"},
            params={"pagelen": 50}
        )

        if response.status_code == 200:
            activities = response.json().get("values", [])

            for activity in activities:
                if activity.get("comment"):
                    comment = activity["comment"]

                    # Check for service account mention
                    if self.is_mentioned(comment.get("content", {}).get("raw", "")):
                        if not self.is_processed(repo, pr_id, comment["id"]):
                            events.append({
                                "source": "bitbucket",
                                "type": "pr_comment_mention",
                                "repo": repo,
                                "pr_id": pr_id,
                                "comment_id": comment["id"],
                                "comment_text": comment["content"]["raw"],
                                "author": activity["comment"]["user"]["display_name"],
                                "timestamp": activity["comment"]["created_on"]
                            })

                            self.mark_processed(repo, pr_id, comment["id"])

        return events

    def is_mentioned(self, text):
        """Check if service account mentioned in PR comment"""
        # Bitbucket format: @{ACCOUNT_ID} or @username
        return "@remington" in text.lower() or f"@{{{self.account_id}}}" in text
```

**Tasks:**
1. ✅ Implement `BitbucketMonitor` with PR/comment polling
2. ✅ Support multiple repositories from .env
3. ✅ Database schema for tracking processed PR comments
4. ✅ Integration with event queue
5. ✅ Rate limit handling
6. ✅ Unit tests

**Success Criteria:**
- Detects PR comment mentions within 60 seconds
- Supports multiple repositories
- Agent can review code and respond to PR comments
- No duplicate processing

---

### Phase 4: Confluence Polling Service (Week 4)

**Goal:** Monitor Confluence for page/comment mentions

**Implementation Details:**

```python
# bots/confluence_monitor.py

class ConfluenceMonitor:
    def __init__(self):
        self.api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.cloud_id = os.getenv("ATLASSIAN_CLOUD_ID")
        self.base_url = f"https://api.atlassian.com/ex/confluence/{self.cloud_id}"

        self.spaces = ["ECD", "COMP"]  # Focus on specific spaces
        self.polling_interval = 120  # 2 minutes (stricter rate limits)
        self.db_path = Path(".claude/data/bot-state/confluence_state.db")

    def poll_pages(self):
        """Poll for recently updated pages with mentions"""
        new_events = []

        last_check = self.get_last_check_time()

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }

        params = {
            "limit": 50,
            "modified-from": last_check.isoformat(),
            "sort": "modified-date"
        }

        response = requests.get(
            f"{self.base_url}/wiki/api/v2/pages",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            pages = response.json().get("results", [])

            for page in pages:
                # Check page comments for mentions
                page_events = self.check_page_comments(page["id"])
                new_events.extend(page_events)

        return new_events

    def check_page_comments(self, page_id):
        """Check page footer and inline comments for mentions"""
        events = []

        # Check footer comments
        footer_comments = self.get_comments(page_id, "footer-comments")
        events.extend(self.process_comments(page_id, footer_comments, "footer"))

        # Check inline comments
        inline_comments = self.get_comments(page_id, "inline-comments")
        events.extend(self.process_comments(page_id, inline_comments, "inline"))

        return events

    def process_comments(self, page_id, comments, comment_type):
        """Process comments for mentions"""
        events = []

        for comment in comments:
            comment_body = comment.get("body", {}).get("storage", {}).get("value", "")

            if self.is_mentioned(comment_body):
                if not self.is_processed(page_id, comment["id"]):
                    events.append({
                        "source": "confluence",
                        "type": f"page_{comment_type}_comment_mention",
                        "page_id": page_id,
                        "comment_id": comment["id"],
                        "comment_text": comment_body,
                        "author": comment["authorId"],
                        "timestamp": comment["createdAt"]
                    })

                    self.mark_processed(page_id, comment["id"])

        return events
```

**Tasks:**
1. ✅ Implement `ConfluenceMonitor` with page/comment polling
2. ✅ Handle both footer and inline comments
3. ✅ Database schema for tracking processed comments
4. ✅ Integration with event queue
5. ✅ Rate limit handling (more conservative)
6. ✅ Unit tests

**Success Criteria:**
- Detects Confluence mentions within 2 minutes
- Handles both comment types
- Agent can update documentation pages
- Respects stricter rate limits

---

### Phase 5: Unified Bot Service (Week 5)

**Goal:** Orchestrate all monitors with shared event queue and agent routing

**Implementation Details:**

```python
# bot_service.py (Main entrypoint)

import asyncio
from bots.slack_monitor import SlackMonitor
from bots.jira_monitor import JiraMonitor
from bots.bitbucket_monitor import BitbucketMonitor
from bots.confluence_monitor import ConfluenceMonitor
from bots.event_queue import EventQueue
from bots.response_dispatcher import ResponseDispatcher

class CiteMedPMBotService:
    """Unified bot service coordinating all monitors"""

    def __init__(self):
        self.slack_monitor = SlackMonitor()
        self.jira_monitor = JiraMonitor()
        self.bitbucket_monitor = BitbucketMonitor()
        self.confluence_monitor = ConfluenceMonitor()

        self.event_queue = EventQueue()
        self.response_dispatcher = ResponseDispatcher()

    async def start(self):
        """Start all monitoring services"""
        print("🚀 Starting CiteMed PM Bot Service...")

        # Start all monitors concurrently
        await asyncio.gather(
            self.run_slack_monitor(),
            self.run_jira_monitor(),
            self.run_bitbucket_monitor(),
            self.run_confluence_monitor(),
            self.process_event_queue()
        )

    async def run_slack_monitor(self):
        """Run Slack polling loop"""
        while True:
            try:
                events = self.slack_monitor.poll_for_mentions()
                for event in events:
                    self.event_queue.add(event)

                await asyncio.sleep(self.slack_monitor.polling_interval)
            except Exception as e:
                print(f"Slack monitor error: {e}")
                await asyncio.sleep(30)  # Back off on error

    async def run_jira_monitor(self):
        """Run Jira polling loop"""
        while True:
            try:
                events = self.jira_monitor.poll_for_mentions()
                for event in events:
                    self.event_queue.add(event)

                await asyncio.sleep(self.jira_monitor.polling_interval)
            except Exception as e:
                print(f"Jira monitor error: {e}")
                await asyncio.sleep(60)

    async def run_bitbucket_monitor(self):
        """Run Bitbucket polling loop"""
        while True:
            try:
                events = self.bitbucket_monitor.poll_pull_requests()
                for event in events:
                    self.event_queue.add(event)

                await asyncio.sleep(self.bitbucket_monitor.polling_interval)
            except Exception as e:
                print(f"Bitbucket monitor error: {e}")
                await asyncio.sleep(60)

    async def run_confluence_monitor(self):
        """Run Confluence polling loop"""
        while True:
            try:
                events = self.confluence_monitor.poll_pages()
                for event in events:
                    self.event_queue.add(event)

                await asyncio.sleep(self.confluence_monitor.polling_interval)
            except Exception as e:
                print(f"Confluence monitor error: {e}")
                await asyncio.sleep(120)

    async def process_event_queue(self):
        """Process events from queue and dispatch to agents"""
        while True:
            try:
                event = self.event_queue.get(timeout=1)

                if event:
                    # Classify event and route to appropriate agent
                    classified_event = self.event_queue.classify(event)

                    # Call run_agent.py with appropriate subagent
                    response = await self.invoke_agent(classified_event)

                    # Dispatch response to appropriate channel
                    await self.response_dispatcher.send(classified_event, response)

            except Exception as e:
                print(f"Event processing error: {e}")
                await asyncio.sleep(1)

    async def invoke_agent(self, event):
        """Invoke appropriate agent via run_agent.py"""
        import subprocess

        # Build context for agent
        context = {
            "source": event["source"],
            "type": event["type"],
            "content": event.get("comment_text") or event.get("text"),
            "author": event.get("author"),
            "metadata": event
        }

        # Determine which subagent to use
        if event["type"] in ["bug_report", "sla_violation"]:
            agent_type = "sla-monitor"
        elif event["type"] in ["pr_review_request", "code_question"]:
            agent_type = "developer-auditor"
        else:
            agent_type = "jira-manager"

        # Call run_agent.py
        result = subprocess.run(
            ["python", "run_agent.py", agent_type, "--context", json.dumps(context)],
            capture_output=True,
            text=True,
            timeout=300
        )

        return result.stdout if result.returncode == 0 else "Error processing request"

async def main():
    service = CiteMedPMBotService()
    await service.start()

if __name__ == "__main__":
    asyncio.run(main())
```

**Tasks:**
1. ✅ Implement unified `CiteMedPMBotService` orchestrator
2. ✅ Concurrent asyncio loops for all monitors
3. ✅ Event queue with deduplication and classification
4. ✅ Response dispatcher for multi-channel output
5. ✅ Integration with `run_agent.py`
6. ✅ Comprehensive logging and monitoring
7. ✅ Unit and integration tests

**Success Criteria:**
- All 4 monitors running concurrently
- Events properly deduplicated and routed
- Agent responses sent to correct channels
- Service recovers from individual monitor failures
- < 2 minute response time from mention to agent action

---

### Phase 6: Webhook Support (Week 6 - Optional)

**Goal:** Add webhook support as alternative to polling for production

**Why Webhooks:**
- ✅ Real-time (< 1 second latency)
- ✅ No rate limit concerns
- ✅ Recommended by Atlassian
- ⚠️ Requires public endpoint (ngrok for local dev)
- ⚠️ More complex (signature validation, Flask server)

**Implementation:**
1. ✅ Flask webhook server (based on `slack_bot_service.py`)
2. ✅ Signature validation for Jira/Bitbucket/Slack
3. ✅ Event routing from webhook to event queue
4. ✅ Configuration toggle: `.env` setting `USE_WEBHOOKS=true/false`
5. ✅ Ngrok integration for local development
6. ✅ Production deployment guide

**Success Criteria:**
- Can toggle between polling and webhooks via config
- Webhooks properly validated and routed
- Local dev works with ngrok
- Production deployment documented

---

## 4. Event Classification & Routing

### Event Types

```python
EVENT_TYPES = {
    # Slack events
    "slack_mention": {
        "agent": "general",  # Use Claude with MCP tools (existing working_bot behavior)
        "priority": "medium"
    },

    # Jira events
    "jira_comment_mention": {
        "agent": "jira-manager",
        "priority": "high",
        "actions": ["update_ticket", "post_comment", "create_subtask"]
    },
    "jira_blocker_mentioned": {
        "agent": "sla-monitor",
        "priority": "critical",
        "actions": ["escalate", "notify_team"]
    },

    # Bitbucket events
    "pr_review_request": {
        "agent": "developer-auditor",
        "priority": "high",
        "actions": ["review_code", "post_pr_comment", "approve_or_request_changes"]
    },
    "pr_comment_mention": {
        "agent": "developer-auditor",
        "priority": "medium",
        "actions": ["answer_question", "review_specific_file"]
    },

    # Confluence events
    "confluence_page_mention": {
        "agent": "jira-manager",
        "priority": "medium",
        "actions": ["update_documentation", "clarify_policy"]
    },
    "confluence_policy_review": {
        "agent": "compliance",  # Future: integrate compliance agent
        "priority": "high",
        "actions": ["initiate_review_workflow"]
    }
}
```

### Classification Logic

```python
# bots/event_queue.py

class EventQueue:
    def classify(self, event):
        """Classify event type and determine routing"""

        # Extract text content
        text = event.get("comment_text") or event.get("text", "")
        text_lower = text.lower()

        # Pattern matching for classification
        if "blocked" in text_lower or "blocker" in text_lower:
            event["classified_type"] = "jira_blocker_mentioned"
            event["priority"] = "critical"

        elif event["source"] == "bitbucket" and "review" in text_lower:
            event["classified_type"] = "pr_review_request"
            event["priority"] = "high"

        elif "bug" in text_lower or "error" in text_lower:
            event["classified_type"] = "bug_report"
            event["priority"] = "high"

        elif "?" in text or "how" in text_lower or "what" in text_lower:
            event["classified_type"] = "question"
            event["priority"] = "medium"

        else:
            event["classified_type"] = f"{event['source']}_mention"
            event["priority"] = "medium"

        return event
```

---

## 5. Configuration

### 5.1 Environment Variables (.env)

```bash
# Existing variables (already configured)
ATLASSIAN_SERVICE_ACCOUNT_TOKEN='ATSTT...'
ATLASSIAN_SERVICE_ACCOUNT_EMAIL='remington-cd3wmzelbd@serviceaccount.atlassian.com'
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
SLACK_BOT_TOKEN="xoxb-your-bot-token-here"
SLACK_CHANNEL_STANDUP="C02NW7QN1RN"
SLACK_BOT_USER_ID='U09BVV00XRP'

# New variables for bot service
BOT_SERVICE_MODE=polling  # 'polling' or 'webhooks'

# Bitbucket configuration
BITBUCKET_WORKSPACE=citemed
BITBUCKET_REPOS=citemed_web,word_addon

# Confluence configuration
CONFLUENCE_SPACES=ECD,COMP

# Polling intervals (seconds)
SLACK_POLL_INTERVAL=15
JIRA_POLL_INTERVAL=60
BITBUCKET_POLL_INTERVAL=60
CONFLUENCE_POLL_INTERVAL=120

# Rate limit settings
MAX_RETRIES=3
BACKOFF_MULTIPLIER=2
```

### 5.2 Database Schemas

```sql
-- .claude/data/bot-state/slack_state.db
CREATE TABLE IF NOT EXISTS processed_messages (
    ts TEXT PRIMARY KEY,
    channel TEXT,
    user_id TEXT,
    text TEXT,
    response TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- .claude/data/bot-state/jira_state.db
CREATE TABLE IF NOT EXISTS processed_mentions (
    issue_key TEXT,
    comment_id TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (issue_key, comment_id)
);

CREATE TABLE IF NOT EXISTS last_check (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- .claude/data/bot-state/bitbucket_state.db
CREATE TABLE IF NOT EXISTS processed_pr_comments (
    repo TEXT,
    pr_id INTEGER,
    comment_id TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (repo, pr_id, comment_id)
);

CREATE TABLE IF NOT EXISTS last_check_per_repo (
    repo TEXT PRIMARY KEY,
    timestamp TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- .claude/data/bot-state/confluence_state.db
CREATE TABLE IF NOT EXISTS processed_comments (
    page_id TEXT,
    comment_id TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (page_id, comment_id)
);

CREATE TABLE IF NOT EXISTS last_check (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_jira_monitor.py
def test_jira_mention_detection():
    """Test Jira monitor detects service account mentions"""

def test_jira_deduplication():
    """Test Jira monitor doesn't reprocess same comment"""

def test_jira_rate_limit_handling():
    """Test Jira monitor handles 429 responses"""

# tests/test_bitbucket_monitor.py
def test_bitbucket_pr_polling():
    """Test Bitbucket polls for updated PRs"""

def test_bitbucket_mention_format():
    """Test Bitbucket detects @{accountId} format"""

# tests/test_event_queue.py
def test_event_deduplication():
    """Test event queue deduplicates identical events"""

def test_event_classification():
    """Test event queue classifies events correctly"""
```

### 6.2 Integration Tests

```python
# tests/integration/test_end_to_end.py
async def test_slack_to_agent_to_response():
    """Test: Slack mention → Agent processing → Slack response"""

async def test_jira_mention_to_ticket_update():
    """Test: Jira mention → Agent action → Jira comment response"""

async def test_pr_review_request():
    """Test: PR mention → Code review → PR comment with feedback"""
```

### 6.3 Load Testing

```python
# tests/load/test_rate_limits.py
async def test_sustained_polling():
    """Test bot service handles sustained polling without hitting rate limits"""

async def test_burst_events():
    """Test bot service handles burst of events across all sources"""
```

---

## 7. Deployment & Operations

### 7.1 Local Development

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with actual tokens

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run bot service
python bot_service.py

# Monitor logs
tail -f .claude/data/bot-state/bot_service.log
```

### 7.2 Production Deployment (Future)

**Option 1: Polling-based (Current Plan)**
```bash
# Run as systemd service on Linux server
sudo systemctl start citemed-pm-bot
sudo systemctl enable citemed-pm-bot
```

**Option 2: Webhook-based (Phase 6)**
```bash
# Deploy Flask app behind nginx
# Use Let's Encrypt for HTTPS
# Configure webhook URLs in Atlassian
```

### 7.3 Monitoring

**Metrics to Track:**
- Events processed per minute (by source)
- Response latency (mention → agent action)
- API rate limit hits (429 responses)
- Failed processing (errors)
- Database size growth

**Alerting:**
- Critical: Service down for > 5 minutes
- Warning: Rate limit hit 3+ times in 10 minutes
- Info: Event queue > 50 items

---

## 8. Timeline & Milestones

| Week | Phase | Deliverables | Status |
|------|-------|--------------|--------|
| 1 | Slack Bot Migration | `bots/slack_monitor.py`, Event queue | 🔲 Not Started |
| 2 | Jira Polling | `bots/jira_monitor.py`, JQL integration | 🔲 Not Started |
| 3 | Bitbucket Polling | `bots/bitbucket_monitor.py`, PR monitoring | 🔲 Not Started |
| 4 | Confluence Polling | `bots/confluence_monitor.py`, Page tracking | 🔲 Not Started |
| 5 | Unified Service | `bot_service.py`, Full integration | 🔲 Not Started |
| 6 | Webhook Support | Flask server, Webhook handlers (Optional) | 🔲 Future |

**Total Estimated Time:** 5-6 weeks for full polling implementation

---

## 9. Risks & Mitigations

### Risk 1: API Rate Limits
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Conservative polling intervals (60s+ for Atlassian)
- Exponential backoff on 429 responses
- Monitor rate limit headers proactively
- Implement webhook fallback (Phase 6)

### Risk 2: Event Deduplication Failures
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Robust database-backed deduplication
- Event fingerprinting (hash of key fields)
- Comprehensive unit tests

### Risk 3: Agent Timeout on Complex Requests
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- 10-minute timeout for agent calls (already in working_bot.py)
- Async processing (don't block polling loops)
- Fallback responses for timeouts

### Risk 4: Confluence API Limitations
**Probability:** Medium
**Impact:** Low
**Mitigation:**
- Focus on specific spaces only
- Longer polling interval (2 minutes)
- Consider Confluence as lower priority source

---

## 10. Future Enhancements

### Short-term (3-6 months)
1. **AI-powered Event Triage** - Use LLM to classify urgency before agent invocation
2. **Smart Batching** - Group related events for more efficient agent processing
3. **Proactive Notifications** - Bot proactively notifies team of sprint risks

### Long-term (6-12 months)
1. **Full Webhook Migration** - Transition from polling to webhooks in production
2. **Multi-tenant Support** - Support multiple Atlassian instances/workspaces
3. **Analytics Dashboard** - Web dashboard showing bot activity and metrics
4. **Voice Commands** - Slack slash commands for manual agent invocation

---

## 11. Decision: Polling vs Webhooks

### Recommendation: **Polling for Phase 1, Webhooks for Phase 2**

**Phase 1 (Weeks 1-5): Polling**
- ✅ Easier local development (no ngrok required)
- ✅ Simpler implementation (no Flask server, signature validation)
- ✅ Good enough for initial deployment (<100 events/day)
- ⚠️ 30-120 second latency (acceptable for PM tasks)

**Phase 2 (Week 6+): Webhooks**
- ✅ Production-ready with real-time responses
- ✅ No rate limit concerns
- ✅ Recommended by Atlassian
- ⚠️ Requires public endpoint setup

**The best of both worlds:** Implement polling first, add webhooks as optional toggle later.

---

## 12. Next Steps

**Immediate (Today):**
1. ✅ Review and approve this integration plan
2. ✅ Confirm polling intervals are acceptable (15s Slack, 60s Jira/BB, 120s Confluence)
3. ✅ Decide: Start with Phase 1 (Slack migration) or full implementation?

**This Week:**
1. 🔲 Create `bots/` directory structure
2. 🔲 Migrate `working_bot.py` to `bots/slack_monitor.py`
3. 🔲 Implement `EventQueue` with deduplication
4. 🔲 Test Slack monitor integration with `run_agent.py`

**Next Week:**
1. 🔲 Implement `JiraMonitor` with JQL polling
2. 🔲 Test Jira mention detection end-to-end
3. 🔲 Begin `BitbucketMonitor` implementation

---

## Appendix A: API Endpoint Reference

### Jira Cloud REST API v3

```
Base URL: https://api.atlassian.com/ex/jira/{cloudId}

# Search with JQL
GET /rest/api/3/search/jql?jql={query}&fields={fields}&maxResults=50

# Get specific issue
GET /rest/api/3/issue/{issueIdOrKey}?expand=renderedFields

# Add comment
POST /rest/api/3/issue/{issueIdOrKey}/comment
Body: {"body": {"type": "doc", "content": [...]}}

# Update issue
PUT /rest/api/3/issue/{issueIdOrKey}
```

### Bitbucket Cloud API v2

```
Base URL: https://api.bitbucket.org/2.0

# List pull requests
GET /repositories/{workspace}/{repo}/pullrequests?state=OPEN&updated_on>={timestamp}

# Get PR activity
GET /repositories/{workspace}/{repo}/pullrequests/{pr_id}/activity?pagelen=50

# Get PR comments
GET /repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments

# Post PR comment
POST /repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments
Body: {"content": {"raw": "Comment text @{accountId}"}}
```

### Confluence Cloud API v2

```
Base URL: https://api.atlassian.com/ex/confluence/{cloudId}

# Search pages
GET /wiki/api/v2/pages?limit=50&modified-from={iso_timestamp}&sort=modified-date

# Get page comments (footer)
GET /wiki/api/v2/pages/{page_id}/footer-comments

# Get page comments (inline)
GET /wiki/api/v2/pages/{page_id}/inline-comments

# Post comment
POST /wiki/api/v2/pages/{page_id}/footer-comments
Body: {"body": {"representation": "storage", "value": "<p>Comment text</p>"}}
```

---

## Appendix B: Example Event Flow

```
1. User mentions @remington in Jira comment:
   "Hey @remington, ECD-789 is blocked on database migration"

2. JiraMonitor (60s polling loop):
   - Runs JQL: updated >= -2m AND comment ~ "remington"
   - Finds ECD-789 with new comment
   - Checks database: comment ID not processed
   - Creates event:
     {
       "source": "jira",
       "type": "comment_mention",
       "issue_key": "ECD-789",
       "comment_id": "12345",
       "comment_text": "Hey @remington, ECD-789 is blocked...",
       "author": "Mohamed",
       "timestamp": "2025-10-19T14:30:00Z"
     }
   - Adds to EventQueue
   - Marks comment as processed in database

3. EventQueue.classify():
   - Detects "blocked" keyword
   - Classifies as "jira_blocker_mentioned"
   - Sets priority: "critical"

4. Agent Orchestrator:
   - Routes to "sla-monitor" agent
   - Calls: python run_agent.py sla-monitor --context {...}
   - Agent analyzes blocker, checks SLAs, prepares escalation

5. ResponseDispatcher:
   - Posts comment to ECD-789:
     "I've detected a blocker on ECD-789. This ticket is in 'In Progress' status
      for 3 days with no updates. I'm escalating to @TechLead per SLA policy.

      Actions taken:
      - Created escalation ticket ECD-790
      - Posted to #dev-alerts Slack channel
      - Updated ticket status to 'Blocked'

      Next steps:
      - Database migration needs approval from DevOps
      - Alternative: Use separate schema for this feature"

   - Posts to Slack #dev-alerts:
     "🚨 Blocker Alert: ECD-789 has been blocked for 3 days
      See: https://citemed.atlassian.net/browse/ECD-789"

6. Total Time: ~60-90 seconds from mention to response
```

---

**End of Integration Plan**

**Questions or feedback?** Review this plan and confirm approach before implementation begins.