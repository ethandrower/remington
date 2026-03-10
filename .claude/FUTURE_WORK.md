# Long-Term Improvements & Future Enhancements

**Last Updated:** 2025-11-25

This document tracks long-term improvements, automation goals, and feature requests for the CiteMed Project Manager autonomous agent.

---

## 🎯 SDLC Audit-Based Roadmap (Priority Tiers)

**Based on:** SDLC Audit Report (2025-11-24)
**Current SDLC Coverage:** ~40%
**Target Coverage:** 80% by end of Phase 2

### ⭐ Tier 1: Critical SDLC Gates (Immediate - Weeks 1-2)
**Effort:** 4-6 days | **ROI:** Very High | **Impact:** Prevents 80% of incomplete work from progressing

#### 1.1. Ready for Dev Gate Validator (Gap #1)
**Problem:** Stories enter development without complete requirements
**Impact:** Causes downstream rework, wasted dev time

**Implementation:**
- Automated validator checks:
  - ✅ Acceptance Criteria clearly written (not empty)
  - ✅ Story Points assigned
  - ✅ Fix Version assigned
  - ✅ **Due Date set** (NEW - for deadline tracking)
  - ✅ **Original Estimate set** (NEW - for capacity planning)
  - ✅ UX flag set if needed
  - ✅ Test scenarios provided
  - ✅ Confluence link attached
- **Block** transition to "Ready for Dev" if incomplete
- Post Jira comment listing missing items
- Alert PM via Slack

**Effort:** 2-3 days | **Priority:** P0

---

#### 1.4. Definition of Ready Daily Enforcement (NEW)
**Problem:** Active work missing deadlines, time estimates, or stalled in refinement
**Impact:** Poor capacity planning, sprint unpredictability, refinement bottlenecks

**Implementation:**
Daily monitoring and automated Jira comments for:

**Rule 1: Missing Deadlines**
- Query: In Progress, Ready for Dev, Ready for QA tickets without due dates
- Action: Post Jira comment tagging assignee, request due date by EOD
- Track compliance rate (target: ≥95%)

**Rule 2: Missing Hours Estimates**
- Query: Active work without Original Estimate field set
- Action: Post Jira comment with instructions to add time estimate
- Track compliance rate (target: ≥90%)

**Rule 3: Stalled Refinement (>2 days)**
- Query: Tickets in "In Refinement" status longer than 2 days
- Analysis: Check if questions were asked in comments
- Action (no questions): Urgent reminder to transition to Ready for Dev/Design OR ask questions
- Action (with questions): Gentle reminder to clarify and move forward
- Track refinement cycle time (target: ≥95% complete within 2 days)

**Integration:** Section 7 of Daily Standup Workflow

**Effort:** 1 day | **Priority:** P0

**Escalation Path:**
- Day 1: Automated Jira comment
- Day 2: Slack notification
- Day 3: PM/Tech Lead escalation

---

#### 1.2. Demo Video & INT Link Validator (Gap #4)
**Problem:** Stories marked "Ready for QA" without proper handoff artifacts
**Impact:** QA efficiency suffers without demo context

**Implementation:**
- Parse Jira ticket for demo video attachment or link
- Parse Jira ticket for INT environment link
- **Block** transition to "Ready for QA" if missing
- Post Jira comment reminding developer
- Track completion rate metrics

**Effort:** 1 day | **Priority:** P0

---

#### 1.3. Pending Approval Escalation (Gap #3)
**Problem:** Tickets sit waiting for PM/CTO approval, blocking releases
**Impact:** Release delays, missed deadlines

**Implementation:**
- Monitor "Pending Approval" status continuously
- Auto-notify PM/CTO when items need approval
- **Escalate** after 24 hours (soft reminder via Slack)
- **Escalate** after 48 hours (urgent - @mention in Slack)
- Track approval cycle time
- Generate weekly approval bottleneck report

**Effort:** 1-2 days | **Priority:** P0

---

### ⭐⭐ Tier 2: QA & Release Automation (High Priority - Weeks 3-4)
**Effort:** 6-7 days | **ROI:** High | **Impact:** Reduces release cycle time by 20-30%

#### 2.1. QA Cycle Time Monitoring (Gap #2)
**Problem:** QA bottlenecks go unnoticed, delaying releases
**Impact:** Unpredictable release timelines

**Implementation:**
- Track tickets entering "In QA" status
- Monitor time spent in QA (SLA: 48 hours)
- **Alert** when QA SLA is approaching (36-hour warning)
- Track "Needs Fix" → retest loops
- Generate weekly QA bottleneck report
- Post Slack alerts for QA delays

**Effort:** 2-3 days | **Priority:** P1

---

#### 2.2. Release Notes Automation (Gap #5)
**Problem:** Manual release notes creation is time-consuming
**Impact:** PM time drain, delayed communications

**Implementation:**
- Query all tickets in Fix Version (e.g., "v5.5.6")
- Group by Epic or issue type
- Generate markdown release notes with:
  - Ticket keys, summaries, descriptions
  - Breaking changes highlighted
  - Known issues section
- Post to Confluence automatically
- Draft Slack announcement

**Effort:** 2 days | **Priority:** P1

---

#### 2.3. Bug Spillover Management (Gap #6)
**Problem:** Bugs from previous sprint go untracked
**Impact:** Poor sprint planning, capacity surprises

**Implementation:**
- On sprint close, detect incomplete bugs
- Auto-label with "Sprint Spillover"
- Auto-move to new sprint
- Post Slack alert to PM with list
- Adjust sprint capacity calculation
- Track spillover trends over time

**Effort:** 2 days | **Priority:** P1

---

### ⭐⭐⭐ Tier 3: Advanced SDLC Automation (Medium Priority - Weeks 5-8)
**Effort:** 10-13 days | **ROI:** Medium | **Impact:** Full SDLC visibility and automation

#### 3.1. Deployment Pipeline Integration (Gap #7)
**Problem:** No automated deployment tracking
**Impact:** Limited visibility into production deployments

**Implementation:**
- Integrate with Heroku API or Azure DevOps
- Monitor deployment status via API
- Post Slack notification on successful deployment
- Auto-transition tickets to "Complete" after production deploy
- Track deployment failures and rollback events

**Effort:** 5+ days (depends on CI/CD system) | **Priority:** P2

---

#### 3.2. Design Phase Tracking (Gap #8)
**Problem:** Design phase not monitored
**Impact:** Currently not a bottleneck, but may become one

**Implementation:** *Defer until design becomes a bottleneck*
- Monitor "Needs Design" label
- Track time in design status
- Validate Figma link attachment before "Ready for Dev"
- Post Slack notification to designer when story enters design

**Effort:** 2-3 days | **Priority:** P3 (LOW - defer)

---

#### 3.3. Advanced Sprint Analytics
**Goal:** Comprehensive sprint health monitoring

**Implementation:**
- Automated burndown chart generation
- Epic progress tracking (% complete by story points)
- Velocity forecasting (predict sprint completion)
- Bottleneck identification (stuck statuses)
- Resource allocation analysis

**Effort:** 3-5 days | **Priority:** P2

---

## High Priority

### 0. Intelligent Idea Ingestion Workflow

**Goal:** Automated workflow for creating new ideas with deduplication and automatic story linking.

**Workflow Steps:**
1. **User Submits Idea** - User provides idea description via Slack or Jira
2. **Search for Duplicates** - Query existing ideas using semantic search or keyword matching
3. **Present Similar Ideas** - Show user existing ideas that might be duplicates (with similarity scores)
4. **User Confirms/Proceeds** - User decides if their idea is truly new or should be merged
5. **Search Related Stories** - Query Jira for existing stories/tickets related to the idea
6. **Suggest Story Links** - Present list of relevant stories with rationale for linking
7. **User Approves Links** - User confirms which stories should be linked to the new idea
8. **Create Idea + Links** - Create Jira idea ticket and link approved stories
9. **Notify Stakeholders** - Post to Slack with summary and links

**Technical Approach:**
```python
class IdeaIngestionWorkflow:
    async def ingest_idea(self, idea_description: str, user_id: str):
        # Step 1: Search for duplicate ideas
        similar_ideas = await self.search_similar_ideas(idea_description)

        if similar_ideas:
            # Present to user and get confirmation
            confirmation = await self.present_duplicates_for_review(similar_ideas)
            if not confirmation.proceed:
                return {"status": "merged", "merged_with": confirmation.selected_idea}

        # Step 2: Search for related stories
        related_stories = await self.search_related_stories(idea_description)

        # Step 3: AI-powered link suggestions
        suggested_links = await self.suggest_story_links(
            idea_description,
            related_stories
        )

        # Step 4: User approval
        approved_links = await self.get_user_approval_for_links(suggested_links)

        # Step 5: Create idea and links
        idea_ticket = await self.create_jira_idea(idea_description)
        await self.link_stories(idea_ticket.key, approved_links)

        # Step 6: Notify
        await self.notify_slack(idea_ticket, approved_links)

        return {"status": "created", "idea_key": idea_ticket.key}
```

**Deduplication Strategy:**
- Use Jira JQL with text search: `project = ECD AND issuetype = Idea AND text ~ "keywords"`
- Calculate similarity score using TF-IDF or embeddings
- Threshold: > 80% similarity = likely duplicate, present to user

**Story Linking Logic:**
- Search for stories mentioning similar keywords
- Check stories in same epic or with related labels
- Use AI (Claude MCP) to evaluate semantic relevance
- Present top 5-10 most relevant stories for user approval

**UI/UX:**
- Slack interactive blocks for user confirmations
- Show duplicate ideas with clickable Jira links
- Inline approval buttons for suggested story links
- Progress indicators for each workflow step

**Benefits:**
- Prevents duplicate ideas before they're created
- Automatically discovers related work
- Improves idea-to-execution traceability
- Reduces manual PM work for linking tickets
- Creates audit trail of decision-making

**Implementation Priority:** Medium (after standup automation is stable)

**Future Enhancement - Web UI:**
Consider building a dedicated web interface for idea ingestion workflow:
- React/Vue.js frontend for better UX than Slack blocks
- Visual similarity comparison (side-by-side duplicate view)
- Drag-and-drop story linking interface
- Real-time progress indicators and notifications
- Admin dashboard for workflow analytics
- Could integrate with Jira as a plugin or standalone web app

---

### 0.1. Customer Call Transcript Processing & Insight Extraction

**Goal:** Automatically process customer call transcripts to extract actionable ideas, feature requests, and insights.

---

### 0.3. AI Capability Guardrails & Validation Layer

**Goal:** Prevent false-positive commitments by implementing pre-execution capability validation for AI operations.

