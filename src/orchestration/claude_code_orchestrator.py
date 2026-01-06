"""
Claude Code Orchestrator - Invokes Claude Code with full context

This orchestrator invokes the Claude Code CLI to leverage:
- .claude/CLAUDE.md (project context)
- .claude/agents/*.md (specialized agent instructions)
- .claude/skills/*.md (business knowledge)
- MCP tools (Atlassian, Filesystem)

Flow: Event → Build Context-Aware Prompt → Invoke Claude Code → MCP Actions → Response
"""

import os
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from src.database.models import get_session, AgentCycle
from src.config import get_atlassian_config, get_project_key, get_jira_base_url

PROJECT_ROOT = Path(__file__).parent.parent.parent


class ClaudeCodeOrchestrator:
    """
    Orchestrator that invokes Claude Code CLI for intelligent reasoning
    with full access to project context and MCP tools
    """

    def __init__(self):
        print("🤖 Initializing Claude Code Orchestrator...")

        # Verify Claude Code CLI is available
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"   ✅ Claude Code CLI found: {result.stdout.strip()}")
            else:
                raise FileNotFoundError("Claude CLI not working")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise ValueError(
                "Claude Code CLI not found!\n"
                "Install from: https://claude.com/claude-code\n"
                f"Error: {e}"
            )

        # Verify settings file exists
        self.settings_file = PROJECT_ROOT / ".claude" / "settings.local.json"
        if not self.settings_file.exists():
            raise ValueError(
                f"Claude Code settings not found at {self.settings_file}\n"
                "Expected .claude/settings.local.json with MCP permissions"
            )

        print(f"   ✅ Settings file: {self.settings_file}")
        print(f"   ✅ Project root: {PROJECT_ROOT}")
        print(f"   ✅ Claude Code Orchestrator ready\n")

    def process_pr_review(
        self,
        repo: str,
        pr_id: int,
        pr_title: str,
        pr_author: str,
        pr_author_account_id: str,
        latest_commit: str,
        diff_url: str = None
    ) -> Dict:
        """
        Perform automated code review on a Pull Request using Claude Code

        Args:
            repo: Repository name (e.g., "citemed_web")
            pr_id: Pull request ID
            pr_title: PR title
            pr_author: PR author username
            latest_commit: Latest commit SHA
            diff_url: URL to diff (optional)

        Returns:
            Dict with review status and actions taken
        """
        print(f"\n{'='*60}")
        print(f"🔍 PR CODE REVIEW")
        print(f"{'='*60}")
        print(f"Repository: {repo}")
        print(f"PR: #{pr_id} - {pr_title}")
        print(f"Author: {pr_author}")
        print(f"Commit: {latest_commit[:8]}")
        print(f"{'='*60}\n")

        # Build PR review prompt
        prompt = self._build_pr_review_prompt(
            repo, pr_id, pr_title, pr_author, pr_author_account_id, latest_commit, diff_url
        )

        # Invoke Claude Code
        response = self._invoke_claude_code(prompt, timeout=300)  # 5 min for PR reviews

        # Log the cycle
        self._log_cycle(
            trigger_type="pr_review",
            trigger_data={
                "repo": repo,
                "pr_id": pr_id,
                "pr_title": pr_title,
                "pr_author": pr_author,
                "commit": latest_commit
            },
            claude_response=response,
            status="complete"
        )

        print(f"\n{'='*60}")
        print(f"✅ PR REVIEW COMPLETE")
        print(f"{'='*60}\n")

        return {
            "status": "complete",
            "repo": repo,
            "pr_id": pr_id,
            "response": response
        }

    def process_jira_comment(
        self,
        issue_key: str,
        comment_text: str,
        commenter: str,
        commenter_account_id: str = "",
        agent_type: str = "jira-manager"
    ) -> Dict:
        """
        Process a Jira comment using Claude Code with specialized agent context

        Args:
            issue_key: Jira issue key (e.g., "ECD-123")
            comment_text: The comment text
            commenter: Who made the comment
            agent_type: Which agent to use (jira-manager, sla-monitor, etc.)

        Returns:
            Dict with status and actions taken
        """
        print(f"\n{'='*60}")
        print(f"🔄 CLAUDE CODE REASONING CYCLE")
        print(f"{'='*60}")
        print(f"Agent: {agent_type}")
        print(f"Trigger: Jira comment on {issue_key}")
        print(f"Commenter: {commenter}")
        print(f"Comment: {comment_text[:100]}...")
        print(f"{'='*60}\n")

        # Build context-aware prompt
        prompt = self._build_jira_prompt(
            issue_key, comment_text, commenter, commenter_account_id, agent_type
        )

        # Invoke Claude Code
        response = self._invoke_claude_code(prompt)

        # Log the cycle
        self._log_cycle(
            trigger_type="jira_comment",
            trigger_data={
                "issue_key": issue_key,
                "comment": comment_text,
                "commenter": commenter,
                "agent_type": agent_type
            },
            claude_response=response,
            status="complete"
        )

        print(f"\n{'='*60}")
        print(f"✅ CYCLE COMPLETE")
        print(f"{'='*60}\n")

        return {
            "status": "complete",
            "agent_used": agent_type,
            "response": response
        }

    def _build_jira_prompt(
        self,
        issue_key: str,
        comment_text: str,
        commenter: str,
        commenter_account_id: str,
        agent_type: str
    ) -> str:
        """
        Build a context-aware prompt that tells Claude Code to:
        1. Read the appropriate agent instructions
        2. Use MCP tools for context
        3. Take specific actions
        4. Follow business rules from .claude/
        """

        agent_file = f".claude/agents/{agent_type}.md"

        prompt = f"""You are acting as the PM Agent responding to a Jira comment.

AGENT CONTEXT:
Read your specialized instructions from: {agent_file}
Load relevant skills from: .claude/skills/
Project context is in: .claude/CLAUDE.md

NEW JIRA COMMENT:
- Issue: {issue_key}
- Commenter: {commenter}
- Commenter Account ID: {commenter_account_id}
- Comment: "{comment_text}"
- Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

AVAILABLE JIRA TOOLS (use these instead of MCP):
All tools are in src/tools/jira/ and can be called via Python CLI:

1. **Search Issues:**
   ```bash
   python -m src.tools.jira.search "project = YOUR_PROJECT AND status = 'In Progress'" --max-results 10
   ```

2. **Get Issue Details:**
   ```bash
   python -m src.tools.jira.get_issue {issue_key}
   python -m src.tools.jira.get_issue {issue_key} --include-comments
   ```

3. **Add Comment (with @mentions):**
   ```bash
   python -m src.tools.jira.add_comment {issue_key} "Hi @{commenter}, your comment text here" --mention "{commenter_account_id}" "{commenter}"
   ```
   Note: The @Name in text will become a clickable mention.

4. **Edit Issue Fields:**
   ```bash
   python -m src.tools.jira.edit_issue {issue_key} --priority High
   python -m src.tools.jira.edit_issue {issue_key} --assignee "account_id_here"
   python -m src.tools.jira.edit_issue {issue_key} --add-labels "needs-review"
   ```

5. **Transition Issue Status:**
   ```bash
   python -m src.tools.jira.get_transitions {issue_key}  # See available transitions
   python -m src.tools.jira.transition_issue {issue_key} "Done"
   python -m src.tools.jira.transition_issue {issue_key} "In Progress"
   ```

6. **Lookup User:**
   ```bash
   python -m src.tools.jira.lookup_user "user@example.com"
   python -m src.tools.jira.lookup_user "John Doe"
   ```

7. **List Projects:**
   ```bash
   python -m src.tools.jira.list_projects
   ```

YOUR TASK:
1. **READ YOUR AGENT FILE** - Load {agent_file} for your specific procedures
2. **GATHER CONTEXT** - Use the tools above to understand the issue:
   - Run get_issue to get full issue details
   - Check status, assignee, priority, sprint
   - Use --include-comments to see recent comment history if needed
3. **ANALYZE** - Based on your agent instructions:
   - What is the nature of this comment?
   - Does it require a response?
   - Are there SLA implications?
   - What actions should be taken?
4. **ACT** - Execute the appropriate tools:
   - Use get_issue/search for QUERYING
   - Use edit_issue for field updates
   - Use add_comment for posting responses WITH @mentions
   - Use transition_issue to change status
5. **REPORT** - Provide a clear summary

YOUR RESPONSE MUST INCLUDE:

🎯 **Actions Taken:**
- List every tool call made (with actual output)
- Include specific results (ticket numbers, user IDs, etc.)

🔍 **Analysis:**
- What did you learn about the issue?
- What business rules did you apply?
- What was your decision?

📋 **Jira Updates:**
- Did you post a comment? (exact text)
- Did you update fields? (which ones)
- Did you tag anyone? (who)

➡️ **Next Steps:**
- What should happen next?
- Any follow-up needed?

CRITICAL REQUIREMENTS:
- You MUST read {agent_file} first to understand your role
- You MUST use the Python tools above - NOT MCP tools (MCP is not configured)
- You MUST follow the business rules in .claude/
- You MUST be specific about what you did
- If you post to Jira, include the exact comment text

BEGIN PROCESSING NOW.
"""

        return prompt

    def _build_pr_review_prompt(
        self,
        repo: str,
        pr_id: int,
        pr_title: str,
        pr_author: str,
        pr_author_account_id: str,
        latest_commit: str,
        diff_url: str = None
    ) -> str:
        """
        Build PR review prompt using the comprehensive review workflow
        """

        prompt = f"""You are performing an automated code review on a Pull Request.

PULL REQUEST DETAILS:
- Repository: {repo}
- PR Number: #{pr_id}
- Title: {pr_title}
- Author: {pr_author}
- Author Account ID: {pr_author_account_id}
- Latest Commit: {latest_commit}
- Review Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

YOUR TASK:
You must perform a comprehensive code review following the PR review workflow documented in:
`.claude/workflows/pr-review-automation.md`

STEP 1: GATHER PR CONTEXT
Use MCP tools to get the full PR details:
- Use `bitbucket-cli` or MCP tools to fetch PR diff
- Get list of files changed
- Get diffstat (lines added/removed)
- Get PR description

STEP 2: COMPREHENSIVE CODE REVIEW
Analyze the code changes focusing on:

**1. Code Quality:**
- Logic errors or bugs
- Performance issues (inefficient loops, N+1 queries, memory leaks)
- Security vulnerabilities (SQL injection, XSS, auth bypass)
- Code smells and anti-patterns

**2. Best Practices:**
- Python/JavaScript/Django/Vue.js standards adherence
- Proper error handling and edge cases
- Test coverage (are tests included and adequate?)
- Documentation (docstrings, comments for complex logic)

**3. Architecture & Design:**
- Design patterns and SOLID principles
- Separation of concerns
- Maintainability and readability
- Database design (indexes, relationships, migrations)

**4. Project-Specific Checks:**
- Hardcoded values (use environment variables)
- SQL injection risks in ORM queries
- Missing null/undefined checks
- Inefficient database queries
- Frontend reactivity issues
- Authentication/authorization checks
- Compliance considerations (if applicable)

STEP 3: POST REVIEW TO BITBUCKET
Use MCP tools to post your review:
- IMPORTANT: To mention the PR author, use: @{{{pr_author_account_id}}} (e.g., @{{712020:27a3f2fe-9037-455d-9392-fb80ba1705c0}})
- This is Bitbucket's required format for mentions - you MUST use the account_id, not the display name
- Post overall summary comment with the author mention
- Post inline comments on specific issues (file + line number)
- Use Bitbucket API to add comments

YOUR RESPONSE MUST INCLUDE:

## 🎯 Actions Taken:
- List all MCP tool calls made
- Include PR diff analysis
- Note any API calls to Bitbucket

## 🔍 Review Summary:
**Overall Assessment:** APPROVE | REQUEST CHANGES | COMMENT
**Severity:** LOW | MEDIUM | HIGH | CRITICAL
**Files Changed:** [count]
**Lines Added/Removed:** +X / -Y

Brief 2-3 sentence summary of changes and quality.

## ⚠️ Issues Found:
For each issue:
- **Type:** bug | performance | security | style | architecture
- **Severity:** critical | major | minor | info
- **File:** path/to/file.py
- **Line:** 123 (if identifiable)
- **Description:** What's wrong
- **Suggestion:** Specific fix

## ✅ Positives:
- 2-3 good things about this PR

## 📋 Bitbucket Comments Posted:
**Main Comment:** (exact text posted)
**Inline Comments:** (list of file:line comments)

## ➡️ Recommendation:
- Ready to merge? Any blockers?
- Follow-up actions needed?

CRITICAL REQUIREMENTS:
- You MUST use MCP tools to fetch PR details and post comments
- You MUST analyze actual code, not theorize
- You MUST post comments to Bitbucket PR
- Be constructive and specific
- Prioritize critical issues over style nitpicks
- Include the exact comment text you posted

BEGIN PR REVIEW NOW.
"""

        return prompt

    def _invoke_claude_code(
        self,
        prompt: str,
        max_retries: int = 2,
        timeout: int = 600
    ) -> str:
        """
        Invoke Claude Code CLI with the given prompt

        This runs: claude -p --output-format text --settings .claude/settings.local.json

        The settings file enables MCP servers (atlassian, filesystem)
        Claude Code will automatically read .claude/ context
        """

        for attempt in range(max_retries):
            try:
                print(f"🤖 Invoking Claude Code (attempt {attempt + 1}/{max_retries}, timeout: {timeout//60} min)...")

                # Build environment with MCP-required variables
                # This ensures dotenv-loaded vars are passed to Claude subprocess
                env = os.environ.copy()
                env['ATLASSIAN_SERVICE_ACCOUNT_TOKEN'] = os.getenv('ATLASSIAN_SERVICE_ACCOUNT_TOKEN', '')

                result = subprocess.run(
                    [
                        "claude",
                        "-p",  # Prompt mode
                        "--output-format",
                        "text",  # Plain text output
                        "--settings",
                        str(self.settings_file),  # Use our settings (enables MCP)
                    ],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(PROJECT_ROOT),  # Run in project root for .claude/ access
                    env=env,  # Pass environment with MCP tokens
                )

                if result.returncode == 0:
                    response = result.stdout.strip()
                    if response:
                        print(f"   ✅ Claude Code response received ({len(response)} chars)")
                        if len(response) > 200:
                            print(f"   Preview: {response[:200]}...")
                        return response
                    else:
                        print("   ⚠️  Claude Code returned empty response")
                        return "Processed but no response generated."

                else:
                    error_msg = result.stderr.strip()
                    print(f"   ❌ Claude Code error (code {result.returncode})")
                    print(f"   Error: {error_msg[:500]}...")

                    if attempt < max_retries - 1:
                        print("   🔄 Retrying in 2 seconds...")
                        time.sleep(2)
                        continue

                    return f"Error processing: {error_msg[:200]}"

            except subprocess.TimeoutExpired:
                print(f"   ⏱️  Claude Code timed out after {timeout//60} minutes")
                if attempt < max_retries - 1:
                    print("   🔄 Retrying...")
                    time.sleep(5)
                    continue

                return "Processing timed out. The request was too complex."

            except FileNotFoundError:
                print("   ❌ Claude Code CLI not found")
                return "Error: Claude Code CLI not available on this system."

            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue

                return f"Unexpected error: {str(e)}"

        return "Failed after multiple retries."

    def _log_cycle(
        self,
        trigger_type: str,
        trigger_data: Dict,
        claude_response: str,
        status: str
    ):
        """Log the reasoning cycle to database"""
        print(f"💾 Logging cycle to database...")

        session = get_session()
        try:
            cycle = AgentCycle(
                trigger_type=trigger_type,
                trigger_data=json.dumps(trigger_data),
                context_gathered="See Claude Code response for context",
                plan=json.dumps({"claude_code_invoked": True}),
                actions_taken=json.dumps({"response": claude_response}),
                status=status
            )

            session.add(cycle)
            session.commit()

            print(f"   ✓ Cycle #{cycle.id} logged")

        except Exception as e:
            print(f"   ❌ Failed to log cycle: {e}")
            session.rollback()

        finally:
            session.close()


    def detect_pm_intent(self, comment_text: str) -> Dict:
        """
        Detect if a comment is a PM request (story/bug/epic creation) vs other request types

        Returns:
            {
                "is_pm_request": bool,
                "request_type": "story" | "bug" | "epic" | "none",
                "confidence": float (0-1),
                "keywords_found": List[str]
            }
        """
        comment_lower = comment_text.lower()

        # PM request patterns
        pm_patterns = {
            "story": [
                "create a story", "write a story", "make a story",
                "create a ticket", "write up a ticket", "file a ticket",
                "create a feature", "new feature", "add feature"
            ],
            "bug": [
                "create a bug", "file a bug", "report a bug",
                "bug report", "create a defect", "file a defect",
                "this is broken", "not working", "issue with"
            ],
            "epic": [
                "create an epic", "write an epic", "make an epic",
                "strategic initiative", "this should be an epic"
            ]
        }

        # Check each pattern type
        detected_type = "none"
        keywords_found = []
        confidence = 0.0

        for request_type, patterns in pm_patterns.items():
            for pattern in patterns:
                if pattern in comment_lower:
                    detected_type = request_type
                    keywords_found.append(pattern)
                    confidence = max(confidence, 0.8 if "create" in pattern or "write" in pattern else 0.6)

        is_pm_request = detected_type != "none"

        return {
            "is_pm_request": is_pm_request,
            "request_type": detected_type,
            "confidence": confidence,
            "keywords_found": keywords_found
        }

    def process_pm_request(
        self,
        source: str,
        source_id: str,
        request_type: str,
        comment_text: str,
        requester_id: str,
        requester_name: str
    ) -> Dict:
        """
        Process a PM request (create story/bug/epic draft)

        Args:
            source: 'jira' | 'slack' | 'bitbucket'
            source_id: issue_key | thread_ts | pr_id
            request_type: 'story' | 'bug' | 'epic'
            comment_text: Original comment with the request
            requester_id: User account ID
            requester_name: User display name

        Returns:
            Dict with request_id, draft_posted, status
        """
        print(f"\n{'='*60}")
        print(f"📋 PM REQUEST - {request_type.upper()} CREATION")
        print(f"{'='*60}")
        print(f"Source: {source} ({source_id})")
        print(f"Requester: {requester_name}")
        print(f"Type: {request_type}")
        print(f"{'='*60}\n")

        # Build PM prompt
        prompt = self._build_pm_prompt(
            source, source_id, request_type, comment_text, requester_id, requester_name
        )

        # Invoke Claude Code with PM agent
        response = self._invoke_claude_code(prompt, timeout=300)  # 5 min for PM drafts

        # Store draft in database
        from src.database.pm_requests_db import get_pm_requests_db
        db = get_pm_requests_db()

        request_id = db.create_request(
            source=source,
            source_id=source_id,
            request_type=request_type,
            user_id=requester_id,
            user_name=requester_name,
            original_context=comment_text,
            draft_content=response
        )

        # Post draft to Jira as comment
        if source == 'jira':
            try:
                self._post_jira_comment(source_id, response)
                print(f"   ✅ Posted PM draft to Jira {source_id}")
            except Exception as e:
                print(f"   ⚠️  Failed to post draft to Jira: {e}")
                import traceback
                traceback.print_exc()

        # Log the cycle
        self._log_cycle(
            trigger_type="pm_request",
            trigger_data={
                "source": source,
                "source_id": source_id,
                "request_type": request_type,
                "requester": requester_name
            },
            claude_response=response,
            status="draft_created"
        )

        print(f"\n{'='*60}")
        print(f"✅ PM DRAFT CREATED")
        print(f"{'='*60}")
        print(f"Request ID: {request_id}")
        print(f"Status: Awaiting approval")
        print(f"{'='*60}\n")

        return {
            "success": True,
            "request_id": request_id,
            "request_type": request_type,
            "draft_posted": True,
            "status": "pending_approval",
            "draft_content": response
        }

    def _build_pm_prompt(
        self,
        source: str,
        source_id: str,
        request_type: str,
        comment_text: str,
        requester_id: str,
        requester_name: str
    ) -> str:
        """
        Build prompt for PM agent to generate story/bug/epic draft
        """

        workflow_map = {
            "story": "story-generation",
            "bug": "bug-generation",
            "epic": "epic-generation"
        }

        workflow = workflow_map.get(request_type, "story-generation")

        prompt = f"""You are acting as the Product Manager Agent creating a {request_type} draft.

AGENT CONTEXT:
Read your PM agent instructions from: .claude/agents/product-manager/agent.md
Load the workflow for this request type: .claude/agents/product-manager/workflows/{workflow}.md
Load the appropriate template: .claude/agents/product-manager/templates/{request_type}-template.md

REQUEST DETAILS:
- Source: {source}
- Source ID: {source_id}
- Request Type: {request_type}
- Requester: {requester_name} ({requester_id})
- Original Request: "{comment_text}"
- Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

YOUR TASK:
Follow the {workflow}.md workflow to generate a comprehensive {request_type} draft:

1. **ANALYZE CONTEXT** - Extract key information from the request:
   - What is the user trying to accomplish?
   - What problem are they solving?
   - Who is the target user persona?
   - What module/area is affected?
   - Gather additional context if {source} is Jira (use: python -m src.tools.jira.get_issue ISSUE_KEY)

2. **LOAD TEMPLATE** - Read the {request_type}-template.md to understand the required structure

3. **GENERATE DRAFT** - Create a comprehensive draft following the template:
   - For STORIES: User story, business context, technical scope, acceptance criteria
   - For BUGS: Summary, reproduction steps, expected vs actual, severity, acceptance criteria
   - For EPICS: Business justification, scope, success criteria, timeline phases

4. **APPLY BEST PRACTICES** - Follow project-specific patterns:
   - Core business features and workflows
   - Compliance requirements (if applicable)
   - Technology stack (refer to project documentation)

5. **FORMAT FOR POSTING** - Create a response that will be posted to {source} ({source_id}):

RESPONSE FORMAT:

📋 I've analyzed your request and created a draft {request_type}.

---

[COMPLETE DRAFT CONTENT IN MARKDOWN]
(Use the template structure from {request_type}-template.md)

---

**Next Steps:**
- Reply **'approved'** to create Jira ticket ECD-XXX
- Reply **'changes: [your feedback]'** to refine the draft
- Reply **'cancel'** to discard

I'll monitor this thread for your response.

CRITICAL REQUIREMENTS:
- You MUST read .claude/agents/product-manager/agent.md first
- You MUST follow the workflow in .claude/agents/product-manager/workflows/{workflow}.md
- You MUST use the template from .claude/agents/product-manager/templates/{request_type}-template.md
- Be comprehensive but concise - aim for clear, actionable specifications
- Include specific acceptance criteria that are testable
- Consider project context and user personas
- Use proper markdown formatting

OUTPUT ONLY THE FORMATTED RESPONSE - this will be posted directly to {source}.

BEGIN GENERATING THE {request_type.upper()} DRAFT NOW.
"""

        return prompt

    def _post_jira_comment(self, issue_key: str, comment_text: str):
        """
        Post a comment to a Jira issue using direct REST API

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123")
            comment_text: Comment text (markdown format)
        """
        import os
        import requests

        api_token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN", "").strip("'\"")

        # Use configuration from src/config.py
        atlassian_config = get_atlassian_config()
        cloud_id = atlassian_config['cloud_id']

        if not api_token:
            print(f"   ❌ No ATLASSIAN_SERVICE_ACCOUNT_TOKEN configured")
            return False

        base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

        try:
            headers = {
                "Authorization": f"Bearer {api_token}",
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
                f"{base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                print(f"   ✅ Posted comment to {issue_key}")
                return True
            else:
                print(f"   ❌ Failed to post comment: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"   ❌ Error posting comment: {e}")
            raise

    def parse_approval_response(self, comment_text: str) -> Dict:
        """
        Parse comment text for approval keywords

        Detects:
        - Approval: "approved", "looks good", "go ahead", "✅"
        - Changes: "changes: [feedback]", "revise: [feedback]"
        - Cancel: "cancel", "discard", "never mind", "❌"

        Returns:
            {
                "response_type": "approved" | "changes" | "cancel" | None,
                "feedback": str (if changes requested),
                "confidence": float (0-1)
            }
        """
        import re

        comment_lower = comment_text.lower().strip()

        # Approval patterns (match anywhere in comment, not just exact match)
        approval_patterns = [
            r'\bapproved?\b',  # Word boundary - matches "approved" or "approve" as standalone word
            r'\bapprove\b',
            r'\blooks good\b',
            r'\bgo ahead\b',
            r'✅'
        ]

        for pattern in approval_patterns:
            if re.search(pattern, comment_lower):
                return {
                    "response_type": "approved",
                    "feedback": None,
                    "confidence": 0.9
                }

        # Change request patterns (extract feedback after keyword)
        change_patterns = [
            r'changes?:\s*(.+)',
            r'revise?:\s*(.+)',
            r'update:\s*(.+)',
            r'modify:\s*(.+)',
            r'please change\s+(.+)'
        ]

        for pattern in change_patterns:
            match = re.search(pattern, comment_lower, re.IGNORECASE | re.DOTALL)
            if match:
                feedback = match.group(1).strip()
                return {
                    "response_type": "changes",
                    "feedback": feedback,
                    "confidence": 0.9
                }

        # Cancel patterns (match anywhere in comment)
        cancel_patterns = [
            r'\bcancel\b',
            r'\bdiscard\b',
            r'\bnever mind\b',
            r"\bdon'?t create\b",
            r'❌'
        ]

        for pattern in cancel_patterns:
            if re.search(pattern, comment_lower):
                return {
                    "response_type": "cancel",
                    "feedback": None,
                    "confidence": 0.9
                }

        # No match
        return {
            "response_type": None,
            "feedback": None,
            "confidence": 0.0
        }

    def handle_pm_approval(self, request_id: str) -> Dict:
        """
        Handle approval of PM request - create Jira ticket

        Steps:
        1. Get approved draft from database
        2. Parse draft to extract ticket fields
        3. Create Jira ticket via Atlassian MCP
        4. Update database with ticket key
        5. Post confirmation comment

        Returns:
            {
                "success": bool,
                "jira_ticket_key": str,
                "error": str (if failed)
            }
        """
        from src.database.pm_requests_db import get_pm_requests_db

        db = get_pm_requests_db()
        request = db.get_request(request_id)

        if not request:
            return {"success": False, "error": "Request not found"}

        print(f"✅ Creating Jira ticket for approved {request['request_type']} (request_id: {request_id})")

        # Parse draft to extract title (first # heading)
        draft_lines = request['draft_content'].split('\n')
        title = None
        for line in draft_lines:
            if line.startswith('# '):
                title = line.replace('# ', '').strip()
                break

        if not title:
            title = f"{request['request_type'].title()}: Untitled"

        # Use Claude Code to create Jira ticket via MCP
        # Get configuration from src/config.py
        atlassian_config = get_atlassian_config()
        cloud_id = atlassian_config['cloud_id']
        project_key = atlassian_config['project_key']

        # Map request type to Jira issue type
        issue_type_map = {
            "story": "Story",
            "bug": "Bug",
            "epic": "Epic"
        }
        issue_type = issue_type_map.get(request['request_type'], "Story")

        prompt = f"""Create a Jira {issue_type} ticket from this approved PM draft.

**Title:** {title}

**Description:**
{request['draft_content']}

Create the Jira ticket using available tools with:
- cloudId: {cloud_id}
- fields:
  - project: {{"key": "{project_key}"}}
  - issuetype: {{"name": "{issue_type}"}}
  - summary: "{title}"
  - description: Convert the markdown draft above to Atlassian Document Format (ADF) for the description field
  - priority: {{"name": "Medium"}}  (adjust based on content if indicated)

After creating the ticket, report back the issue key (e.g., {project_key}-123).
"""

        try:
            response = self._invoke_claude_code(prompt, timeout=120)

            # Extract issue key from response
            import re
            # Use configured project key for pattern matching
            issue_key_match = re.search(rf'({project_key}-\d+)', response)

            if issue_key_match:
                issue_key = issue_key_match.group(1)
                print(f"   ✅ Created Jira ticket: {issue_key}")

                # Update database
                db.update_request_status(request_id, 'created', issue_key)

                # Post confirmation comment
                jira_url = get_jira_base_url()
                confirmation = f"""✅ Created {issue_key}: {title}

Link: {jira_url}/browse/{issue_key}

The ticket is ready for the development team."""

                if request['source'] == 'jira':
                    try:
                        self._post_jira_comment(request['source_id'], confirmation)
                        print(f"   ✅ Posted confirmation to {request['source_id']}")
                    except Exception as e:
                        print(f"   ⚠️  Failed to post confirmation: {e}")

                return {
                    "success": True,
                    "jira_ticket_key": issue_key
                }
            else:
                print(f"   ❌ Could not extract issue key from response")
                return {
                    "success": False,
                    "error": "Could not extract issue key from Claude Code response"
                }

        except Exception as e:
            print(f"   ❌ Failed to create Jira ticket: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def handle_pm_revision(self, request_id: str, feedback: str) -> Dict:
        """
        Handle revision request - generate updated draft with feedback

        Steps:
        1. Get original request and draft from database
        2. Build revision prompt with feedback
        3. Invoke Claude Code to generate revised draft
        4. Store revision in database
        5. Post revised draft for re-approval

        Returns:
            {
                "success": bool,
                "revision_number": int,
                "revised_draft": str,
                "error": str (if failed)
            }
        """
        from src.database.pm_requests_db import get_pm_requests_db

        db = get_pm_requests_db()
        request = db.get_request(request_id)

        if not request:
            return {"success": False, "error": "Request not found"}

        print(f"📝 Generating revision for {request['request_type']} based on feedback...")
        print(f"   Feedback: {feedback[:100]}...")

        # Get current revision number
        revisions = db.get_revisions(request_id)
        current_revision = len(revisions) + 1

        # Build revision prompt
        prompt = f"""You are revising a {request['request_type']} draft based on user feedback.

**Original Context:**
{request['original_context']}

**Previous Draft (Revision {current_revision - 1}):**
{request['draft_content']}

**User Feedback:**
{feedback}

**Task:**
Apply the user's feedback to create an improved draft. Make the requested changes while maintaining the overall structure and quality of the original draft.

Follow the {request['request_type']} template structure from .claude/agents/product-manager/templates/{request['request_type']}-template.md

**Output:**
Provide the complete revised draft in markdown format, ready to be posted to {request['source']}.

Include this header:
📝 Updated draft based on your feedback (Revision {current_revision})

**Changes Made:**
[Summarize what was changed based on the feedback]

---

[COMPLETE REVISED DRAFT]

---

**Next Steps:**
- Reply **'approved'** to create Jira ticket
- Reply **'changes: [more feedback]'** to revise again
- Reply **'cancel'** to discard

Does this look better?
"""

        # Invoke Claude Code to generate revision
        try:
            revised_draft = self._invoke_claude_code(prompt, timeout=300)

            # Store revision in database
            revision_number = db.add_revision(
                request_id=request_id,
                draft_content=revised_draft,
                feedback=feedback
            )

            print(f"   ✅ Generated revision {revision_number}")

            # Post revised draft to Jira
            if request['source'] == 'jira':
                try:
                    self._post_jira_comment(request['source_id'], revised_draft)
                    print(f"   ✅ Posted revised draft to {request['source_id']}")
                except Exception as e:
                    print(f"   ⚠️  Failed to post revised draft: {e}")

            return {
                "success": True,
                "revision_number": revision_number,
                "revised_draft": revised_draft
            }

        except Exception as e:
            print(f"   ❌ Failed to generate revision: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def handle_pm_cancellation(self, request_id: str) -> Dict:
        """
        Handle cancellation of PM request

        Steps:
        1. Update database status to 'cancelled'
        2. Post acknowledgment comment

        Returns:
            {
                "success": bool,
                "error": str (if failed)
            }
        """
        from src.database.pm_requests_db import get_pm_requests_db

        db = get_pm_requests_db()
        request = db.get_request(request_id)

        if not request:
            return {"success": False, "error": "Request not found"}

        print(f"❌ Cancelling {request['request_type']} request (request_id: {request_id})")

        # Update database
        db.update_request_status(request_id, 'cancelled')

        # Post acknowledgment to Jira
        if request['source'] == 'jira':
            acknowledgment = f"❌ PM request cancelled. The draft has been discarded."
            try:
                self._post_jira_comment(request['source_id'], acknowledgment)
                print(f"   ✅ Posted cancellation acknowledgment to {request['source_id']}")
            except Exception as e:
                print(f"   ⚠️  Failed to post acknowledgment: {e}")

        return {
            "success": True
        }


if __name__ == "__main__":
    """
    Test the Claude Code orchestrator
    Run: python -m src.orchestration.claude_code_orchestrator
    """
    print("\n🧪 Testing Claude Code Orchestrator...\n")

    try:
        orchestrator = ClaudeCodeOrchestrator()

        # Test with a simulated Jira comment
        result = orchestrator.process_jira_comment(
            issue_key="ECD-123",
            comment_text="Can someone help review this PR? It's been waiting for 2 days.",
            commenter="Sarah Johnson",
            agent_type="jira-manager"
        )

        print(f"\n📊 Result:")
        print(json.dumps(result, indent=2))

        print("\n✅ Claude Code Orchestrator test complete!\n")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure:")
        print("  1. Claude Code CLI is installed")
        print("  2. .claude/settings.local.json exists")
        print("  3. MCP servers are configured in .mcp.json\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
