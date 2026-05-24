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
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to sys.path so src imports work
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from trinity.jira import search_jira, add_jira_comment


class DOREnforcer:
    """Definition of Ready Enforcement"""

    def __init__(self, cloud_id: str, project_root: Path, dry_run: bool = False):
        self.cloud_id = cloud_id
        self.project_root = project_root
        self.dry_run = dry_run

        # Build JQL-ready project clause (supports comma-separated project keys)
        raw_keys = [k.strip() for k in os.getenv("ATLASSIAN_PROJECT_KEY", "").split(",") if k.strip()]
        self.project_key = (
            f'project IN ({", ".join(raw_keys)})'
            if len(raw_keys) > 1
            else f'project = {raw_keys[0] if raw_keys else ""}'
        )

    def query_missing_deadlines(self) -> List[Dict]:
        """Query tickets missing due dates"""
        print("  📅 Querying tickets missing deadlines...")

        jql = (
            f'{self.project_key} AND sprint in openSprints() '
            f'AND status IN ("In Progress", "Ready for Development", "Ready for QA") '
            f'AND duedate IS EMPTY '
            f'ORDER BY status ASC, updated DESC'
        )

        result = search_jira(
            jql,
            max_results=50,
            fields=["summary", "status", "assignee", "priority", "updated"]
        )

        if result.get("error"):
            print(f"  ⚠️  Jira query failed: {result.get('message')}")
            return []

        issues = result.get("issues", [])
        print(f"  Found {len(issues)} tickets missing deadlines")
        return issues

    def query_missing_estimates(self) -> List[Dict]:
        """Query tickets missing hours estimates"""
        print("  ⏱️  Querying tickets missing hours estimates...")

        jql = (
            f'{self.project_key} AND sprint in openSprints() '
            f'AND status IN ("In Progress", "Ready for Development", "Ready for QA") '
            f'AND timeoriginalestimate IS EMPTY '
            f'ORDER BY status ASC, updated DESC'
        )

        result = search_jira(
            jql,
            max_results=50,
            fields=["summary", "status", "assignee", "priority", "updated"]
        )

        if result.get("error"):
            print(f"  ⚠️  Jira query failed: {result.get('message')}")
            return []

        issues = result.get("issues", [])
        print(f"  Found {len(issues)} tickets missing estimates")
        return issues

    def query_stalled_refinement(self) -> List[Dict]:
        """Query tickets stalled in refinement > 2 days"""
        print("  🔄 Querying tickets stalled in refinement...")

        jql = (
            f'{self.project_key} AND sprint in openSprints() '
            f'AND status = "In Refinement" '
            f'AND updated < -2d '
            f'ORDER BY updated ASC'
        )

        result = search_jira(
            jql,
            max_results=50,
            fields=["summary", "status", "assignee", "updated"]
        )

        if result.get("error"):
            print(f"  ⚠️  Jira query failed: {result.get('message')}")
            return []

        issues = result.get("issues", [])
        print(f"  Found {len(issues)} tickets stalled in refinement")
        return issues

    def post_jira_comment(self, issue_key: str, comment_text: str, mentions: Optional[list] = None) -> bool:
        """Post comment to Jira ticket"""
        if self.dry_run:
            print(f"  [DRY RUN] Would post comment to {issue_key}: {comment_text[:80]}...")
            return True

        result = add_jira_comment(issue_key, comment_text, mentions=mentions)
        if result.get("success"):
            return True
        else:
            print(f"  ⚠️  Failed to post comment to {issue_key}: {result.get('message')}")
            return False

    def generate_missing_deadline_comment(self, ticket: Dict):
        """Generate Jira comment for missing deadline. Returns (text, mentions)."""
        days_in_status = self._calculate_days_in_status(ticket.get("updated"))

        assignee_name = ticket.get("assignee") or "the assignee"
        assignee_id = ticket.get("assignee_id")

        mention_text = f"@{assignee_name}" if assignee_id else assignee_name
        mentions = [{"id": assignee_id, "name": assignee_name}] if assignee_id else None

        comment = (
            f"📅 MISSING DEADLINE\n\n"
            f"This ticket has been {ticket.get('status', 'Unknown')} for {days_in_status} days without a due date set.\n\n"
            f"Required Action: {mention_text} - Please set a due date by EOD today for capacity planning and sprint tracking.\n\n"
            f"Why this matters:\n"
            f"- Enables deadline risk monitoring\n"
            f"- Improves sprint forecasting\n"
            f"- Provides visibility to stakeholders\n\n"
            f"---\nAutomated reminder from Definition of Ready Enforcer"
        )

        return comment, mentions

    def generate_missing_estimate_comment(self, ticket: Dict):
        """Generate Jira comment for missing hours estimate. Returns (text, mentions)."""
        assignee_name = ticket.get("assignee") or "the assignee"
        assignee_id = ticket.get("assignee_id")

        mention_text = f"@{assignee_name}" if assignee_id else assignee_name
        mentions = [{"id": assignee_id, "name": assignee_name}] if assignee_id else None

        comment = (
            f"⏱️ MISSING HOURS ESTIMATE\n\n"
            f"This ticket does not have an Original Estimate set.\n\n"
            f'Required Action: {mention_text} - Please add time estimate in the "Original Estimate" field.\n\n'
            f"How to set:\n"
            f"1. Edit ticket\n"
            f'2. Find "Original Estimate" field\n'
            f'3. Enter estimate (e.g., "4h", "2d", "1w")\n\n'
            f"Why this matters:\n"
            f"- Enables capacity planning\n"
            f"- Improves sprint velocity tracking\n"
            f"- Helps identify workload imbalances\n\n"
            f"---\nAutomated reminder from Definition of Ready Enforcer"
        )

        return comment, mentions

    def generate_refinement_comment(self, ticket: Dict, has_questions: bool):
        """Generate Jira comment for stalled refinement. Returns (text, mentions)."""
        days_stalled = self._calculate_days_in_status(ticket.get("updated"))

        assignee_name = ticket.get("assignee") or "the assignee"
        assignee_id = ticket.get("assignee_id")

        mention_text = f"@{assignee_name}" if assignee_id else assignee_name
        mentions = [{"id": assignee_id, "name": assignee_name}] if assignee_id else None

        if has_questions:
            comment = (
                f"⏰ REFINEMENT REMINDER\n\n"
                f"This ticket has been in In Refinement status for {days_stalled} days with pending questions.\n\n"
                f"Required Action: {mention_text} - Please clarify the pending questions and move this ticket forward.\n\n"
                f"Status Check:\n"
                f'- Are questions answered? → Transition to "Ready for Development" or "Ready for Design"\n'
                f"- Need more info? → Follow up with stakeholders\n\n"
                f"---\nAutomated reminder from Definition of Ready Enforcer"
            )
        else:
            comment = (
                f"🚨 COMPLETE REFINEMENT\n\n"
                f"This ticket has been in In Refinement status for {days_stalled} days without any questions asked.\n\n"
                f"Required Action: {mention_text} - Please choose one:\n"
                f'1. Transition to "Ready for Development" if refinement is complete\n'
                f'2. Transition to "Ready for Design" if design is needed\n'
                f"3. Ask clarifying questions if more information is required\n\n"
                f"Why this matters:\n"
                f"- Prevents bottlenecks in refinement phase\n"
                f"- Keeps sprint velocity healthy\n"
                f"- Ensures work doesn't stall\n\n"
                f"---\nAutomated reminder from Definition of Ready Enforcer (2-day limit)"
            )

        return comment, mentions

    def _calculate_days_in_status(self, updated_str: Optional[str]) -> int:
        """Calculate days since last update"""
        if not updated_str:
            return 0

        try:
            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            now = datetime.now(updated.tzinfo)
            delta = now - updated
            return delta.days
        except Exception:
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

        # Post comments for missing deadlines (limit to 5 per run)
        for ticket in missing_deadlines[:5]:
            comment, mentions = self.generate_missing_deadline_comment(ticket)
            if self.post_jira_comment(ticket["key"], comment, mentions):
                results["actions_taken"]["deadline_comments"] += 1
                print(f"  ✅ Posted deadline reminder to {ticket['key']}")

        # Post comments for missing estimates (limit to 5 per run)
        for ticket in missing_estimates[:5]:
            comment, mentions = self.generate_missing_estimate_comment(ticket)
            if self.post_jira_comment(ticket["key"], comment, mentions):
                results["actions_taken"]["estimate_comments"] += 1
                print(f"  ✅ Posted estimate reminder to {ticket['key']}")

        # Post comments for stalled refinement (limit to 5 per run)
        for ticket in stalled_refinement[:5]:
            has_questions = False  # TODO: check comment history for open questions
            comment, mentions = self.generate_refinement_comment(ticket, has_questions)
            if self.post_jira_comment(ticket["key"], comment, mentions):
                results["actions_taken"]["refinement_comments"] += 1
                print(f"  ✅ Posted refinement reminder to {ticket['key']}")

        # Store results
        results["missing_deadlines"] = missing_deadlines
        results["missing_estimates"] = missing_estimates
        results["stalled_refinement"] = stalled_refinement

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
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")

    cloud_id = os.getenv("ATLASSIAN_CLOUD_ID", "")

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