**Problem Statement:**
Currently, AI agents (including Claude Code and this PM agent) may confidently state they'll perform actions they cannot actually execute:
- "Yes! I'll read that Figma file and update the description" (when Figma access not available)
- "I'll analyze the video recording from the call" (when video processing isn't supported)
- "I'll update the database directly" (when only API access is permitted)

This creates user frustration when promised actions fail silently or with cryptic errors.

**Proposed Solution:**
Implement a **Capability Validation Layer** that checks tool/feature availability before making commitments.

**Architecture:**

```python
class CapabilityRegistry:
    """
    Central registry of available capabilities with metadata
    """
    def __init__(self):
        self.capabilities = {
            "jira_read": {"available": True, "tools": ["mcp__atlassian__*"]},
            "jira_write": {"available": True, "tools": ["editJiraIssue", "createJiraIssue"]},
            "figma_read": {"available": False, "alternative": "Request Figma export/screenshot"},
            "video_analysis": {"available": False, "alternative": "Process transcript instead"},
            "direct_db_access": {"available": False, "alternative": "Use API endpoints"},
            "slack_post": {"available": True, "tools": ["post_slack_message.py"]},
            "git_operations": {"available": True, "tools": ["Bash(git:*)"]},
            "file_read": {"available": True, "tools": ["Read", "mcp__filesystem__*"]},
            "file_write": {"available": True, "tools": ["Write", "Edit"]},
            # ... more capabilities
        }

    def check_capability(self, requested_action: str) -> CapabilityCheck:
        """
        Check if requested action is feasible

        Returns:
            CapabilityCheck with:
            - can_do: bool (is this action possible?)
            - alternative: str (if not, what CAN we do instead?)
            - tools_required: list[str] (what tools would be used?)
        """
        pass

class GuardrailValidator:
    """
    Pre-execution validator that checks capabilities before committing
    """
    def __init__(self, capability_registry: CapabilityRegistry):
        self.registry = capability_registry

    async def validate_plan(self, user_request: str, proposed_plan: str) -> ValidationResult:
        """
        Analyze proposed plan and validate all actions are feasible

        Example:
            User: "Read the Figma file and update Jira description"
            Proposed Plan: "1. Read Figma file, 2. Extract requirements, 3. Update Jira"

            Validation Result:
            {
                "valid": False,
                "issues": [
                    {
                        "action": "Read Figma file",
                        "can_do": False,
                        "reason": "Figma API access not configured",
                        "alternative": "I can process a Figma screenshot/export instead"
                    }
                ],
                "suggested_response": "I cannot directly read Figma files. Would you like me to:\n1. Process a Figma screenshot you provide?\n2. Work from requirements doc instead?\n3. Skip Figma and proceed with Jira update?"
            }
        """
        pass
```

**User-Facing Behavior:**

**Before (Current - False Positives):**
```
User: "Update the Jira ticket based on the Figma designs"
AI: "Sure! I'll read the Figma file, extract requirements, and update ECD-817."
[Attempts to read Figma]
[Fails silently or with error]
AI: "I encountered an error accessing Figma..."
User: 😤 (frustrated - AI promised something it couldn't deliver)
```

**After (With Guardrails):**
```
User: "Update the Jira ticket based on the Figma designs"
AI: "I cannot directly access Figma files. However, I can help in these ways:
     1. If you provide a Figma screenshot/PDF export, I can analyze it
     2. I can update the Jira ticket based on written requirements you provide
     3. I can create a template ticket description for you to fill in design details

     Which approach would you prefer?"
User: 😊 (appreciates honesty and clear alternatives)
```

**Implementation Strategy:**

1. **Phase 1: Capability Manifest**
   - Create `capabilities.json` listing all available tools and constraints
   - Include tool dependencies (e.g., Slack posting requires SLACK_BOT_TOKEN)
   - Mark experimental/unreliable features

2. **Phase 2: Pre-Flight Validation**
   - Before responding with a plan, validate all proposed actions
   - Check tool availability, permissions, API keys
   - Test critical paths (e.g., "Can I actually write to Jira right now?")

3. **Phase 3: Graceful Degradation**
   - Always provide alternatives when primary path unavailable
   - Rank alternatives by similarity to original request
   - Explain why primary approach won't work (educate user)

4. **Phase 4: Runtime Monitoring**
   - Track capability check accuracy (false positives/negatives)
   - Alert on frequently requested but unavailable capabilities
   - Suggest new tool integrations based on demand

**Example Capability Checks:**

```python
# Example 1: Figma Request
check_result = validator.check_capability("read_figma_file", "https://figma.com/file/...")
# Returns: {
#   "available": False,
#   "reason": "Figma MCP server not configured",
#   "alternatives": [
#       "Process Figma export (PNG/PDF)",
#       "Use Figma REST API if design token provided",
#       "Work from written spec instead"
#   ]
# }

# Example 2: Video Analysis
check_result = validator.check_capability("analyze_video", "meeting_recording.mp4")
# Returns: {
#   "available": False,
#   "reason": "Video processing not supported",
#   "alternatives": [
#       "Process transcript of video (if available)",
#       "Analyze screenshots from key moments",
#       "Work from meeting notes instead"
#   ]
# }

# Example 3: Database Write (Restricted)
check_result = validator.check_capability("update_database", "UPDATE projects SET...")
# Returns: {
#   "available": False,
#   "reason": "Direct database access restricted for safety",
#   "alternatives": [
#       "Use Jira API to update project fields",
#       "Create migration script for review",
#       "Propose SQL changes for DBA approval"
#   ]
# }
```

**Benefits:**

1. **Trust & Transparency**
   - Users know upfront what's possible vs. not possible
   - No surprise failures after time investment
   - Clear documentation of agent limitations

2. **Better User Experience**
   - Proactive alternative suggestions
   - Faster resolution (no wasted attempts)
   - Educational (users learn tool capabilities)

3. **Reliability Metrics**
   - Track capability check accuracy
   - Identify missing tools/integrations to prioritize
   - Reduce error rates and retry loops

4. **Debuggability**
   - Clear logs of why actions were rejected
   - Audit trail of capability decisions
   - Easier troubleshooting for admins

**Integration Points:**

- **Claude Code Integration:** Add capability checks before file operations, MCP calls
- **PM Agent Integration:** Validate Jira/Slack operations before attempting
- **Electron App (Future):** UI to show capability status (green/yellow/red indicators)
- **Documentation:** Auto-generate "What I Can Do" documentation from manifest

**Monitoring & Analytics:**

```python
# Track capability check results
capability_analytics = {
    "figma_access_requests": 45,  # High demand = consider Figma MCP
    "video_analysis_requests": 12,
    "direct_db_requests": 3,  # Low demand = OK to keep restricted
    "false_positives": 2,  # Said we could, but failed
    "false_negatives": 0,  # Said we couldn't, but actually could have
}
```

**Implementation Priority:** High (addresses core user experience issue)

**Estimated Effort:** 2-3 days
- Day 1: Build capability registry and validation logic
- Day 2: Integrate into Claude Code and PM Agent prompts
- Day 3: Testing, refinement, documentation

**Success Metrics:**
- Zero false-positive commitments (promises agent can't keep)
- >90% user satisfaction with alternative suggestions
- Reduced error-related support tickets

**Workflow:**
1. **Ingest Call Transcript** - Upload or fetch transcript from call recording system
2. **AI Analysis** - Use Claude to extract:
   - Customer pain points and frustrations
   - Feature requests (explicit and implicit)
   - Product feedback and satisfaction signals
   - Competitive mentions
   - Usage patterns and workflows
3. **Categorize Insights** - Classify into:
   - Feature ideas (potential Jira ideas)
   - Bug reports (potential Jira bugs)
   - Product feedback (sentiment analysis)
   - Competitive intelligence
   - Customer success opportunities
4. **Search for Duplicates** - Check if similar ideas/feedback already exist
5. **Generate Jira Ideas** - Auto-create ideas with:
   - Customer quote as description
   - Extracted context and rationale
   - Customer metadata (company, role, account tier)
   - Links to transcript/recording
6. **Link Related Work** - Connect to existing stories/epics
7. **Notify Stakeholders** - Alert PM/product team with summary
8. **Aggregate Insights** - Track themes across multiple calls

**Technical Approach:**
```python
class TranscriptProcessor:
    async def process_transcript(self, transcript: str, metadata: dict):
        # Step 1: AI extraction
        insights = await self.extract_insights(transcript)
        # {
        #   "pain_points": [...],
        #   "feature_requests": [...],
        #   "bugs": [...],
        #   "competitive_mentions": [...]
        # }

        # Step 2: For each feature request
        for feature in insights["feature_requests"]:
            # Check for duplicates
            similar = await self.search_similar_ideas(feature["description"])

            if not similar:
                # Create Jira idea
                idea = await self.create_jira_idea(
                    summary=feature["title"],
                    description=self._format_idea_from_transcript(
                        feature,
                        transcript,
                        metadata
                    ),
                    customer_context=metadata
                )

                # Link related stories
                await self.link_related_stories(idea, feature)

        # Step 3: Generate summary report
        return await self.generate_insights_report(insights, metadata)
```

**AI Prompting Strategy:**
```
Analyze this customer call transcript and extract:

1. PAIN POINTS: What problems are they experiencing?
2. FEATURE REQUESTS: What capabilities are they asking for?
3. WORKAROUNDS: How are they solving problems today?
4. COMPETITIVE MENTIONS: What alternatives did they mention?
5. SATISFACTION SIGNALS: Are they happy/frustrated? Why?

For each feature request, provide:
- Title (concise, 1 sentence)
- Description (what they want and why)
- Priority signal (how urgently did they need this?)
- Customer quote (verbatim request from transcript)

Format as structured JSON.
```

**Data Sources:**
- Zoom/Teams call recordings & transcripts
- Sales call notes
- Customer support tickets with chat logs
- User interviews and research sessions
- Product demo feedback sessions

**Output Format:**
```json
{
  "call_metadata": {
    "date": "2025-11-19",
    "customer": "ACME Corp",
    "participants": ["Sarah (Customer)", "Alex (Sales)", "Jordan (PM)"],
    "duration": "45min"
  },
  "extracted_insights": {
    "feature_requests": [
      {
        "title": "Bulk evidence import via CSV",
        "description": "Customer needs to migrate 500+ evidence items from old system",
        "priority_signal": "high",
        "customer_quote": "We have hundreds of documents we need to import...",
        "jira_idea_created": "ECD-850",
        "similar_existing_ideas": ["ECD-720"]
      }
    ],
    "pain_points": [...],
    "competitive_intel": [...]
  },
  "recommended_actions": [
    "Create idea ECD-850 for bulk import",
    "Follow up on pricing concern mentioned",
    "Schedule technical deep-dive for integration"
  ]
}
```

**Benefits:**
- Capture customer voice directly into product roadmap
- Prevent lost ideas from verbal conversations
- Quantify feature demand (how many customers asked for X?)
- Improve sales-to-product feedback loop
- Build evidence-based roadmap (customer quotes as proof)
- Track competitive intelligence systematically

**Integration Points:**
- Jira (idea creation)
- Slack (stakeholder notifications)
- CRM (customer metadata)
- Call recording platforms (Zoom, Gong, Chorus)
- Product analytics (correlate requests with usage data)

**Implementation Priority:** Medium-High (valuable for customer-driven roadmap)

**Original Claude Code Prototype:** This workflow was originally explored using Claude Code for transcript analysis. Can be adapted to autonomous PM agent architecture.

---

### 0.2. Electron Desktop App with Hybrid Cloud Architecture

**Goal:** Ship a customer-facing desktop application that simplifies setup, handles authentication, and provides flexible deployment options (local, cloud, or hybrid).

**Problem Solved:**
- Complex OAuth/MCP credential setup
- Re-authentication friction when tokens expire
- Always-on requirement vs. user machine availability
- Multi-user coordination and team-wide reporting
- Subscription enforcement and license management

**Hybrid Architecture:**
```
┌─────────────────────────────────────────┐
│  ELECTRON DESKTOP APP (Local)          │
├─────────────────────────────────────────┤
│  • Configuration & Setup UI             │
│  • OAuth/MCP credential management      │
│  • Real-time workflow testing           │
│  • Log viewer & debugging               │
│  • On-demand workflows (run now)        │
│  • License activation & validation      │
└──────────────┬──────────────────────────┘
               │ API/WebSocket
               ▼
┌─────────────────────────────────────────┐
│  CLOUD SERVICE (Heroku/Railway)         │
├─────────────────────────────────────────┤
│  • Scheduled automations (cron jobs)    │
│  • Daily standups (9am weekdays)        │
│  • Hourly SLA monitoring                │
│  • Team-wide reporting                  │
│  • Centralized audit logs               │
│  • Subscription validation API          │
└─────────────────────────────────────────┘
```

**Desktop App Features:**

1. **Setup Wizard:**
   - Step 1: Jira OAuth (opens browser, captures callback)
   - Step 2: Slack OAuth (opens browser, captures callback)
   - Step 3: MCP Server Setup (guided configuration)
   - Step 4: Test Connections (live validation with status indicators)
   - Step 5: Choose Deployment Mode (local/cloud/hybrid)

2. **Main Dashboard:**
   - Workflows Tab: Run on-demand (instant feedback)
   - Scheduled Jobs Tab: View/edit cron schedules
   - Logs Tab: Real-time streaming with filtering
   - Settings Tab: Credentials, preferences, team config
   - Subscription Tab: Status, billing, license management

3. **Credential Management:**
   - Native OS keychain integration (macOS Keychain, Windows Credential Manager)
   - Automatic token refresh with user prompts
   - Visual indicators for expired credentials
   - One-click re-authentication flows

**Deployment Modes:**

```yaml
local_only:
  description: All workflows run on user's machine
  use_case: Testing, small teams, consultant use
  pros: No cloud costs, full control, data stays local
  cons: No scheduled automation, machine must be on

cloud_only:
  description: User provides cloud credentials, app configures instance
  use_case: Production, 24/7 automation, team collaboration
  pros: Always-on, scheduled jobs, team-wide visibility
  cons: Cloud costs, credential management in cloud

hybrid:
  description: On-demand local + scheduled cloud
  use_case: Best of both worlds
  pros: Instant local testing + reliable scheduled automation
  cons: Most complex setup, requires both
```

**Subscription & License Enforcement:**

```python
class LicenseValidator:
    """Validate subscription and lock features if expired"""

    def validate_license(self, license_key: str) -> dict:
        """Phone home to licensing server every 24h"""
        response = requests.post(
            "https://licensing.yoursaas.com/validate",
            json={
                "license_key": license_key,
                "machine_id": get_machine_id(),  # Prevent sharing
                "version": APP_VERSION,
                "deployment_mode": "hybrid"
            }
        )

        if not response.ok:
            return {
                "valid": False,
                "reason": "Subscription expired",
                "grace_period_remaining": 0
            }

        # Cache valid license for 24h
        # Offline grace period: 7 days
        return {
            "valid": True,
            "tier": "professional",
            "expires_at": "2025-12-19",
            "features_enabled": ["standup", "sla", "transcripts"]
        }

    def lock_features_if_expired(self):
        """Show 'Subscription Required' overlay, disable workflows"""
        # Allow: License renewal, settings view
        # Block: All workflow execution, cloud deployment
```

**Revenue Model (Three-Tier):**

1. **Free/Open Source Core** - CLI scripts only
   - Target: Developers, self-hosters
   - Price: Free
   - Features: All core workflows, no GUI

2. **Desktop App (Professional)** - $29/month
   - Target: Individual PMs, consultants
   - Features: Electron GUI, local execution, license key
   - Limitations: Single user, no cloud deployment

3. **Managed Cloud (Enterprise)** - $99/month
   - Target: Teams, always-on automation
   - Features: Hosted cloud service + desktop app + team features
   - Includes: 24/7 uptime, centralized logs, multi-user support

**Technical Stack:**

```javascript
// Electron main process
{
  "framework": "Electron",
  "ui": "React + Tailwind CSS",
  "state": "Redux or Zustand",
  "python_bridge": "zeromq or child_process",
  "auth": "OAuth PKCE flow",
  "storage": "electron-store + OS keychain",
  "updates": "electron-updater (auto-update)",
  "analytics": "PostHog or Mixpanel"
}
```

**User Flow Example:**

1. User downloads Desktop App (.dmg/.exe)
2. Launches app, greeted with setup wizard
3. Clicks "Connect Jira" → Opens browser → OAuth flow → Credentials stored in keychain
4. Clicks "Connect Slack" → Same OAuth flow
5. Clicks "Setup MCP" → Guided form (CloudId, etc.) → Test connection
6. Chooses deployment: "Hybrid" (local + cloud)
7. App provisions Heroku instance automatically (or user provides API key)
8. App syncs encrypted credentials to cloud instance
9. Dashboard shows "All systems operational"
10. User runs standup workflow on-demand (instant feedback)
11. User schedules daily standup at 9am (runs in cloud)
12. Logs stream in real-time from both local and cloud

**Subscription Enforcement:**

- Desktop app validates license every 24 hours
- Requires internet connection at least once every 7 days
- Expired subscriptions show overlay with renewal link
- All workflows disabled except license renewal
- Auto-update mechanism can revoke access remotely
- Tie to machine ID to prevent sharing (allow 2 devices per license)

**Benefits:**

- **Simplified Setup:** GUI wizard vs. manual .env editing
- **Better Auth UX:** Visual OAuth flows, auto-refresh, keychain storage
- **Flexible Deployment:** Choose what fits your needs
- **Monetization:** Clear upgrade path from free to paid
- **Customer Support:** Easier to debug with GUI logs viewer
- **Enterprise Appeal:** Data stays local option + managed cloud option

**Implementation Priority:** Low-Medium (after core workflows are stable and proven)

**Next Steps for Implementation:**
1. Prototype Electron app with basic UI
2. Implement OAuth callback handler
3. Build setup wizard flow
4. Integrate with existing Python scripts via child_process
5. Design license validation API
6. Create subscription payment flow (Stripe integration)
7. Build auto-update mechanism
8. Package for distribution (.dmg, .exe, .AppImage)

---

### 1. Daily Standup Automation with Ping Notification

**Goal:** Automated daily standup that sends summary to Ethan with health check confirmation.

**Requirements:**
- Run automatically every weekday at 9 AM ET
- Execute full 5-part standup workflow (sprint analysis, code-ticket gaps, developer audit, timesheet analysis, SLA monitoring)
- Send summary report to Slack and/or Email
- Include health check status: "✅ PM Agent running without errors" or "⚠️ Issues detected"
- Ping Ethan directly for awareness and acknowledgment

**Implementation Options:**

#### Option A: Heroku Scheduler (Recommended)
```yaml
# Procfile
worker: python run_agent.py standup --notify-ethan
clock: python clock.py  # APScheduler for precise timing
```

**Benefits:**
- Zero-config scheduling via Heroku Scheduler add-on
- Automatic error recovery
- Centralized logs in Heroku dashboard
- Can deploy directly from git

#### Option B: GitHub Actions (Free Alternative)
```yaml
# .github/workflows/daily-standup.yml
name: Daily Standup
on:
  schedule:
    - cron: '0 14 * * 1-5'  # 9 AM ET = 2 PM UTC
jobs:
  standup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: python run_agent.py standup --notify-ethan
```

**Benefits:**
- Free for public repos
- Easy to monitor via GitHub Actions UI
- No separate infrastructure needed

#### Option C: AWS Lambda + EventBridge
**Benefits:**
- Serverless, pay per execution
- Highly scalable
- AWS integration for future features

**Status:** ⏳ Pending Heroku deployment (see item #2)

**Notification Format:**
```
📊 Daily Standup Report - 2025-10-21
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@ethan_dm

✅ PM Agent Health: Running without errors

📈 Sprint Health:
  • 12 tickets in progress
  • 5 completed today
  • 3 SLA violations detected

⚠️ Action Items:
  1. ECD-123 - Stale PR (3 days no update)
  2. ECD-456 - Blocked ticket needs escalation

Full report: [Confluence Link] | [Jira Dashboard]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply 'ok' to acknowledge or 'details' for full report
```

**Related Files:**
- `.claude/workflows/standup-orchestrator.md`
- `run_agent.py`
- New: `clock.py` (for scheduling)
- New: `notify.py` (for Ethan pings)

---

### 2. Heroku Deployment for Autonomous Operation

**Goal:** Deploy PM agent to Heroku for 24/7 autonomous operation with git-based deployment.

**Requirements:**
- Deploy to Heroku dyno (hobby tier $7/month or free tier with scheduler)
- Automatic deployment from GitHub main branch
- Store secrets in Heroku Config Vars
- Logging to Heroku logs and/or external service
- Health checks and error alerting
- Easy rollback capability

**Setup Steps:**

1. **Create Heroku App**
   ```bash
   heroku create citemed-pm-agent
   heroku addons:create heroku-postgresql:hobby-dev  # If needed
   heroku addons:create scheduler:standard  # Free scheduler
   ```

2. **Configure Environment Variables**
   ```bash
   heroku config:set ATLASSIAN_SERVICE_ACCOUNT_EMAIL=xxx
   heroku config:set ATLASSIAN_SERVICE_ACCOUNT_TOKEN=xxx
   heroku config:set SLACK_BOT_TOKEN=xxx
   heroku config:set CITEMED_WEB_PATH=/app/citemed_web  # Adjust for Heroku
   ```

3. **Create Required Files:**
   - `Procfile` - Define dyno commands
   - `runtime.txt` - Python version (3.11)
   - `requirements.txt` - Already exists
   - `app.json` - Heroku app manifest
   - `heroku.yml` - Docker config (optional)

4. **Set Up Git Deployment**
   ```bash
   git remote add heroku https://git.heroku.com/citemed-pm-agent.git
   git push heroku main
   ```

5. **Configure Scheduler**
   ```bash
   heroku addons:open scheduler
   # Add job: python run_agent.py standup --notify-ethan
   # Frequency: Daily at 9:00 AM ET
   ```

**Monitoring:**
- Heroku dashboard for dyno health
- Heroku logs via `heroku logs --tail`
- Slack notifications for errors
- Weekly health report to Ethan

**Cost Estimate:**
- Hobby dyno: $7/month
- Scheduler: Free
- Postgres (if needed): $9/month
- **Total: ~$16/month**

**Alternative:** Use free tier with worker dyno that runs scheduler internally.

**Status:** ⏳ Ready to implement

---

## Medium Priority

### 3. PR Review Context Awareness Enhancement

**Goal:** Make PR review process aware of previous review feedback when new commits are pushed, so the agent can verify that previously requested changes were addressed.

**Problem Statement:**
Currently, when new code is pushed to a PR:
- ✅ The bot detects new commits and triggers a re-review (working)
- ✅ The bot reviews the new code changes (working)
- ❌ The bot is NOT aware of what was previously requested to be changed
- ❌ Cannot verify if previous feedback was addressed

**Desired Behavior:**
When reviewing a PR with new commits, the agent should:
1. Fetch all previous review comments from Bitbucket
2. Parse previous feedback to identify issues that were flagged
3. Include context about previously requested changes in the review prompt
4. Specifically check if those issues were addressed in the new commits
5. Provide a structured review with sections:
   - **Previously Requested Changes:** ✅ Implemented / ❌ Not Yet Addressed / ⚠️ Partially Addressed
   - **New Code Review:** Standard review of new changes

**Implementation Plan:**

**Step 1: Fetch Previous Comments**
```python
# In bots/bitbucket_monitor.py or new pr_review module
def get_previous_review_feedback(repo: str, pr_id: int) -> dict:
    """
    Fetch and parse all previous review comments from this PR

    Returns:
        {
            "critical_issues": [...],
            "suggestions": [...],
            "questions": [...],
            "approvals": [...]
        }
    """
    # Use existing BitbucketAPI methods
    all_comments = self.api.get_comments(workspace=self.workspace, repo=repo, pr_id=pr_id)
    inline_activity = self.api.get_activity(workspace=self.workspace, repo=repo, pr_id=pr_id)

    # Filter for bot's own previous reviews
    # Parse comment structure to extract issues and their severity
    # Return structured feedback
```

**Step 2: Structure Previous Feedback**
```python
def parse_review_comments(comments: list) -> dict:
    """
    Extract structured feedback from previous review comments

    Identifies:
    - Issue descriptions and file/line references
    - Severity levels (critical, high, medium, low)
    - Categories (security, performance, style, logic)
    - Status (resolved via replies, still open)
    """
    parsed_feedback = {
        "unresolved_issues": [],
        "security_concerns": [],
        "performance_issues": [],
        "code_quality_suggestions": []
    }

    for comment in comments:
        # Look for bot's previous comments (identify by author or format)
        if comment["author"]["display_name"] == "CiteMed AI (Remington)":
            # Parse structured review format
            # Extract issue items
            parsed_feedback["unresolved_issues"].append({
                "file": extract_file_reference(comment),
                "line": extract_line_reference(comment),
                "description": extract_issue_description(comment),
                "severity": extract_severity(comment),
                "timestamp": comment["created_on"]
            })

    return parsed_feedback
```

**Step 3: Enhanced Review Prompt**
```python
def build_context_aware_review_prompt(pr_data: dict, diff: str, previous_feedback: dict) -> str:
    """
    Build Claude prompt that includes previous review context
    """
    prompt = f"""You are reviewing Pull Request #{pr_data['id']}: {pr_data['title']}

## PREVIOUS REVIEW FEEDBACK (from last review iteration)

The following issues were identified in a previous review of this PR:

{format_previous_issues(previous_feedback)}

## YOUR TASK

1. **Verify Previous Issues:** Check if the above issues have been addressed in the new commits
2. **New Code Review:** Review the new changes for any additional issues

## NEW CODE CHANGES

{diff[:50000]}

## REQUIRED OUTPUT FORMAT

Provide your review in this exact JSON format:
{{
  "previous_issues_status": [
    {{
      "issue": "Description of previously flagged issue",
      "status": "implemented" | "not_addressed" | "partially_addressed",
      "notes": "Details about how it was addressed (or why not)"
    }}
  ],
  "new_issues": [
    {{
      "severity": "critical" | "high" | "medium" | "low",
      "category": "security" | "performance" | "logic" | "style",
      "file": "path/to/file.py",
      "line": 123,
      "description": "What the issue is",
      "suggestion": "How to fix it"
    }}
  ],
  "overall_assessment": "summary of PR quality and readiness"
}}
"""
    return prompt
```

**Step 4: Structured Review Output**
The review comment posted to Bitbucket should have two clear sections:

```markdown
## 🔄 Previously Requested Changes

✅ **IMPLEMENTED:**
- [ECD-585] Security: SQL injection vulnerability fixed in `database/queries.py:45`
- [ECD-586] Performance: N+1 query eliminated in `api/views.py:120`

❌ **NOT YET ADDRESSED:**
- [ECD-587] Code Quality: `process_data()` function still exceeds 100 lines (security/utils.py:200)
- [ECD-588] Logic: Edge case for empty array not handled (validators.py:78)

⚠️ **PARTIALLY ADDRESSED:**
- [ECD-589] Error handling added but doesn't log errors to Sentry yet (handlers.py:45)

---

## 🆕 New Code Review

**Critical Issues (2):**
1. **[NEW]** Security: Unvalidated user input in new feature (feature.py:34)
   - **Risk:** XSS vulnerability
   - **Fix:** Add input sanitization before rendering

**Suggestions (3):**
[Standard new review items...]

---

**Overall Assessment:** PR has addressed 2 of 4 previous issues. 2 new critical issues introduced. Requires additional work before approval.
```

**Database Schema Addition (Optional):**
```sql
-- Track review history per PR for analytics
CREATE TABLE pr_review_history (
    repo TEXT NOT NULL,
    pr_id INTEGER NOT NULL,
    commit_sha TEXT NOT NULL,
    review_iteration INTEGER NOT NULL,
    issues_identified INTEGER DEFAULT 0,
    issues_from_previous INTEGER DEFAULT 0,
    issues_resolved INTEGER DEFAULT 0,
    issues_new INTEGER DEFAULT 0,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (repo, pr_id, commit_sha)
);
```

**Files to Modify:**

1. **`bots/bitbucket_monitor.py`**
   - Add `get_previous_review_feedback()` method
   - Add `parse_review_comments()` method
   - Update `poll_for_pr_updates()` to include previous feedback

2. **Create new file: `bots/pr_review_engine.py`**
   - Core review logic extracted from monitor
   - `perform_code_review()` function
   - `build_context_aware_review_prompt()` function
   - `format_review_comment()` function

3. **Update: `.claude/workflows/pr-review-automation.md`**
   - Add context awareness flow diagram
   - Update review process steps
   - Document new prompt structure

4. **Optional: `src/database/pr_review_db.py`**
   - Track review iterations and issue resolution
   - Analytics on review effectiveness

**Available Bitbucket API Methods (Confirmed Working):**
- ✅ `get_comments(workspace, repo, pr_id)` - Fetch all PR comments
- ✅ `get_activity(workspace, repo, pr_id)` - Fetch PR activity including inline comments
- ✅ `add_comment(workspace, repo, pr_id, message)` - Post review comments
- ✅ `get_pull_request(workspace, repo, pr_id)` - Get PR metadata
- ✅ `get_diff(workspace, repo, pr_id)` - Get code changes

**Benefits:**

1. **Continuity:** Reviews build on previous feedback rather than repeating same issues
2. **Developer Experience:** Clear visibility into what was fixed vs still needs work
3. **Accountability:** Track if developers address critical issues or ignore them
4. **Efficiency:** Reduces back-and-forth by explicitly checking requested changes
5. **Quality Metrics:** Can measure how often previous issues get resolved

**Success Metrics:**
- % of previously flagged issues that get resolved in next iteration
- Average number of review iterations per PR (should decrease over time)
- Developer satisfaction with review process (via survey)
- Reduction in "repeat" issues across PRs (bot learns what team needs)

**Implementation Priority:** Medium (valuable enhancement, not blocking core functionality)

**Estimated Effort:** 2-3 days
- Day 1: Implement comment fetching and parsing logic
- Day 2: Build context-aware review prompt and output formatting
- Day 3: Testing, refinement, documentation

**Status:** 📋 Planned - Ready for implementation when bandwidth available

**Date Added:** 2025-11-20

**Related Files:**
- `bots/bitbucket_monitor.py` - Existing PR monitoring (foundation)
- `.claude/workflows/pr-review-automation.md` - Original design doc
- `.claude/workflows/pr-git-branch-analysis.md` - Git analysis workflow

**Original Request Context:**
> User: "when new code is pushed, it runs the PR review process again (good), but it should also know what specifically was requested to change so it can add that to what it's reviewing"

---

w### 3.1. Migration File Scope Validation in PR Reviews

**Goal:** Automatically validate that database migration files included in PRs are directly relevant to the feature being developed, preventing scope creep and migration conflicts.

**Problem Statement:**
Developers sometimes commit migration files that are:
- Unrelated to the ticket/feature in the PR
- Auto-generated from model changes made for testing
- Leftover from branch merges or rebases
- Conflicting with other team members' migrations

This causes:
- Migration conflicts during deployment
- Confusion about which migrations belong to which feature
- Rollback complications when features are reverted
- Database schema drift from intended design

**Desired Behavior:**
When a PR includes migration files (e.g., Django migrations, Alembic migrations), the bot should:

1. **Detect Migration Files:**
   - Identify files matching migration patterns:
     - Django: `*/migrations/00XX_*.py`
     - Alembic: `alembic/versions/*.py`
     - Prisma: `prisma/migrations/*/migration.sql`

2. **Parse Migration Content:**
   - Extract operations: `CREATE TABLE`, `ALTER TABLE`, `ADD COLUMN`, etc.
   - Identify affected models/tables
   - Detect migration dependencies

3. **Compare to PR Scope:**
   - Read PR title and Jira ticket description
   - Extract feature scope keywords (e.g., "user authentication", "payment processing")
   - Check if migration operations align with stated scope

4. **Validation Rules:**
   - ✅ **PASS:** Migration modifies `User` table + PR is about "user profile feature" = relevant
   - ⚠️ **WARN:** Migration modifies `Payment` table + PR is about "user profile feature" = possibly unrelated
   - 🚨 **FAIL:** Migration contains 5+ unrelated table changes = likely auto-generated or scope creep

5. **Request Clarification:**
   - Post comment asking developer to explain unrelated migrations
   - Suggest creating separate PR for infrastructure changes
   - Request removal of auto-generated migrations

**Example Review Comment:**

```markdown
## ⚠️ Migration File Scope Concern

I detected database migrations in this PR that may be unrelated to the stated feature scope:

**PR Scope:** ECD-543 - Add user profile photo upload feature

**Migration Files:**
1. ✅ `users/migrations/0045_user_profile_photo.py`
   - Adds `profile_photo` field to User model ✓ (directly related)

2. ⚠️ `payments/migrations/0023_add_stripe_customer_id.py`
   - Adds `stripe_customer_id` to Payment model
   - **Question:** Is this related to profile photo feature? Seems unrelated.

3. 🚨 `core/migrations/0012_auto_20251120_1430.py`
   - Auto-generated migration with multiple model changes
   - Modifies: Product, Order, Category (5 tables)
   - **Concern:** Appears to be auto-generated from unrelated model changes

**Recommendations:**
1. Keep migration #1 (directly related to PR scope)
2. Remove migration #2 or create separate PR if it's a genuine feature
3. Remove migration #3 (likely auto-generated) and investigate why models changed

**Action Required:**
Please confirm these migrations are intentional and explain their relationship to this feature. If they're unrelated, please:
- Stash/remove unrelated migrations
- Ensure your models match the migration baseline
- Create separate PRs for infrastructure changes

Reply in this thread to clarify or confirm removal. ✅
```

**Implementation Plan:**

**Step 1: Detect Migration Files in Diff**
```python
def detect_migration_files(diff: str) -> list[dict]:
    """
    Parse git diff to find migration files

    Returns:
        [
            {
                "path": "users/migrations/0045_user_profile_photo.py",
                "framework": "django",
                "operations": ["AddField"],
                "tables": ["users_user"],
                "is_auto_generated": False
            }
        ]
    """
    migration_patterns = {
        "django": r"[\w/]+/migrations/\d+_[\w]+\.py",
        "alembic": r"alembic/versions/[\w]+\.py",
        "prisma": r"prisma/migrations/\d+_[\w]+/migration\.sql"
    }

    # Parse diff for added files matching patterns
    # Extract migration content from diff
    # Parse migration operations (AddField, CreateModel, etc.)
    pass
```

**Step 2: Analyze Migration Scope**
```python
def analyze_migration_scope(migration: dict, pr_context: dict) -> dict:
    """
    Compare migration changes to PR scope

    Args:
        migration: Parsed migration data
        pr_context: {
            "title": "Add user profile photo upload",
            "description": "Allows users to upload profile photos...",
            "ticket": "ECD-543",
            "jira_description": "Full Jira ticket text"
        }

    Returns:
        {
            "relevance_score": 0.85,  # 0-1 scale
            "is_related": True,
            "confidence": "high",
            "reasoning": "Migration adds profile_photo field, PR is about profile photos",
            "flags": []
        }
    """
    # Use Claude to analyze semantic relationship
    # Check for keyword matches (table names in PR description)
    # Detect auto-generated migrations (generic names, many operations)
    pass
```

**Step 3: Scope Validation Heuristics**
```python
VALIDATION_RULES = {
    "auto_generated_markers": [
        "auto_", "_auto", "squashed", "merge_", "temp_"
    ],
    "suspicious_patterns": {
        "too_many_tables": 3,  # More than 3 tables modified = suspicious
        "no_description": True,  # Migration without docstring
        "generic_name": ["update", "changes", "fixes"]
    },
    "scope_keywords_extract": True,  # Extract keywords from PR/Jira
    "table_match_threshold": 0.7  # 70% of tables should relate to PR scope
}
```

**Step 4: Integration into PR Review**
```python
def perform_code_review_with_migration_check(repo: str, pr_id: int):
    """Enhanced PR review including migration validation"""

    # Standard review process...
    diff = get_pr_diff(repo, pr_id)
    pr_context = get_pr_context(repo, pr_id)

    # NEW: Migration validation
    migrations = detect_migration_files(diff)
    migration_issues = []

    for migration in migrations:
        analysis = analyze_migration_scope(migration, pr_context)

        if analysis["relevance_score"] < 0.5:
            migration_issues.append({
                "severity": "high" if analysis["relevance_score"] < 0.3 else "medium",
                "migration_file": migration["path"],
                "concern": "Possibly unrelated to PR scope",
                "reasoning": analysis["reasoning"],
                "action": "Request clarification or removal"
            })

        if migration["is_auto_generated"]:
            migration_issues.append({
                "severity": "high",
                "migration_file": migration["path"],
                "concern": "Auto-generated migration detected",
                "action": "Review and regenerate with proper scope"
            })

    # Include migration issues in review comment
    if migration_issues:
        review_comment += format_migration_section(migration_issues)
```

**Claude Semantic Analysis Prompt:**
```python
migration_analysis_prompt = f"""
Analyze if this database migration is relevant to the PR scope.

PR SCOPE:
- Title: {pr_title}
- Ticket: {ticket_key}
- Description: {pr_description}

MIGRATION:
- File: {migration_path}
- Operations: {migration_operations}
- Tables: {affected_tables}

QUESTION: Is this migration directly related to the PR feature scope?

Provide:
1. relevance_score (0.0-1.0)
2. is_related (yes/no)
3. reasoning (1-2 sentences)
4. recommendation (keep/clarify/remove)

JSON format:
{{
  "relevance_score": 0.85,
  "is_related": true,
  "reasoning": "Migration adds profile_photo field, PR implements profile photo upload",
  "recommendation": "keep"
}}
"""
```

**Django-Specific Checks:**
```python
def check_django_migration(migration_file: str) -> dict:
    """Additional Django-specific validation"""

    with open(migration_file) as f:
        content = f.read()

    # Check for auto-generated indicators
    is_auto = "_auto" in migration_file or "# Auto-generated" in content

    # Count operations
    operations_count = content.count("migrations.")

    # Check for squashed migrations
    is_squashed = "squashed" in content.lower()

    # Extract dependencies
    dependencies = re.findall(r"dependencies = \[(.*?)\]", content, re.DOTALL)

    return {
        "is_auto_generated": is_auto,
        "operations_count": operations_count,
        "is_squashed": is_squashed,
        "seems_suspicious": is_auto or operations_count > 5 or is_squashed
    }
```

**Benefits:**

1. **Prevents Migration Conflicts:** Catch unrelated migrations before merge
2. **Cleaner Git History:** Each PR contains only relevant changes
3. **Easier Rollbacks:** Feature rollback doesn't affect unrelated migrations
4. **Developer Education:** Teaches best practices for migration management
5. **Deployment Safety:** Reduces risk of unexpected schema changes

**Edge Cases to Handle:**

1. **Infrastructure PRs:** PRs explicitly for database refactoring (allow multiple tables)
2. **Dependency Chains:** Migration depends on another PR's migration
3. **Squashed Migrations:** Legitimate consolidation of old migrations
4. **Test Data Migrations:** Data migrations for seeding test data
5. **Hotfixes:** Emergency migrations that bypass normal process

**Configuration:**
```yaml
# .claude/config/migration-validation.yml
enabled: true
frameworks:
  - django
  - alembic
  - prisma

validation:
  max_unrelated_tables: 2
  auto_generated_warning: true
  require_migration_description: false

exceptions:
  - pattern: "infrastructure/*"  # Allow infra PRs
  - ticket_prefix: "DB-"  # Database tickets exempt
  - label: "migration-refactor"  # Labeled PRs exempt
```

**Success Metrics:**
- Reduction in migration conflicts during deployment
- Fewer PRs with unrelated migration files
- Faster PR review cycle (clear scope = faster approval)
- Developer feedback on usefulness of checks

**Implementation Priority:** Medium (valuable addition to PR review automation)

**Estimated Effort:** 1-2 days
- Day 1: Build migration file detection and parsing
- Day 2: Implement scope analysis and validation rules

**Status:** 📋 Planned - To be implemented alongside PR review context awareness

**Date Added:** 2025-11-20

**Related Enhancements:**
- Section 3: PR Review Context Awareness Enhancement (primary feature)
- Automated code quality checks
- Jira ticket-to-code alignment validation

**Original Request:**
> User: "we should do a check to make sure that migration files committed are directly relevant to the scoped feature -- otherwise request clarification and their removal most likely"

---

### 4. Agent Dashboard & Observability Portal

**Goal:** Web-based dashboard for monitoring agent health, viewing reports, and tracking metrics.

**Features:**
- **Real-Time Status:** Current agent health, running jobs, last heartbeat
- **Activity Feed:** Recent PR reviews, Jira comments, SLA escalations
- **Metrics & Analytics:**
  - Time saved calculations
  - SLA compliance trends
  - Developer productivity graphs
  - Sprint velocity charts
- **Report Archive:** Access to daily standups, weekly reports, audits
- **Manual Controls:** Trigger ad-hoc analyses, run specific workflows
- **Alert Configuration:** Set custom thresholds for notifications

**Technology Options:**

#### Option A: Simple Flask Dashboard
```python
# dashboard/app.py
from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    # Read from .claude/data/ databases
    # Display metrics and recent activity
    return render_template('dashboard.html')
```

**Benefits:**
- Lightweight, easy to deploy alongside PM agent
- Can read directly from SQLite databases
- Simple authentication with environment variables

#### Option B: Grafana + Prometheus
**Benefits:**
- Professional-grade dashboards
- Time-series metrics
- Built-in alerting
- Industry standard

#### Option C: Retool / Internal Tool Builder
**Benefits:**
- No-code dashboard builder
- Quick to set up
- Built-in database connections
- Mobile-friendly

**Status:** 📋 Planned - Nice to have for enhanced visibility

**Related Files:**
- New: `dashboard/` directory
- New: `scripts/export_metrics.py` - Export data for dashboard
- `.claude/data/` - Data source for all metrics

---

### 4. Slack Logging Channel with Hourly Heartbeats

**Goal:** Dedicated Slack channel for agent logging, heartbeats, and automated reports.

**Channel:** `#pm-agent-logs` (to be created)

**Features:**

**Hourly Heartbeat (Every hour, 9am-5pm CST weekdays):**
```
🤖 PM Agent Heartbeat - 2:00 PM CST
━━━━━━━━━━━━━━━━━━━━━━━
✅ Status: Operational
📊 Last hour activity:
  • 3 Jira comments monitored
  • 1 PR review completed
  • 0 SLA violations detected

⚡ Service uptime: 99.8%
🔗 Full status: /health
```

**Daily Standup Report (Weekdays at 9am CST):**
```
📊 Daily Standup Report - Nov 11, 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@ethan

✅ PM Agent Health: Running without errors

📈 Sprint Health:
  • 12 tickets in progress
  • 5 completed today
  • 3 SLA violations detected

⚠️ Action Items:
  1. ECD-123 - Stale PR (3 days no update)
  2. ECD-456 - Blocked ticket needs escalation

Full report: [Link to detailed analysis]
```

**Weekly Summary (Mondays at 9am CST):**
```
📊 Weekly PM Agent Report - Week of Nov 4-8
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Agent Activities:
  • 42 Jira comments (3.5 hrs saved)
  • 15 PR reviews (7.5 hrs saved)
  • 8 SLA escalations (2 hrs saved)

📈 Total Time Saved: 30 hours
   ROI: 5x productivity multiplier

✅ Team Performance:
  • All weekly standups submitted on time
  • Average PR review time: 18 hours
  • Zero critical SLA violations
```

**Error/Warning Alerts (Real-time):**
```
⚠️ PM Agent Warning
━━━━━━━━━━━━━━━━━
Service: Bitbucket Monitor
Issue: Rate limit approaching (80%)
Action: Reducing poll frequency temporarily
Time: 2:34 PM CST
```

**Implementation:**

1. **Create Slack Channel:**
   ```bash
   # Manually create #pm-agent-logs channel
   # Add to .env: SLACK_PM_AGENT_LOG_CHANNEL=C123456789
   ```

2. **Heartbeat Script:**
   ```python
   # scripts/heartbeat.py
   import os
   from slack_sdk import WebClient

   def post_heartbeat():
       """Post hourly heartbeat to logging channel"""
       client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
       channel = os.getenv("SLACK_PM_AGENT_LOG_CHANNEL")

       # Gather metrics from last hour
       metrics = gather_hourly_metrics()

       # Format message
       message = format_heartbeat(metrics)

       # Post to Slack
       client.chat_postMessage(channel=channel, text=message)
   ```

3. **Schedule Heartbeats:**
   ```python
   # clock.py - Add to existing scheduler
   from apscheduler.schedulers.blocking import BlockingScheduler

   sched = BlockingScheduler()

   # Hourly heartbeat (weekdays 9am-5pm CST)
   @sched.scheduled_job('cron', day_of_week='mon-fri', hour='9-17', minute=0)
   def hourly_heartbeat():
       os.system('python scripts/heartbeat.py')
   ```

4. **Update Report Destinations:**
   - Daily standup → `#pm-agent-logs` + DM to Ethan
   - Weekly summary → `#pm-agent-logs` + `#weekly-standup`
   - All errors/warnings → `#pm-agent-logs`

**Benefits:**
- **Centralized Logging:** All agent activity in one place
- **Transparency:** Team can see what agent is doing
- **Early Detection:** Hourly heartbeats catch issues quickly
- **Audit Trail:** Historical record of all agent actions
- **No External Tools:** Uses existing Slack infrastructure

**Status:** 🚀 Ready to implement (high priority for visibility)

**Related Files:**
- New: `scripts/heartbeat.py`
- New: `.claude/templates/heartbeat-message.md`
- Update: `clock.py` - Add hourly schedule
- Update: `.env.example` - Add SLACK_PM_AGENT_LOG_CHANNEL

---

### 5. Weekly PM Agent Status Report & Employee Timesheet Validation

**Goal:** Weekly report on PM agent activities and validation of employee weekly standup submissions.

**Requirements:**
- **Weekly Report Generation:**
  - Run every Monday morning (after weekly standup submission deadline)
  - Summarize all PM agent activities from the past week
  - Calculate time saved by automation vs. manual PM work
  - Post to `SLACK_WEEKLY_STANDUP_CHANNEL_ID` (from .env)

- **Employee Timesheet Validation:**
  - Monitor weekly standup submissions (Friday → Monday evening CST deadline)
  - Verify submission format includes hours for tasks
  - Flag late submissions or missing weekly standups
  - Request clarification when format is incorrect or unclear
  - Identify potentially unproductive patterns

- **Metrics to Track:**
  - Number of Jira comments posted (time saved: ~5 min each)
  - Number of PR reviews automated (time saved: ~30 min each)
  - Number of SLA violations detected and escalated (time saved: ~15 min each)
  - Number of developer audits performed (time saved: ~60 min each)
  - Weekly standups processed and validated (time saved: ~10 min each)
  - Total estimated time saved per week

- **Report Format:**
```
📊 Weekly PM Agent Report - Week of Nov 4-8, 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 AGENT ACTIVITIES SUMMARY

✅ Automated Tasks:
  • 42 Jira comments posted (3.5 hours saved)
  • 15 PR reviews completed (7.5 hours saved)
  • 8 SLA escalations triggered (2 hours saved)
  • 5 daily standups orchestrated (5 hours saved)
  • 12 developer productivity audits (12 hours saved)

📈 TOTAL TIME SAVED THIS WEEK: 30 hours
   (vs. ~6 hours/week for manual PM work)
   ROI: 5x productivity multiplier

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 WEEKLY STANDUP VALIDATION

✅ On-Time Submissions (5/5):
  • Mohamed - Submitted Monday 9:00 AM CST ✓
  • Ahmed - Submitted Monday 10:30 AM CST ✓
  • Thanh - Submitted Sunday 8:00 PM CST ✓
  • Valentin - Submitted Monday 11:00 AM CST ✓
  • Josh - Submitted Monday 2:00 PM CST ✓

🔍 Format Issues Detected:
  • None this week

⚠️ Productivity Flags:
  • None this week

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 WEEKLY INSIGHTS

Top Achievements:
  1. All developers submitted weekly standups on time
  2. Zero SLA violations escalated to Level 3+
  3. Average PR review time: 18 hours (under 24hr SLA)

Areas for Improvement:
  1. 2 PRs had minor code quality issues flagged
  2. 1 blocked ticket needed follow-up after 3 days

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Week Focus:
  - Continue monitoring sprint velocity
  - Validate test coverage on new PRs
  - Track holiday schedule adjustments
```

**Implementation:**
1. Create `scripts/weekly_report.py`
2. Add `SLACK_WEEKLY_STANDUP_CHANNEL_ID` to .env
3. Schedule via Heroku Scheduler: `python run_agent.py weekly-report`
4. Parse weekly standup submissions from Slack channel
5. Validate format: "Task Name - X hours"
6. Flag missing hours or unclear descriptions
7. Calculate time saved based on task counts
8. Post comprehensive report to weekly standup channel

**Status:** ⏳ Pending implementation

**Related Files:**
- New: `scripts/weekly_report.py`
- New: `.claude/templates/weekly-report.md`
- New: `.claude/workflows/weekly-validation.md`
- `.env` - Add SLACK_WEEKLY_STANDUP_CHANNEL_ID

---

### 6. Clarification-Before-Action Workflow

**Goal:** Agent proposes plan and waits for user approval before executing changes.

**Current Problem:**
- Agent sometimes makes changes immediately without user confirmation
- No opportunity for user to refine approach before execution
- Can lead to rework if agent misunderstands intent

**Desired Behavior:**
1. User requests action (e.g., "refine this ticket", "update sprint")
2. Agent analyzes request and drafts a concise plan
3. Agent posts plan as a **threaded reply** (Jira comment thread or Slack thread)
4. Agent waits for user response:
   - "approved" → Execute plan
   - "changes: [feedback]" → Revise plan
   - "cancel" → Discard
5. Agent executes approved plan and posts confirmation

**Example Flow:**

**User (Jira comment on ECD-123):**
> @remington refine this ticket with the latest design specs

**Agent (threaded reply on ECD-123):**
```
🔍 Here's my plan to refine ECD-123:

1. Review design specs from Figma link in description
2. Extract user flows and acceptance criteria
3. Update ticket description with:
   - Detailed user story statement
   - Technical scope from design
   - Acceptance criteria checklist
4. Add story points estimate based on complexity
5. Update labels: add "design-ready", "frontend"

Reply 'approved' to proceed, or 'changes: [feedback]' to adjust the plan.
```

**User (in thread):**
> changes: also add the API endpoint requirements from the backend doc

**Agent (in thread):**
```
📝 Updated plan (Revision 2):

1. Review design specs from Figma link
2. Review backend API doc for endpoint requirements  ← ADDED
3. Extract user flows and acceptance criteria
4. Update ticket description with:
   - Detailed user story statement
   - Technical scope (frontend + backend API)  ← UPDATED
   - API endpoint specifications  ← ADDED
   - Acceptance criteria checklist
5. Add story points estimate
6. Update labels: add "design-ready", "frontend", "backend"  ← UPDATED

Reply 'approved' to proceed.
```

**User (in thread):**
> approved

**Agent (in thread):**
```
✅ Executing plan now...

[Agent updates ECD-123 description, adds labels, estimates points]

✅ Complete! I've updated ECD-123 with:
- Comprehensive description from design + backend specs
- 8 acceptance criteria
- Story points: 8
- Labels: design-ready, frontend, backend

Link: https://citemed.atlassian.net/browse/ECD-123
```

**Implementation Requirements:**

**For Jira:**
- Use Atlassian MCP `addCommentToJiraIssue` to create threaded replies
- Track parent comment ID for threading context
- Poll for replies in the specific comment thread (not just all comments)
- Use database to track pending approval state per thread

**For Slack:**
- Use `thread_ts` parameter in `chat.postMessage` to create threaded replies
- Reply to user in their thread, not as general channel message
- Use Slack Bolt's thread handling capabilities
- Monitor thread for "approved"/"changes:"/"cancel" responses

**Database Schema Addition:**
```sql
CREATE TABLE pending_actions (
    action_id TEXT UNIQUE NOT NULL,  -- UUID
    source TEXT NOT NULL,             -- 'jira' | 'slack'
    source_id TEXT NOT NULL,          -- issue_key | thread_ts
    parent_comment_id TEXT,           -- For Jira threading
    thread_ts TEXT,                   -- For Slack threading
    action_type TEXT NOT NULL,        -- 'refine_ticket' | 'sprint_move' | 'pm_request'
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    original_request TEXT NOT NULL,
    proposed_plan TEXT NOT NULL,
    status TEXT DEFAULT 'pending',    -- 'pending' | 'approved' | 'cancelled'
    created_at TIMESTAMP,
    approved_at TIMESTAMP,
    executed_at TIMESTAMP
);

CREATE TABLE action_revisions (
    action_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    proposed_plan TEXT NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP
);
```

**Workflow Integration:**
- Modify orchestrator to detect action requests
- Generate plan using Claude Code
- Post plan to thread and store in database
- Poll thread for approval responses (similar to PM approval workflow)
- Execute action on approval
- Log execution results

**Benefits:**
- User has control over all agent actions
- Reduces rework from misunderstood requests
- Builds trust through transparency
- Allows iterative refinement of approach
- Maintains audit trail of decisions

**Challenges:**
- Requires reliable threading in both Jira and Slack
- Adds latency (user must approve)
- Need timeout handling (auto-cancel after N days?)
- Polling overhead for monitoring threads

**Status:** 📋 Planned - Long-term improvement for enhanced user control

**Related Files:**
- New: `.claude/workflows/clarification-workflow.md`
- Update: `src/orchestration/claude_code_orchestrator.py` - Add `propose_action()` method
- Update: `src/database/` - Add `pending_actions_db.py`
- New: `.claude/templates/action-plan-template.md`

---

### 7. Multi-Repository Code Analysis Enhancement

**Current State:** Agent can read citemed_web codebase via Filesystem MCP.

**Enhancement:** Add support for analyzing:
- `word_addon` repository
- Any new microservices/repositories
- External dependencies and API integrations

**Implementation:**
- Extend Filesystem MCP paths in `.mcp.json`
- Update developer auditor to scan multiple repos
- Add repo-specific SLA rules (e.g., word_addon has different PR review SLAs)

---

### 4. Advanced PR Review Automation

**Goal:** Automatically review PRs for code quality, test coverage, and sprint alignment.

**Features:**
- Detect PRs without linked Jira tickets
- Flag PRs missing tests
- Analyze code complexity and suggest refactoring
- Auto-comment on PRs with checklist reminders
- Track PR approval times for SLA monitoring

**Dependencies:**
- Bitbucket API integration (already partially available)
- Or GitHub API if migrating to GitHub

---

### 5. Developer Performance Insights Dashboard

**Goal:** Weekly developer performance reports with trends and insights.

**Metrics:**
- Code commit frequency and quality
- PR review participation
- Ticket completion rate
- Code complexity trends
- SLA compliance percentage

**Delivery:**
- Confluence page with charts
- Slack summary every Friday
- Monthly team retrospective report

---

### 6. Intelligent Sprint Planning Assistant

**Goal:** AI-powered sprint planning recommendations.

**Features:**
- Analyze historical velocity
- Suggest ticket prioritization based on dependencies
- Warn about overcommitment
- Recommend ticket assignments based on developer skillsets
- Predict sprint completion probability

---

### 7. Confluence Documentation Auto-Generation

**Goal:** Automatically generate and update sprint documentation.

**Content Types:**
- Sprint retrospectives
- Developer productivity reports
- SLA compliance summaries
- Technical debt tracking
- Architecture decision records (ADRs)

**Implementation:**
- Use Confluence CLI (already built)
- Template-based generation
- Weekly automated updates

---

## Low Priority / Nice-to-Have

### 8. Slack Bot Interactive Commands

**Goal:** Allow team to interact with PM agent via Slack commands.

**Commands:**
```
/pm-sprint-status           # Get current sprint health
/pm-ticket ECD-123          # Get ticket details
/pm-sla-check               # Run SLA audit now
/pm-assign @dev ECD-123     # Assign ticket
/pm-escalate ECD-123        # Manual escalation
```

---

### 9. Jira Ticket Auto-Creation from Slack

**Goal:** Create Jira tickets directly from Slack messages.

**Usage:**
```
@pm-bot create ticket: Fix login bug
Priority: High
Assignee: @mohamed
```

---

### 10. Code Complexity Alerts

**Goal:** Alert when code complexity exceeds thresholds.

**Metrics:**
- Cyclomatic complexity
- Function length
- Number of parameters
- Nesting depth

**Action:**
- Flag in PR reviews
- Create tech debt tickets automatically

---

### 11. External Integration: Sentry / Error Tracking

**Goal:** Monitor production errors and create Jira tickets for critical issues.

**Workflow:**
1. Sentry detects error spike
2. PM agent receives webhook
3. Auto-creates Jira ticket with priority
4. Assigns to on-call developer
5. Sends Slack alert

---

### 12. Time Zone Intelligence

**Goal:** Handle multi-timezone teams (future growth).

**Features:**
- Adjust SLA deadlines for timezones
- Schedule standups at appropriate local times
- Track "business hours" per developer

---

## Infrastructure Improvements

### 13. Backup & Disaster Recovery

**Goal:** Ensure data persistence and recovery.

**Components:**
- Backup `.claude/data/` daily to cloud storage (S3/GCS)
- Version control all configs and scripts
- Automated restore procedure
- Test recovery monthly

---

### 14. Logging & Observability

**Goal:** Comprehensive logging and monitoring.

**Tools:**
- Structured JSON logging
- Centralized log aggregation (Logtail, Papertrail, CloudWatch)
- Error rate dashboards
- Performance metrics
- Audit trail for all actions

---

### 15. Testing & CI/CD

**Goal:** Automated testing and deployment.

**Components:**
- ✅ Pytest test suite (COMPLETE - 39 tests)
- GitHub Actions CI pipeline
- Pre-commit hooks
- Integration testing
- Load testing for API limits

---

### 16. Security Enhancements

**Goal:** Harden security and compliance.

**Improvements:**
- Rotate API tokens automatically
- Implement least-privilege access
- Audit logging for all API calls
- Secrets management (Vault, AWS Secrets Manager)
- SOC2 compliance documentation

---

## Research & Exploration

### 17. AI-Powered Code Review

**Goal:** Use LLMs to review code quality beyond static analysis.

**Capabilities:**
- Suggest architectural improvements
- Detect potential bugs
- Recommend design patterns
- Identify security vulnerabilities

---

### 18. Natural Language Jira Queries

**Goal:** Allow team to query Jira using natural language.

**Example:**
```
"Show me all high-priority bugs assigned to Mohamed updated in the last week"
→ Translates to JQL: project = ECD AND priority = High AND assignee = mohamed AND type = Bug AND updated >= -7d
```

---

### 19. Predictive Analytics

**Goal:** Machine learning models for sprint prediction.

**Models:**
- Sprint completion probability
- Ticket time-to-completion prediction
- Developer workload optimization
- Risk assessment for deadlines

---

## Completed Items

### ✅ Atlassian CLI Backup Tool (COMPLETE)
**Completed:** 2025-10-21
- Built standalone `jira-cli` and `confluence-cli` tools
- Comprehensive pytest test suite (39 tests)
- Full CRUD operations for issues, comments, transitions
- Serves as backup when MCP is unavailable

### ✅ ECD-539 Story Breakdown (COMPLETE)
**Completed:** 2025-10-21
- Generated 16 subtask stories from implementation plan
- Created manual backup files in markdown format
- Ready for Jira creation via CLI or manual input

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-10-21 | Build Atlassian CLI as MCP backup | MCP reliability issues; need guaranteed API access |
| 2025-10-21 | Deploy to Heroku vs AWS Lambda | Heroku simpler for git-based deployment and cron jobs |
| 2025-10-21 | Daily standup automation as high priority | User requirement for autonomous operation with health checks |

---

## Notes & Considerations

1. **Read-Only Citemed Codebase:** Agent must never modify `citemed_web/` - analysis only
2. **Business Hours:** ET timezone, weekdays only for SLA calculations
3. **Team Size:** Currently 5 developers; scale considerations for future growth
4. **Cost Constraints:** Optimize for free/low-cost solutions where possible
5. **User Preference:** Ethan wants morning notifications, not evening

---

**Related Documents:**
- `.claude/CLAUDE.md` - Main agent instructions
- `.claude/workflows/` - Current workflow implementations
- `docs/BOT_INTEGRATION_SUMMARY.md` - Integration architecture
- `docs/FUTURE_ENHANCEMENTS.md` - Original enhancement ideas

---

## Sprint Planning & Refinement Automation

### Sprint Refinement Monitoring

**Goal:** Automated pre-sprint readiness checks to ensure all tickets are properly refined before sprint planning.

**Requirements:**
- Run automatically 2-3 days before sprint ends (to prep for next sprint)
- Check all tickets in backlog/next sprint for:
  - **Missing story point estimates** - Flag tickets without effort estimates
  - **Incomplete descriptions** - Detect tickets with < 100 characters or missing acceptance criteria
  - **Missing epics/labels** - Ensure proper categorization
  - **Unrefined tickets** - Status = "Draft" or "Needs Refinement"
  - **Technical debt items** - Separate tracking for maintenance vs features

**Notifications:**
- Post refinement report to Slack #sprint-planning channel
- Tag PM/Tech Lead for tickets needing attention
- Provide suggested actions (e.g., "Schedule refinement session for 5 unestimated tickets")

**Example Report:**
```
📋 Sprint Refinement Check - Sprint 23 Prep

⚠️ 8 tickets need attention before sprint planning:

Unestimated (5):
  • ECD-523: Implement OAuth flow
  • ECD-524: Refactor database schema
  [...]

Missing Descriptions (2):
  • ECD-530: Fix bug (only 15 chars)
  [...]

Action Items:
  ✅ Schedule refinement session with tech lead
  ✅ Assign story points to 5 tickets
```

### Capacity Planning & Workload Distribution

**Goal:** Automated capacity planning that distributes work evenly across developers based on estimates and availability.

**Requirements:**
- **Developer Capacity Tracking:**
  - Track individual developer velocity (avg story points per sprint)
  - Account for PTO/holidays from calendar
  - Consider ongoing commitments (support rotations, meetings)
  - Calculate available hours per developer for upcoming sprint

- **Workload Analysis:**
  - Sum estimated hours/points for all tickets in sprint
  - Compare total workload vs total team capacity
  - Flag over/under-allocation
  - Detect skill mismatches (backend-heavy sprint with mostly frontend devs)

- **Smart Distribution Suggestions:**
  - Suggest ticket assignments based on:
    - Developer expertise (past tickets, code ownership)
    - Current workload balance
    - Dependency chains (blockers/prerequisites)
  - Propose rebalancing if one developer has 150% capacity, another has 50%

**Example Report:**
```
📊 Sprint 24 Capacity Planning

Team Capacity: 120 hours (5 devs × 24h)
Sprint Workload: 135 hours (OVERCOMMITTED by 15h)

Developer Allocation:
  • Mohamed: 28h (117% capacity) - ⚠️ Overloaded
  • Ahmed: 18h (75% capacity) - ✅ Balanced
  • Thanh: 32h (133% capacity) - ⚠️ Overloaded
  • Valentin: 22h (92% capacity) - ✅ Balanced
  • Josh: 35h (146% capacity) - 🚨 Severely overloaded

Recommendations:
  1. Remove ECD-540 (8h) from sprint - defer to Sprint 25
  2. Reassign ECD-542 from Josh → Ahmed (7h rebalance)
  3. Schedule pair programming session for ECD-530 (complex)

Adjusted Forecast: 120h total, all devs 90-110% capacity ✅
```

**Integration Points:**
- Read story point estimates and time estimates from Jira custom fields
- Access developer calendars (Google Calendar API or manual `.env` config)
- Historical velocity data from past sprints (stored in `.claude/data/sprints/`)
- Skill matrix config file (`.claude/data/developers/skills.json`)

**Implementation Phases:**
1. **Phase 1:** Basic capacity math (total hours vs estimates)
2. **Phase 2:** Per-developer allocation tracking
3. **Phase 3:** Smart suggestions based on skills and past work
4. **Phase 4:** Auto-rebalancing with ML-based recommendations

---

**Date Added:** 2025-11-18
**Priority:** Medium (implement after core standup automation is stable)
**Estimated Effort:** 2-3 weeks (for full Phase 1-3 implementation)

---

## 🚀 Architecture Migration: Claude Code → LangGraph Deep Agents

**Date Added:** 2025-12-04
**Priority:** High (foundational architecture improvement)
**Estimated Effort:** 2-3 weeks

### Problem Statement

Current architecture uses Claude Code CLI via subprocess:
```python
# Current approach - subprocess to Claude CLI
result = subprocess.run(
    ["claude", "-p", "--output-format", "text"],
    input=prompt,
    timeout=600
)
response = result.stdout
```

**Issues:**
1. **MCP OAuth Fragility** - Atlassian MCP drops frequently, requires interactive `/mcp` reconnection
2. **No Observability** - Can't see token usage, intermediate reasoning, or debug decisions
3. **Subprocess Overhead** - Spawning external process adds latency
4. **Limited Customization** - Can't inject logic between agent reasoning steps
5. **Error Handling** - Parsing stderr vs proper Python exceptions

### Proposed Solution: LangGraph Deep Agents

LangGraph's new **Deep Agents** framework is explicitly "inspired by Claude Code" and provides:

| Feature | Deep Agents | Claude Code |
|---------|-------------|-------------|
| Planning/Todo | ✅ `write_todos` | ✅ Built-in |
| File System | ✅ `read_file`, `write_file` | ✅ Built-in |
| Subagents | ✅ `task` tool | ✅ Task tool |
| Memory | ✅ Persistent | ✅ `.claude/` |
| Shell Commands | ✅ Yes | ✅ Bash tool |
| **Observability** | ✅ LangSmith | ❌ Limited |
| **Custom Middleware** | ✅ Yes | ❌ No |
| **Model Flexibility** | ✅ Any model | ❌ Claude only |
| **Direct API Calls** | ✅ In-process | ❌ Subprocess |

### Architecture Comparison

**Current (Claude Code):**
```
PMAgentService
  └── Polling Threads (Slack/Jira/Bitbucket)
        └── ClaudeCodeOrchestrator
              └── subprocess("claude -p ...")
                    └── MCP OAuth (fragile)
                          └── Atlassian API
```

**Proposed (Deep Agents):**
```
PMAgentService
  └── Polling Threads (Slack/Jira/Bitbucket)  ← UNCHANGED
        └── DeepAgentOrchestrator
              └── LangGraph Agent (in-process)
                    └── Custom Tools (direct REST)
                          └── Atlassian API (service account token)
```

### Key Benefit: Ditch MCP OAuth, Use Service Account

**Problem:** MCP OAuth tokens expire, require browser re-auth, connection drops randomly.

**Solution:** Use Atlassian API tokens (never expire) with direct REST calls:

```python
# Service account - never expires, no browser auth needed
email = "pm-agent@citemed.com"
api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}
```

### Required LangChain Tools to Build

All tools will wrap direct REST API calls (no MCP dependency):

#### Jira Tools (Priority: Critical)

| Tool Name | REST Endpoint | Purpose |
|-----------|---------------|---------|
| `search_jira` | `POST /rest/api/3/search` | JQL queries for sprint analysis, SLA checks |
| `get_jira_issue` | `GET /rest/api/3/issue/{key}` | Get full issue details |
| `create_jira_issue` | `POST /rest/api/3/issue` | Create stories/bugs/epics |
| `update_jira_issue` | `PUT /rest/api/3/issue/{key}` | Update fields (status, assignee, etc.) |
| `add_jira_comment` | `POST /rest/api/3/issue/{key}/comment` | Post comments with @mentions (ADF) |
| `get_jira_comments` | `GET /rest/api/3/issue/{key}/comment` | Read comment history |
| `transition_jira_issue` | `POST /rest/api/3/issue/{key}/transitions` | Change status (In Progress → Done) |
| `get_jira_transitions` | `GET /rest/api/3/issue/{key}/transitions` | Get available status transitions |
| `link_jira_issues` | `POST /rest/api/3/issueLink` | Link related tickets |
| `get_jira_sprint` | `GET /rest/agile/1.0/sprint/{id}` | Get sprint details |
| `get_sprint_issues` | `GET /rest/agile/1.0/sprint/{id}/issue` | Get all issues in sprint |
| `lookup_jira_user` | `GET /rest/api/3/user/search` | Find user account IDs for @mentions |

#### Confluence Tools (Priority: Medium)

| Tool Name | REST Endpoint | Purpose |
|-----------|---------------|---------|
| `get_confluence_page` | `GET /wiki/api/v2/pages/{id}` | Read documentation |
| `create_confluence_page` | `POST /wiki/api/v2/pages` | Create sprint reports |
| `update_confluence_page` | `PUT /wiki/api/v2/pages/{id}` | Update documentation |
| `search_confluence` | `GET /wiki/rest/api/search` | Search for related docs |
| `add_confluence_comment` | `POST /wiki/api/v2/footer-comments` | Add page comments |

#### Bitbucket Tools (Priority: Medium)

| Tool Name | REST Endpoint | Purpose |
|-----------|---------------|---------|
| `get_pull_requests` | `GET /2.0/repositories/{workspace}/{repo}/pullrequests` | List open PRs |
| `get_pr_diff` | `GET /2.0/repositories/{workspace}/{repo}/pullrequests/{id}/diff` | Get code changes |
| `get_pr_comments` | `GET /2.0/repositories/{workspace}/{repo}/pullrequests/{id}/comments` | Read review history |
| `add_pr_comment` | `POST /2.0/repositories/{workspace}/{repo}/pullrequests/{id}/comments` | Post reviews |
| `get_commits` | `GET /2.0/repositories/{workspace}/{repo}/commits` | Check commit activity |
| `get_branches` | `GET /2.0/repositories/{workspace}/{repo}/refs/branches` | Check branch status |

#### Slack Tools (Priority: High)

| Tool Name | API Method | Purpose |
|-----------|------------|---------|
| `post_slack_message` | `chat.postMessage` | Send standup reports, alerts |
| `post_slack_thread` | `chat.postMessage` (thread_ts) | Reply in threads |
| `get_channel_history` | `conversations.history` | Read recent messages |
| `get_thread_replies` | `conversations.replies` | Get thread context |
| `lookup_slack_user` | `users.lookupByEmail` | Find user IDs for mentions |

#### Utility Tools (Priority: High)

| Tool Name | Purpose |
|-----------|---------|
| `read_file` | Read local files (.claude/, team_roster.json, etc.) |
| `write_file` | Write reports to .claude/data/ |
| `get_current_time` | Business hours calculations, SLA checks |
| `calculate_business_days` | SLA deadline calculations |

### Implementation Plan

#### Phase 1: Build Tool Layer (Week 1)
- [ ] Create `src/tools/jira_tools.py` with all Jira REST wrappers
- [ ] Create `src/tools/confluence_tools.py` with Confluence wrappers
- [ ] Create `src/tools/bitbucket_tools.py` with Bitbucket wrappers
- [ ] Create `src/tools/slack_tools.py` with Slack wrappers
- [ ] Create `src/tools/utils.py` with utility functions
- [ ] Add comprehensive error handling and retry logic
- [ ] Write pytest tests for each tool

#### Phase 2: Build Deep Agent Orchestrator (Week 2)
- [ ] Install `deepagents` package
- [ ] Create `src/orchestration/deep_agent_orchestrator.py`
- [ ] Migrate agent prompts from `.claude/agents/*.md` to system prompts
- [ ] Configure middleware: TodoList, Filesystem, SubAgent
- [ ] Implement subagent architecture:
  - `jira_manager_agent` - Jira operations
  - `sla_monitor_agent` - SLA checks and escalations
  - `pm_drafter_agent` - Story/bug/epic drafting
  - `standup_orchestrator_agent` - Daily standup coordination
- [ ] Add LangSmith tracing for observability

#### Phase 3: Integration & Migration (Week 3)
- [ ] Update `PMAgentService` to use `DeepAgentOrchestrator`
- [ ] Parallel run: Keep Claude Code as fallback during testing
- [ ] Migrate polling handlers to use new orchestrator
- [ ] Update standup workflow to use Deep Agents
- [ ] Performance testing and optimization
- [ ] Remove Claude Code dependency once stable

### Code Examples

**Tool Definition:**
```python
# src/tools/jira_tools.py
from langchain_core.tools import tool
import requests
import os

CLOUD_ID = "67bbfd03-b309-414f-9640-908213f80628"
BASE_URL = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}"

def get_auth_headers():
    email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
    token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

@tool
def search_jira(jql: str, max_results: int = 50) -> dict:
    """
    Search Jira issues using JQL query.

    Args:
        jql: JQL query string (e.g., "project = ECD AND sprint in openSprints()")
        max_results: Maximum number of results to return

    Returns:
        Dict with issues array and metadata
    """
    response = requests.post(
        f"{BASE_URL}/rest/api/3/search",
        headers=get_auth_headers(),
        json={"jql": jql, "maxResults": max_results}
    )
    response.raise_for_status()
    return response.json()

@tool
def add_jira_comment(issue_key: str, comment: str, mention_ids: list[str] = None) -> dict:
    """
    Add a comment to a Jira issue with optional @mentions.

    Args:
        issue_key: Jira issue key (e.g., "ECD-123")
        comment: Comment text
        mention_ids: List of Atlassian account IDs to mention

    Returns:
        Created comment data
    """
    # Build ADF body with mentions
    body = build_adf_comment(comment, mention_ids)

    response = requests.post(
        f"{BASE_URL}/rest/api/3/issue/{issue_key}/comment",
        headers=get_auth_headers(),
        json={"body": body}
    )
    response.raise_for_status()
    return response.json()
```

**Deep Agent Setup:**
```python
# src/orchestration/deep_agent_orchestrator.py
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from src.tools.jira_tools import search_jira, add_jira_comment, get_jira_issue
from src.tools.slack_tools import post_slack_message

class DeepAgentOrchestrator:
    def __init__(self):
        self.model = ChatAnthropic(model="claude-sonnet-4-20250514")

        # Load agent instructions
        with open(".claude/agents/jira-manager.md") as f:
            self.jira_system_prompt = f.read()

        # Create specialized agents
        self.jira_agent = create_deep_agent(
            model=self.model,
            tools=[search_jira, add_jira_comment, get_jira_issue],
            system_prompt=self.jira_system_prompt
        )

    async def process_jira_comment(self, issue_key: str, comment: str, commenter: str):
        """Process incoming Jira comment with full reasoning"""

        result = await self.jira_agent.ainvoke(
            {"messages": [{
                "role": "user",
                "content": f"New comment on {issue_key} from {commenter}: {comment}"
            }]},
            config={"callbacks": [langsmith_tracer]}  # Full observability
        )

        return result["messages"][-1].content
```

### Success Metrics

| Metric | Current (Claude Code) | Target (Deep Agents) |
|--------|----------------------|---------------------|
| MCP reconnections/week | 5-10 | 0 |
| Response latency | 5-15s | 2-5s |
| Observable reasoning | ❌ | ✅ |
| Error traceability | Low | High |
| Token cost visibility | ❌ | ✅ |

### Rollback Plan

Keep Claude Code orchestrator as fallback:
```python
class PMAgentService:
    def __init__(self):
        try:
            self.orchestrator = DeepAgentOrchestrator()
            print("✅ Using Deep Agents orchestrator")
        except Exception as e:
            print(f"⚠️ Falling back to Claude Code: {e}")
            self.orchestrator = ClaudeCodeOrchestrator()
```

### Dependencies

```
# requirements.txt additions
deepagents>=0.1.0
langchain-anthropic>=0.3.0
langchain-core>=0.3.0
langsmith>=0.2.0
```

### Related Files

- `src/orchestration/claude_code_orchestrator.py` - Current implementation (to be deprecated)
- `src/orchestration/deep_agent_orchestrator.py` - New implementation
- `src/tools/` - New directory for LangChain tools
- `.claude/agents/*.md` - Agent prompts (migrate to system prompts)

---

## 🤖 Autonomous Booking Assistant via Email

**Added:** 2025-12-10
**Category:** Deep Agent / LangGraph
**Priority:** P2 (Feature Enhancement)
**Effort:** Medium-High (1-2 weeks)

### Overview

An autonomous meeting scheduling agent that consumes the user's MS Outlook inbox (with permission) and can be emailed tasks like "try and set a meeting with Jim and Jennifer."

### Capabilities

1. **Email Consumption** - Monitor dedicated inbox for scheduling requests
2. **Availability Discovery** - Query calendars for participant availability
3. **Priority Handling** - Understand boss's preferred time slots and meeting urgency
4. **Calendar Invite Generation** - Send professional calendar invites
5. **Follow-up Loop** - Continue following up if people don't respond based on reminder SLAs

### Implementation Approach

**Architecture:** LangGraph Deep Agent with email/calendar tools

**Tools Required:**
- MS Graph API for Outlook inbox access
- MS Graph API for Calendar availability
- MS Graph API for sending calendar invites
- SLA tracking for follow-up reminders

**Workflow:**
```
1. Email received → Parse request (participants, topic, urgency, constraints)
2. Query all participants' availability via MS Graph
3. Prioritize slots based on boss preferences
4. Send calendar invite proposal
5. Monitor for responses
6. If no response within SLA → Send follow-up reminder
7. Loop until meeting is scheduled or user cancels
```

### Example Email Interactions

**Request:**
> "Schedule a 30-minute call with Jim and Jennifer about the Q1 roadmap. Sometime next week, preferably morning."

**Agent Response:**
> "I found overlapping availability for you, Jim, and Jennifer on Tuesday 10am and Thursday 11am. I'll send an invite for Tuesday 10am. If that doesn't work, I'll try Thursday. I'll follow up with anyone who doesn't respond within 24 hours."

### Dependencies

- Microsoft 365 Business subscription with Graph API access
- User OAuth consent for Mail.Read, Calendars.ReadWrite
- LangGraph for agent orchestration

---

---

## 🤖 "What Should I Work On Next?" - Personal Developer Assistant

**Category:** Developer Experience Enhancement
**Priority:** P1 (High Impact - Daily Developer Workflow)
**Effort:** Medium (3-5 days)

### Overview

A Slack chatbot command that provides developers with a personalized, prioritized task list showing exactly what they should work on next. The bot analyzes their current work, pending reviews, blocked items, and sprint priorities to give concise, actionable recommendations.

### Core Functionality

**Trigger:** Developer messages Slack bot with "What should I work on next?"

**Bot Response Format:**
```
🎯 Your Next Actions (Highest Priority First):

1. 🔴 URGENT: Review PR #456 (waiting 3 days)
   → Action: Provide code review by EOD
   → Link: https://github.com/.../pull/456

2. 🟡 BLOCKED: ECD-789 - Implement user auth
   → Blocker: Waiting on API spec from backend team
   → Action: Follow up with Ahmed for API documentation
   → Link: https://citemed.atlassian.net/browse/ECD-789

3. ⚡ HIGH PRIORITY: ECD-567 - Fix login timeout bug
   → Sprint Goal: Critical bug fix
   → Action: Start work today
   → Link: https://citemed.atlassian.net/browse/ECD-567

4. ✅ IN PROGRESS: ECD-345 - PDF export feature
   → Status: PR ready for review
   → Action: Address review comments from Josh
   → Link: https://github.com/.../pull/345
```

### Intelligence & Analysis

The bot should analyze:

1. **PRs Pending Developer's Review**
   - How long waiting
   - Who's blocked by this review
   - Priority level

2. **Developer's Assigned Tickets**
   - Current sprint priorities (Highest → High → Medium)
   - Due dates and deadline urgency
   - Blocked status and blocker details

3. **In-Progress Work**
   - Tickets in "In Progress" status
   - PRs awaiting developer's response to comments
   - Stalled work (no commits in 2+ days)

4. **Blockers - Root Cause Analysis**
   - Parse ticket comments/links to understand WHY blocked
   - Identify who/what is blocking
   - Recommend specific follow-up action

### Key Features

✅ **Concise & Actionable**
- No massive walls of text
- Each item has ONE clear next action
- Links directly to Jira/GitHub

✅ **Intelligent Prioritization**
- Weighs: Urgency × Impact × Sprint Goals × Team Dependencies
- Shows highest-priority item first
- Uses emoji indicators (🔴 urgent, 🟡 blocked, ⚡ high priority, ✅ in progress)

✅ **Context-Aware Blockers**
- Reads ticket comments to understand blocker root cause
- Recommends WHO to follow up with and WHAT to ask
- Example: "Blocked on API spec → Follow up with @Ahmed for documentation"

✅ **Team Visibility**
- Shows if other devs are waiting on this developer's review
- Highlights cross-team dependencies

### Implementation Details

**Data Sources:**
1. Jira API - Assigned tickets, priorities, blocked status, comments
2. GitHub API - Open PRs, review requests, PR comments
3. Sprint data - Current sprint goals and deadlines

**Analysis Logic:**
```python
def get_next_actions(developer_slack_id):
    # 1. Get developer's Jira account ID from Slack ID
    jira_user = lookup_jira_user(developer_slack_id)
    
    # 2. Get all relevant work items
    assigned_tickets = get_assigned_tickets(jira_user)
    review_requests = get_pending_pr_reviews(jira_user)
    in_progress = get_in_progress_work(jira_user)
    
    # 3. Analyze blockers
    for ticket in assigned_tickets:
        if ticket.is_blocked:
            blocker_context = parse_blocker_from_comments(ticket)
            ticket.recommended_action = generate_blocker_action(blocker_context)
    
    # 4. Prioritize
    all_items = prioritize_work_items(
        assigned_tickets + review_requests + in_progress,
        weights={
            "urgency": 0.4,
            "sprint_priority": 0.3,
            "team_dependency": 0.2,
            "staleness": 0.1
        }
    )
    
    # 5. Format response
    return format_concise_response(all_items[:5])  # Top 5 only
```

**Blocker Root Cause Parsing:**
- Check ticket links for blockers
- Parse last 5 comments for keywords: "waiting", "blocked", "need", "depends"
- Extract developer mentions to identify who to follow up with
- Look for linked tickets (e.g., "blocked by ECD-XXX")

### Example Scenarios

**Scenario 1: Developer with stale PR review**
```
User: "What should I work on next?"

Bot:
🔴 URGENT: Review PR #789 (waiting 4 days, blocking Mohamed)
   → Action: Provide code review by EOD today
   → Link: https://github.com/.../pull/789
   
⚡ HIGH PRIORITY: ECD-456 - Dashboard performance fix
   → Sprint Goal: Critical performance issue
   → Action: Start work today
```

**Scenario 2: Developer with blocked ticket**
```
User: "What should I work on next?"

Bot:
🟡 BLOCKED: ECD-123 - User authentication
   → Blocker: Waiting on API specification document
   → Last Update: 2 days ago by Valentin "Need API docs to proceed"
   → Action: Follow up with @Valentin in #backend channel for API spec
   
✅ Continue: ECD-234 - Export feature (In Progress)
   → Status: 2 review comments from Josh
   → Action: Address code review feedback
```

**Scenario 3: Developer with nothing urgent**
```
User: "What should I work on next?"

Bot:
✅ All caught up! No urgent items.

📋 Available Work (Priority Order):
1. ECD-567 - Add dark mode toggle
   → Priority: Medium | Sprint: Current
   → Action: Pick up when ready
```

### Integration Points

**Slack Bot:**
- Slash command: `/next` or natural language "what should I work on"
- DM or channel mention: "@PM Bot what should I work on next?"

**Daily Standup Integration:**
- Each developer automatically gets their personalized list at 9 AM
- Included in standup summary

**Jira Integration:**
- Real-time ticket status monitoring
- Comment parsing for blocker context

**GitHub Integration:**
- PR review request tracking
- Stale PR detection

### Success Metrics

- **Developer Adoption:** ≥80% of team using weekly
- **Response Time:** <3 seconds to generate personalized list
- **Accuracy:** ≥95% of recommendations are actionable
- **Developer Satisfaction:** Survey feedback ≥4.5/5

### Future Enhancements

**Phase 2:**
- Learning from developer preferences (preferred work types, time of day)
- Workload balancing suggestions ("You have 5 items, but Ahmed only has 2")
- Proactive notifications ("Your highest priority item is due in 2 hours")

**Phase 3:**
- Integration with time tracking to estimate capacity
- Smart scheduling ("Based on your calendar, you have 3 hours free this afternoon")
- Team coordination ("You and Mohamed are both working on similar features - consider pairing")

### Why This Is High Priority

1. **Daily Developer Pain Point** - Developers waste 15-30 min/day figuring out priorities
2. **Reduces Context Switching** - Clear direction prevents jumping between tasks
3. **Improves Team Velocity** - Unblocks reviews and dependencies faster
4. **Enhances Transparency** - Everyone knows what they should be working on
5. **Low Effort, High ROI** - Leverages existing Jira/GitHub data

---
