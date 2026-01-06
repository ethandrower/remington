#!/usr/bin/env python3
"""
Definition of Ready Enforcement Module

Enforces three rules:
1. Missing Deadlines - All active work must have due dates
2. Missing Hours Estimates - All active work must have Original Estimate set
3. Stalled Refinement - Tickets in "In Refinement" > 2 days must take action

Runs as Section 7 of Daily Standup Workflow
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class DOREnforcer:
    """Definition of Ready Enforcement"""

    def __init__(self, cloud_id: str, project_root: Path, dry_run: bool = False):
        self.cloud_id = cloud_id
        self.project_root = project_root
        self.dry_run = dry_run

    def run_mcp_query(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Execute Claude Code MCP query"""
        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "text", "--settings", ".claude/settings.local.json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"❌ MCP query failed: {result.stderr[:200]}")
                return None

        except subprocess.TimeoutExpired:
            print(f"❌ MCP query timed out after {timeout} seconds")
            return None
        except Exception as e:
            print(f"❌ MCP query error: {e}")
            return None

    def query_missing_deadlines(self) -> List[Dict]:
        """Query tickets missing due dates"""
        print("  📅 Querying tickets missing deadlines...")

        jql = """project = ECD AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND duedate IS EMPTY
ORDER BY status ASC, updated DESC"""

        prompt = f"""Use mcp__atlassian__searchJiraIssuesUsingJql to search for tickets.

CloudId: {self.cloud_id}
JQL: {jql}
Fields: ["key", "summary", "status", "assignee", "priority", "updated"]

IMPORTANT: For assignee field, include both displayName AND accountId.

Return ONLY a JSON array of tickets with these fields.
Format: [{{"key": "ECD-123", "summary": "...", "status": "...", "assignee": {{"displayName": "...", "accountId": "..."}}, "updated": "..."}}, ...]
NO markdown, NO additional text, ONLY JSON array."""

        result = self.run_mcp_query(prompt)
        if not result:
            return []

        try:
            # Clean up result (remove markdown code blocks if present)
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            tickets = json.loads(cleaned)
            if isinstance(tickets, dict) and "issues" in tickets:
                return tickets["issues"]
            return tickets if isinstance(tickets, list) else []
        except json.JSONDecodeError:
            print(f"  ⚠️  Failed to parse JSON: {result[:200]}")
            return []

    def query_missing_estimates(self) -> List[Dict]:
        """Query tickets missing hours estimates"""
        print("  ⏱️  Querying tickets missing hours estimates...")

        jql = """project = ECD AND sprint in openSprints()
AND status IN ("In Progress", "Ready for Development", "Ready for QA")
AND timeoriginalestimate IS EMPTY
ORDER BY status ASC, updated DESC"""

        prompt = f"""Use mcp__atlassian__searchJiraIssuesUsingJql to search for tickets.

CloudId: {self.cloud_id}
JQL: {jql}
Fields: ["key", "summary", "status", "assignee", "priority", "updated"]

IMPORTANT: For assignee field, include both displayName AND accountId.

Return ONLY a JSON array of tickets.
Format: [{{"key": "ECD-123", "summary": "...", "status": "...", "assignee": {{"displayName": "...", "accountId": "..."}}, "updated": "..."}}, ...]
NO markdown, NO additional text, ONLY JSON array."""

        result = self.run_mcp_query(prompt)
        if not result:
            return []

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            tickets = json.loads(cleaned)
            if isinstance(tickets, dict) and "issues" in tickets:
                return tickets["issues"]
            return tickets if isinstance(tickets, list) else []
        except json.JSONDecodeError:
            print(f"  ⚠️  Failed to parse JSON: {result[:200]}")
            return []

    def query_stalled_refinement(self) -> List[Dict]:
        """Query tickets stalled in refinement > 2 days"""
        print("  🔄 Querying tickets stalled in refinement...")

        jql = """project = ECD AND sprint in openSprints()
AND status = "In Refinement"
AND updated < -2d
ORDER BY updated ASC"""

        prompt = f"""Use mcp__atlassian__searchJiraIssuesUsingJql to search for tickets.

CloudId: {self.cloud_id}
JQL: {jql}
Fields: ["key", "summary", "status", "assignee", "updated"]

IMPORTANT: For assignee field, include both displayName AND accountId.

Return ONLY a JSON array of tickets.
Format: [{{"key": "ECD-123", "summary": "...", "status": "...", "assignee": {{"displayName": "...", "accountId": "..."}}, "updated": "..."}}, ...]
NO markdown, NO additional text, ONLY JSON array."""

        result = self.run_mcp_query(prompt)
        if not result:
            return []

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            tickets = json.loads(cleaned)
            if isinstance(tickets, dict) and "issues" in tickets:
                return tickets["issues"]
            return tickets if isinstance(tickets, list) else []
        except json.JSONDecodeError:
            print(f"  ⚠️  Failed to parse JSON: {result[:200]}")
            return []

    def post_jira_comment(self, issue_key: str, comment_body: str) -> bool:
        """Post comment to Jira ticket"""
        if self.dry_run:
            print(f"  [DRY RUN] Would post comment to {issue_key}")
            return True

        prompt = f"""Use mcp__atlassian__addCommentToJiraIssue to add a comment.

CloudId: {self.cloud_id}
IssueIdOrKey: {issue_key}
CommentBody: {comment_body}

Return ONLY: {{"success": true}} or {{"success": false, "error": "..."}}
NO markdown, NO additional text, ONLY JSON."""

        result = self.run_mcp_query(prompt)
        if not result:
            return False

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            response = json.loads(cleaned)
            return response.get("success", False)
        except:
            # If comment was posted, consider success
            return "success" in result.lower() or "added" in result.lower()

    def generate_missing_deadline_comment(self, ticket: Dict) -> str:
        """Generate Jira comment for missing deadline"""
        days_in_status = self._calculate_days_in_status(ticket.get("updated"))

        # Get assignee account ID for @mention
        assignee_field = ticket.get("assignee", {})
        assignee_id = None
        assignee_name = "the assignee"

        if isinstance(assignee_field, dict):
            assignee_id = assignee_field.get("accountId")
            assignee_name = assignee_field.get("displayName", "the assignee")

        # Create @mention if we have account ID
        mention = f"@{assignee_id}" if assignee_id else assignee_name

        return f"""📅 **MISSING DEADLINE**

This ticket has been **{ticket.get('status', 'Unknown')}** for **{days_in_status} days** without a due date set.

**Required Action:** {mention} - Please set a due date by EOD today for capacity planning and sprint tracking.

**Why this matters:**
- Enables deadline risk monitoring
- Improves sprint forecasting
- Provides visibility to stakeholders

---
*Automated reminder from Definition of Ready Enforcer*"""

    def generate_missing_estimate_comment(self, ticket: Dict) -> str:
        """Generate Jira comment for missing hours estimate"""
        # Get assignee account ID for @mention
        assignee_field = ticket.get("assignee", {})
        assignee_id = None
        assignee_name = "the assignee"

        if isinstance(assignee_field, dict):
            assignee_id = assignee_field.get("accountId")
            assignee_name = assignee_field.get("displayName", "the assignee")

        # Create @mention if we have account ID
        mention = f"@{assignee_id}" if assignee_id else assignee_name

        return f"""⏱️ **MISSING HOURS ESTIMATE**

This ticket does not have an **Original Estimate** set.

**Required Action:** {mention} - Please add time estimate in the "Original Estimate" field.

**How to set:**
1. Edit ticket
2. Find "Original Estimate" field
3. Enter estimate (e.g., "4h", "2d", "1w")

**Why this matters:**
- Enables capacity planning
- Improves sprint velocity tracking
- Helps identify workload imbalances

---
*Automated reminder from Definition of Ready Enforcer*"""

    def generate_refinement_comment(self, ticket: Dict, has_questions: bool) -> str:
        """Generate Jira comment for stalled refinement"""
        days_stalled = self._calculate_days_in_status(ticket.get("updated"))

        # Get assignee account ID for @mention
        assignee_field = ticket.get("assignee", {})
        assignee_id = None
        assignee_name = "the assignee"

        if isinstance(assignee_field, dict):
            assignee_id = assignee_field.get("accountId")
            assignee_name = assignee_field.get("displayName", "the assignee")

        # Create @mention if we have account ID
        mention = f"@{assignee_id}" if assignee_id else assignee_name

        if has_questions:
            return f"""⏰ **REFINEMENT REMINDER**

This ticket has been in **In Refinement** status for **{days_stalled} days** with pending questions.

**Required Action:** {mention} - Please clarify the pending questions and move this ticket forward.

**Status Check:**
- Are questions answered? → Transition to "Ready for Development" or "Ready for Design"
- Need more info? → Follow up with stakeholders

---
*Automated reminder from Definition of Ready Enforcer*"""
        else:
            return f"""🚨 **COMPLETE REFINEMENT**

This ticket has been in **In Refinement** status for **{days_stalled} days** without any questions asked.

**Required Action:** {mention} - Please choose one:
1. **Transition to "Ready for Development"** if refinement is complete
2. **Transition to "Ready for Design"** if design is needed
3. **Ask clarifying questions** if more information is required

**Why this matters:**
- Prevents bottlenecks in refinement phase
- Keeps sprint velocity healthy
- Ensures work doesn't stall

---
*Automated reminder from Definition of Ready Enforcer (2-day limit)*"""

    def _calculate_days_in_status(self, updated_str: Optional[str]) -> int:
        """Calculate days since last update"""
        if not updated_str:
            return 0

        try:
            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            now = datetime.now(updated.tzinfo)
            delta = now - updated
            return delta.days
        except:
            return 0

    def execute(self) -> Dict[str, Any]:
        """Execute DOR enforcement and return results"""
        print("\n📋 SECTION 7: MISSING ESTIMATES, DEADLINES & STALLED REFINEMENT")
        print("=" * 60)

        results = {
            "missing_deadlines": [],
            "missing_estimates": [],
            "stalled_refinement": [],
            "compliance_summary": {},
            "actions_taken": {
                "deadline_comments": 0,
                "estimate_comments": 0,
                "refinement_comments": 0
            }
        }

        # Query violations
        missing_deadlines = self.query_missing_deadlines()
        missing_estimates = self.query_missing_estimates()
        stalled_refinement = self.query_stalled_refinement()

        print(f"\n📊 Violations Found:")
        print(f"  - Missing Deadlines: {len(missing_deadlines)}")
        print(f"  - Missing Estimates: {len(missing_estimates)}")
        print(f"  - Stalled Refinement: {len(stalled_refinement)}")

        # Post comments for missing deadlines
        for ticket in missing_deadlines[:5]:  # Limit to 5 per run
            comment = self.generate_missing_deadline_comment(ticket)
            if self.post_jira_comment(ticket["key"], comment):
                results["actions_taken"]["deadline_comments"] += 1
                print(f"  ✅ Posted deadline reminder to {ticket['key']}")

        # Post comments for missing estimates
        for ticket in missing_estimates[:5]:  # Limit to 5 per run
            comment = self.generate_missing_estimate_comment(ticket)
            if self.post_jira_comment(ticket["key"], comment):
                results["actions_taken"]["estimate_comments"] += 1
                print(f"  ✅ Posted estimate reminder to {ticket['key']}")

        # Post comments for stalled refinement
        for ticket in stalled_refinement[:5]:  # Limit to 5 per run
            # TODO: Check if questions were asked (requires comment analysis)
            has_questions = False
            comment = self.generate_refinement_comment(ticket, has_questions)
            if self.post_jira_comment(ticket["key"], comment):
                results["actions_taken"]["refinement_comments"] += 1
                print(f"  ✅ Posted refinement reminder to {ticket['key']}")

        # Store results
        results["missing_deadlines"] = missing_deadlines
        results["missing_estimates"] = missing_estimates
        results["stalled_refinement"] = stalled_refinement

        # Calculate compliance rates
        # TODO: Query total active work count for compliance percentage
        results["compliance_summary"] = {
            "missing_deadlines_count": len(missing_deadlines),
            "missing_estimates_count": len(missing_estimates),
            "stalled_refinement_count": len(stalled_refinement)
        }

        print(f"\n✅ Section 7 Complete")
        print(f"  - Posted {results['actions_taken']['deadline_comments']} deadline reminders")
        print(f"  - Posted {results['actions_taken']['estimate_comments']} estimate reminders")
        print(f"  - Posted {results['actions_taken']['refinement_comments']} refinement reminders")

        return results


def main():
    """Standalone execution for testing"""
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent
    load_dotenv(project_root / ".env")

    cloud_id = os.getenv("ATLASSIAN_CLOUD_ID", "67bbfd03-b309-414f-9640-908213f80628")

    print("=" * 60)
    print("  Definition of Ready Enforcement - Standalone Test")
    print("=" * 60)

    enforcer = DOREnforcer(cloud_id, project_root, dry_run=True)
    results = enforcer.execute()

    print("\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)
    print(f"\nResults: {json.dumps(results['compliance_summary'], indent=2)}")


if __name__ == "__main__":
    main()
