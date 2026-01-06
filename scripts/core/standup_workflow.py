#!/usr/bin/env python3
"""
Daily Standup Workflow - Complete 7-Part Analysis
Coordinates all PM subagents to generate comprehensive standup report

Sections:
1. Sprint Burndown Analysis
2. Code-Ticket Gap Detection
3. Developer Productivity Audit
4. Team Timesheet Analysis
5. SLA Violations & Follow-Up Tracking
6. Deadline Risk Dashboard
7. Missing Estimates, Deadlines & Stalled Refinement
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

# Add parent to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Import DOR Enforcer
from dor_enforcement import DOREnforcer


class StandupWorkflow:
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.project_root = PROJECT_ROOT
        self.data_dir = self.project_root / ".claude" / "data"
        self.standup_dir = self.data_dir / "standups"
        self.standup_dir.mkdir(parents=True, exist_ok=True)

        self.report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "sections": {},
            "action_items": [],
            "errors": []
        }

        # Get CloudId from env
        self.cloud_id = os.getenv("ATLASSIAN_CLOUD_ID", "67bbfd03-b309-414f-9640-908213f80628")

    def log(self, message: str):
        """Print log message"""
        print(message)

    def section_header(self, title: str):
        """Print section header"""
        self.log(f"\n{'='*60}")
        self.log(f"  {title}")
        self.log(f"{'='*60}\n")

    def test_mcp_connection(self) -> bool:
        """
        Test MCP connection with a lightweight query
        Returns True if healthy, False if connection issues
        """
        self.log("🔍 Testing MCP connection...")

        prompt = """Use the Atlassian MCP getAccessibleAtlassianResources tool to get cloud info.

Return ONLY a JSON object: {"status": "ok", "connected": true}

NO additional text, ONLY the JSON object."""

        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "text", "--settings", ".claude/settings.local.json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30,  # Short timeout for health check
                cwd=self.project_root
            )

            if result.returncode == 0 and ("ok" in result.stdout or "connected" in result.stdout):
                self.log("✅ MCP connection healthy")
                return True
            else:
                self.log(f"❌ MCP connection failed: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            self.log("❌ MCP health check timed out after 30 seconds")
            return False
        except Exception as e:
            self.log(f"❌ MCP health check error: {e}")
            return False

    def alert_mcp_failure(self):
        """Post MCP connection failure to Slack logs"""
        if self.dry_run:
            self.log("🔇 Dry-run mode: Would alert MCP failure to Slack")
            return

        slack_token = os.getenv("SLACK_BOT_TOKEN")
        logs_channel = os.getenv("SLACK_PM_AGENT_LOG_CHANNEL")

        if not slack_token or not logs_channel:
            self.log("⚠️ Cannot alert to Slack: Missing credentials")
            return

        try:
            import requests

            message = """🚨 *PM Agent Alert: MCP Connection Failure*

The Atlassian MCP connection is down or authentication has expired.

*Action Required:*
1. Run `/mcp` command in Claude Code to reconnect
2. Check MCP server status in `.mcp.json`
3. Re-run standup workflow after reconnection: `python scripts/standup_workflow.py`

*Impact:* Daily standup workflow cannot query Jira data. Sections 1-3 will fail.

*Troubleshooting:*
- Check if `claude --mcp atlassian` responds
- Verify Atlassian credentials in `.env`
- Restart Claude Code if necessary"""

            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": logs_channel.strip('"'),
                    "text": "MCP Connection Failure",
                    "blocks": [{
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message}
                    }]
                }
            )

            if response.ok:
                self.log("✅ MCP failure alert posted to Slack")
            else:
                self.log(f"❌ Failed to post alert: {response.text}")

        except Exception as e:
            self.log(f"❌ Error alerting MCP failure: {e}")

    def run_section_1_sprint_burndown(self):
        """
        Section 1: Sprint Burndown Analysis
        Uses Claude Code MCP to get current sprint data from Jira
        """
        self.section_header("📊 SECTION 1: SPRINT BURNDOWN ANALYSIS")

        try:
            self.log("Querying Jira via Claude Code MCP...")

            # Create prompt for Claude Code to execute MCP query
            prompt = f"""Use the Atlassian MCP searchJiraIssuesUsingJql tool to query:

CloudId: {self.cloud_id}
JQL: project = ECD AND sprint in openSprints()

Analyze the results and return ONLY a JSON object with these fields:
{{
  "total_issues": <count>,
  "status_breakdown": {{"<status>": <count>, ...}},
  "completion_pct": <percentage of Done issues>,
  "priority_breakdown": {{"<priority>": <count>, ...}},
  "at_risk": <true/false based on < 50% completion>,
  "top_5_tickets": [
    {{"key": "<KEY>", "summary": "<summary>", "status": "<status>", "assignee": "<name>"}},
    ...
  ]
}}

NO additional text, ONLY the JSON object."""

            # Execute Claude Code with MCP access
            result = subprocess.run(
                ["claude", "-p", "--output-format", "text", "--settings", ".claude/settings.local.json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180,  # Increased from 120 to 180 seconds for reliability
                cwd=self.project_root
            )

            if result.returncode != 0:
                raise Exception(f"Claude Code execution failed: {result.stderr}")

            # Parse JSON from response (handle markdown wrapping)
            output = result.stdout.strip()

            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            elif "```" in output:
                json_start = output.find("```") + 3
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            elif "{" in output and "}" in output:
                json_start = output.find("{")
                json_end = output.rfind("}") + 1
                json_str = output[json_start:json_end]
            else:
                raise Exception("No JSON found in Claude Code response")

            data = json.loads(json_str)

            # Format as markdown report
            total = data.get("total_issues", 0)
            completion = data.get("completion_pct", 0)
            at_risk = data.get("at_risk", False)
            status_breakdown = data.get("status_breakdown", {})
            priority_breakdown = data.get("priority_breakdown", {})
            top_tickets = data.get("top_5_tickets", [])

            markdown = f"""**Total Issues in Sprint:** {total}
**Completion:** {completion:.1f}%
**Risk Status:** {"⚠️ AT RISK" if at_risk else "✅ ON TRACK"}

**Status Breakdown:**
"""
            for status, count in sorted(status_breakdown.items(), key=lambda x: x[1], reverse=True):
                markdown += f"- {status}: {count}\n"

            if priority_breakdown:
                markdown += f"\n**Priority Breakdown:**\n"
                for priority, count in sorted(priority_breakdown.items(), key=lambda x: x[1], reverse=True):
                    markdown += f"- {priority}: {count}\n"

            if top_tickets:
                markdown += f"\n**Top Priority Tickets:**\n"
                for ticket in top_tickets[:5]:
                    key = ticket.get("key", "???")
                    summary = ticket.get("summary", "No summary")[:60]
                    status = ticket.get("status", "Unknown")
                    assignee = ticket.get("assignee", "Unassigned")
                    markdown += f"- [{key}](https://citemed.atlassian.net/browse/{key}) - {summary}... [{status}] - {assignee}\n"

            section_data = {
                "title": "📊 SPRINT PROGRESS",
                "status": "completed",
                "output": markdown,
                "raw_data": data
            }

            self.report["sections"]["sprint_burndown"] = section_data
            self.log(f"✅ Sprint analysis complete: {total} issues, {completion:.1f}% done")

        except subprocess.TimeoutExpired:
            error_msg = "Claude Code MCP query timed out after 180 seconds"
            self.report["errors"].append(error_msg)
            self.log(f"❌ {error_msg}")
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from Claude Code response: {e}"
            self.report["errors"].append(error_msg)
            self.log(f"❌ {error_msg}")
        except Exception as e:
            self.report["errors"].append(f"Sprint burndown failed: {e}")
            self.log(f"❌ Error: {e}")

    def run_section_2_code_ticket_gaps(self):
        """
        Section 2: Code-Ticket Gap Detection
        Finds tickets in "In Progress" without recent git activity
        """
        self.section_header("🚨 SECTION 2: CODE-TICKET GAP DETECTION")

        try:
            self.log("Checking for tickets without git activity...")

            # This requires:
            # 1. Get all "In Progress" tickets from Jira via MCP
            # 2. Check git activity in citemed_web repo
            # 3. Cross-reference ticket keys with branch names

            section_data = {
                "title": "🚨 CODE-TICKET GAPS DETECTED",
                "status": "analysis_required",
                "mcp_query": {
                    "tool": "mcp__atlassian__searchJiraIssuesUsingJql",
                    "params": {
                        "cloudId": self.cloud_id,
                        "jql": 'project = ECD AND status = "In Progress" AND sprint in openSprints()',
                        "fields": ["summary", "assignee", "updated"],
                        "maxResults": 50
                    }
                },
                "git_check_needed": True,
                "repo_path": os.getenv("CITEMED_WEB_PATH", "/Users/ethand320/code/citemed/citemed_web")
            }

            self.report["sections"]["code_ticket_gaps"] = section_data
            self.log("✅ Gap detection section prepared (requires MCP + git analysis)")

        except Exception as e:
            self.report["errors"].append(f"Gap detection failed: {e}")
            self.log(f"❌ Error: {e}")

    def run_section_3_productivity_audit(self):
        """
        Section 3: Developer Productivity Audit
        Reviews timesheet submissions and code complexity
        """
        self.section_header("🔍 SECTION 3: DEVELOPER PRODUCTIVITY AUDIT")

        try:
            self.log("Analyzing developer productivity (last 7 days)...")

            # This would integrate with timesheet analysis scripts
            section_data = {
                "title": "🔍 PRODUCTIVITY AUDIT (Last 7 Days)",
                "status": "analysis_required",
                "requires": [
                    "Slack timesheet data analysis",
                    "Git commit analysis",
                    "Code complexity metrics",
                    "Cross-reference with Jira tickets"
                ],
                "script": "scripts/integrated_productivity_audit.py"
            }

            self.report["sections"]["productivity_audit"] = section_data
            self.log("✅ Productivity audit section prepared")

        except Exception as e:
            self.report["errors"].append(f"Productivity audit failed: {e}")
            self.log(f"❌ Error: {e}")

    def run_section_4_timesheet_analysis(self):
        """
        Section 4: Team Timesheet Analysis
        Aggregates team timesheet data
        """
        self.section_header("📈 SECTION 4: TEAM TIMESHEET ANALYSIS")

        try:
            self.log("Aggregating team timesheet data...")

            section_data = {
                "title": "📈 TEAM PRODUCTIVITY SUMMARY",
                "status": "analysis_required",
                "requires": [
                    "Extract timesheet data from Slack",
                    "Calculate total team hours",
                    "Individual developer breakdowns",
                    "Ticket correlation"
                ],
                "script": "scripts/timesheet_analyzer.py"
            }

            self.report["sections"]["timesheet_analysis"] = section_data
            self.log("✅ Timesheet analysis section prepared")

        except Exception as e:
            self.report["errors"].append(f"Timesheet analysis failed: {e}")
            self.log(f"❌ Error: {e}")

    def run_section_5_sla_monitoring(self):
        """
        Section 5: SLA Violations & Follow-Up Tracking
        Executes the existing sla_check_working.py script
        """
        self.section_header("🚨 SECTION 5: SLA VIOLATIONS & FOLLOW-UP TRACKING")

        try:
            self.log("Running SLA compliance check...")

            # Execute the existing working SLA script
            sla_script = self.project_root / "scripts" / "sla_check_working.py"

            cmd = ["python", str(sla_script)]
            if self.dry_run:
                cmd.append("--no-slack")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            section_data = {
                "title": "🚨 SLA VIOLATIONS & FOLLOW-UP TRACKING",
                "status": "completed",
                "output": result.stdout,
                "errors": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode
            }

            self.report["sections"]["sla_monitoring"] = section_data

            if result.returncode == 0:
                self.log("✅ SLA monitoring completed successfully")
            else:
                self.log(f"⚠️ SLA monitoring completed with errors (code {result.returncode})")
                self.report["errors"].append(f"SLA monitoring returned code {result.returncode}")

        except FileNotFoundError:
            error_msg = "SLA check script not found at scripts/sla_check_working.py"
            self.report["errors"].append(error_msg)
            self.log(f"❌ {error_msg}")
        except Exception as e:
            self.report["errors"].append(f"SLA monitoring failed: {e}")
            self.log(f"❌ Error: {e}")

    def run_section_7_dor_enforcement(self):
        """
        Section 7: Missing Estimates, Deadlines & Stalled Refinement
        Enforces Definition of Ready requirements
        """
        self.section_header("📋 SECTION 7: MISSING ESTIMATES, DEADLINES & STALLED REFINEMENT")

        try:
            self.log("Running Definition of Ready enforcement...")

            # Initialize DOR enforcer
            enforcer = DOREnforcer(self.cloud_id, self.project_root, dry_run=self.dry_run)

            # Execute enforcement
            results = enforcer.execute()

            # Format output
            missing_deadlines = results.get("missing_deadlines", [])
            missing_estimates = results.get("missing_estimates", [])
            stalled_refinement = results.get("stalled_refinement", [])
            actions_taken = results.get("actions_taken", {})

            output = ""

            # Missing deadlines
            if missing_deadlines:
                output += f"🚫 **IN PROGRESS WITHOUT DUE DATES ({len(missing_deadlines)} tickets)**\n\n"
                for ticket in missing_deadlines[:10]:  # Show top 10
                    key = ticket.get("key", "???")
                    summary = ticket.get("summary", "No summary")[:60]
                    assignee_field = ticket.get("assignee", "Unassigned")
                    assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                    status = ticket.get("status", "Unknown")
                    output += f"- [{key}](https://citemed.atlassian.net/browse/{key}): {summary}\n"
                    output += f"  - Assignee: {assignee} | Status: {status}\n"
                    output += f"  - ACTION: 📅 Set due date by EOD today\n\n"

            # Missing estimates
            if missing_estimates:
                output += f"\n⏱️ **IN PROGRESS WITHOUT HOURS ESTIMATE ({len(missing_estimates)} tickets)**\n\n"
                for ticket in missing_estimates[:10]:  # Show top 10
                    key = ticket.get("key", "???")
                    summary = ticket.get("summary", "No summary")[:60]
                    assignee_field = ticket.get("assignee", "Unassigned")
                    assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                    status = ticket.get("status", "Unknown")
                    output += f"- [{key}](https://citemed.atlassian.net/browse/{key}): {summary}\n"
                    output += f"  - Assignee: {assignee} | Status: {status}\n"
                    output += f"  - ACTION: ⏱️ Add Original Estimate for capacity planning\n\n"

            # Stalled refinement
            if stalled_refinement:
                output += f"\n🔄 **STALLED IN REFINEMENT (> 2 days) ({len(stalled_refinement)} tickets)**\n\n"
                for ticket in stalled_refinement[:10]:  # Show top 10
                    key = ticket.get("key", "???")
                    summary = ticket.get("summary", "No summary")[:60]
                    assignee_field = ticket.get("assignee", "Unassigned")
                    assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                    updated = ticket.get("updated", "")
                    output += f"- [{key}](https://citemed.atlassian.net/browse/{key}): {summary}\n"
                    output += f"  - Assignee: {assignee} | Last Updated: {updated}\n"
                    output += f"  - ACTION: 🚨 COMPLETE REFINEMENT - Transition to Ready for Dev/Design OR ask questions\n\n"

            # Compliance summary
            output += "\n---\n\n"
            output += "📊 **COMPLIANCE SUMMARY**\n\n"
            output += f"- Missing Deadlines: {len(missing_deadlines)} tickets\n"
            output += f"- Missing Estimates: {len(missing_estimates)} tickets\n"
            output += f"- Stalled Refinement: {len(stalled_refinement)} tickets\n\n"
            output += f"**Actions Taken:**\n"
            output += f"- Posted {actions_taken.get('deadline_comments', 0)} deadline reminders\n"
            output += f"- Posted {actions_taken.get('estimate_comments', 0)} estimate reminders\n"
            output += f"- Posted {actions_taken.get('refinement_comments', 0)} refinement reminders\n"

            if not missing_deadlines and not missing_estimates and not stalled_refinement:
                output = "✅ **All tickets have proper estimates, deadlines, and are not stalled in refinement.**\n\nNo violations found. Great work team! 🎉"

            section_data = {
                "title": "📋 MISSING ESTIMATES, DEADLINES & STALLED REFINEMENT",
                "status": "completed",
                "output": output,
                "raw_data": results
            }

            self.report["sections"]["dor_enforcement"] = section_data
            self.log("✅ DOR enforcement complete")

            # Add action items for critical violations
            if len(missing_deadlines) > 5:
                self.report["action_items"].append({
                    "priority": "HIGH",
                    "action": f"Set deadlines for {len(missing_deadlines)} active tickets",
                    "owner": "Team",
                    "source": "DOR Enforcer"
                })

            if len(stalled_refinement) > 3:
                self.report["action_items"].append({
                    "priority": "HIGH",
                    "action": f"Complete refinement for {len(stalled_refinement)} stalled tickets",
                    "owner": "Team",
                    "source": "DOR Enforcer"
                })

        except Exception as e:
            self.report["errors"].append(f"DOR enforcement failed: {e}")
            self.log(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    def generate_action_items(self):
        """
        Generate actionable items from all sections
        """
        self.log("\n📝 Generating Action Items...")

        # Action items will be derived from each section's findings
        # For now, placeholder logic
        action_items = []

        # From SLA violations
        if "sla_monitoring" in self.report["sections"]:
            sla_output = self.report["sections"]["sla_monitoring"].get("output", "")
            if "CRITICAL" in sla_output or "⚠️" in sla_output:
                action_items.append({
                    "priority": "HIGH",
                    "action": "Review and resolve SLA violations",
                    "owner": "Tech Lead",
                    "source": "SLA Monitor"
                })

        self.report["action_items"] = action_items
        self.log(f"Generated {len(action_items)} action items")

    def format_report(self) -> str:
        """
        Format the complete standup report as markdown
        """
        date = self.report["date"]
        timestamp = self.report["timestamp"]

        md = f"""# 🏃‍♂️ DAILY STANDUP REPORT - {date}

**Generated:** {timestamp}

---

"""

        # Add each section
        for section_key, section_data in self.report["sections"].items():
            title = section_data.get("title", section_key.upper())
            md += f"## {title}\n\n"

            if section_data.get("status") == "completed":
                output = section_data.get("output", "")
                md += f"{output}\n\n"
            elif section_data.get("status") == "analysis_required":
                md += "_Section requires Claude MCP execution for real-time analysis_\n\n"
                if "mcp_query" in section_data:
                    md += f"**MCP Query Required:**\n```json\n{json.dumps(section_data['mcp_query'], indent=2)}\n```\n\n"

            md += "---\n\n"

        # Add action items
        if self.report["action_items"]:
            md += "## 💡 ACTION ITEMS\n\n"
            for item in self.report["action_items"]:
                priority = item.get("priority", "MEDIUM")
                action = item.get("action", "")
                owner = item.get("owner", "Unassigned")
                md += f"- **[{priority}]** {action} - _{owner}_\n"
            md += "\n---\n\n"

        # Add errors if any
        if self.report["errors"]:
            md += "## ⚠️ REPORT GENERATION NOTES\n\n"
            for error in self.report["errors"]:
                md += f"- {error}\n"
            md += "\n---\n\n"

        md += f"**Next Standup:** {date} (automated daily at 9am)\n"

        return md

    def save_report(self, markdown_report: str):
        """
        Save report to file system
        """
        report_file = self.standup_dir / f"{self.report['date']}-standup.md"

        try:
            report_file.write_text(markdown_report)
            self.log(f"\n💾 Report saved to: {report_file}")

            # Also save JSON for programmatic access
            json_file = self.standup_dir / f"{self.report['date']}-standup.json"
            json_file.write_text(json.dumps(self.report, indent=2))
            self.log(f"💾 JSON report saved to: {json_file}")

        except Exception as e:
            self.log(f"❌ Error saving report: {e}")

    def post_to_slack(self, markdown_report: str):
        """
        Post report to Slack channels (standup + pm-agent-logs)
        """
        if self.dry_run:
            self.log("\n🔇 Dry-run mode: Skipping Slack posting")
            return

        slack_token = os.getenv("SLACK_BOT_TOKEN")
        standup_channel = os.getenv("SLACK_CHANNEL_STANDUP")
        logs_channel = os.getenv("SLACK_PM_AGENT_LOG_CHANNEL")

        if not slack_token:
            self.log("\n⚠️ Slack not configured (missing SLACK_BOT_TOKEN)")
            return

        try:
            import requests

            # Split report into chunks (Slack has 3000 char limit per section)
            chunks = []
            current_chunk = ""

            for line in markdown_report.split("\n"):
                if len(current_chunk) + len(line) + 1 > 2800:  # Leave buffer
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            # Create blocks for each chunk
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🏃‍♂️ Daily Standup Report - {self.report['date']}"
                    }
                }
            ]

            for i, chunk in enumerate(chunks):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": chunk
                    }
                })

            # Post to standup channel
            if standup_channel:
                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": standup_channel.strip('"'),
                        "text": f"Daily Standup Report - {self.report['date']}",
                        "blocks": blocks
                    }
                )

                if response.ok:
                    self.log(f"\n✅ Report posted to standup channel ({standup_channel})")
                else:
                    self.log(f"\n❌ Failed to post to standup channel: {response.text}")

            # Post to pm-agent-logs channel
            if logs_channel:
                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": logs_channel.strip('"'),
                        "text": f"Daily Standup Report - {self.report['date']}",
                        "blocks": blocks
                    }
                )

                if response.ok:
                    self.log(f"✅ Report posted to pm-agent-logs channel ({logs_channel})")
                else:
                    self.log(f"❌ Failed to post to pm-agent-logs: {response.text}")

        except Exception as e:
            self.log(f"\n❌ Error posting to Slack: {e}")

    def post_violations_to_slack(self):
        """
        Post individual violation messages to Slack for threaded discussions
        Each violation gets its own message that can be replied to
        """
        if self.dry_run:
            self.log("\n🔇 Dry-run mode: Skipping individual violation posting")
            return

        slack_token = os.getenv("SLACK_BOT_TOKEN")
        standup_channel = os.getenv("SLACK_CHANNEL_STANDUP")

        if not slack_token or not standup_channel:
            self.log("\n⚠️ Slack not configured for violation posting")
            return

        try:
            import requests

            # Get DOR enforcement results
            dor_data = self.report["sections"].get("dor_enforcement", {}).get("raw_data", {})

            missing_deadlines = dor_data.get("missing_deadlines", [])
            missing_estimates = dor_data.get("missing_estimates", [])
            stalled_refinement = dor_data.get("stalled_refinement", [])

            violation_count = 0

            # Post missing deadline violations
            for ticket in missing_deadlines[:10]:  # Limit to 10 per category
                key = ticket.get("key", "???")
                summary = ticket.get("summary", "No summary")[:80]
                assignee_field = ticket.get("assignee", "Unassigned")
                assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                status = ticket.get("status", "Unknown")

                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📅 Missing Deadline: {key}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{summary}*\n\n*Status:* {status}\n*Assignee:* {assignee}\n\n⚠️ This ticket has been in progress without a due date."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Required Action:* Set a due date by EOD today for capacity planning and sprint tracking."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Jira"
                                },
                                "url": f"https://citemed.atlassian.net/browse/{key}",
                                "style": "primary"
                            }
                        ]
                    }
                ]

                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": standup_channel.strip('"'),
                        "text": f"📅 Missing Deadline: {key}",
                        "blocks": blocks
                    }
                )

                if response.ok:
                    violation_count += 1
                    self.log(f"  ✅ Posted missing deadline violation: {key}")

            # Post missing estimate violations
            for ticket in missing_estimates[:10]:
                key = ticket.get("key", "???")
                summary = ticket.get("summary", "No summary")[:80]
                assignee_field = ticket.get("assignee", "Unassigned")
                assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                status = ticket.get("status", "Unknown")

                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"⏱️ Missing Hours Estimate: {key}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{summary}*\n\n*Status:* {status}\n*Assignee:* {assignee}\n\n⚠️ This ticket does not have an Original Estimate set."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Required Action:* Add time estimate in the 'Original Estimate' field for capacity planning."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Jira"
                                },
                                "url": f"https://citemed.atlassian.net/browse/{key}",
                                "style": "primary"
                            }
                        ]
                    }
                ]

                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": standup_channel.strip('"'),
                        "text": f"⏱️ Missing Hours Estimate: {key}",
                        "blocks": blocks
                    }
                )

                if response.ok:
                    violation_count += 1
                    self.log(f"  ✅ Posted missing estimate violation: {key}")

            # Post stalled refinement violations
            for ticket in stalled_refinement[:10]:
                key = ticket.get("key", "???")
                summary = ticket.get("summary", "No summary")[:80]
                assignee_field = ticket.get("assignee", "Unassigned")
                assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field) if assignee_field else "Unassigned"
                updated = ticket.get("updated", "")

                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🔄 Stalled in Refinement: {key}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{summary}*\n\n*Assignee:* {assignee}\n*Last Updated:* {updated}\n\n🚨 This ticket has been in refinement for more than 2 days."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Required Action:*\n1. Transition to 'Ready for Development' if complete\n2. Transition to 'Ready for Design' if design is needed\n3. Ask clarifying questions if more info is required"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View in Jira"
                                },
                                "url": f"https://citemed.atlassian.net/browse/{key}",
                                "style": "danger"
                            }
                        ]
                    }
                ]

                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": standup_channel.strip('"'),
                        "text": f"🔄 Stalled in Refinement: {key}",
                        "blocks": blocks
                    }
                )

                if response.ok:
                    violation_count += 1
                    self.log(f"  ✅ Posted stalled refinement violation: {key}")

            self.log(f"\n✅ Posted {violation_count} individual violation messages to Slack")

        except Exception as e:
            self.log(f"\n❌ Error posting violations to Slack: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """
        Execute complete standup workflow
        """
        self.log(f"\n{'='*60}")
        self.log("  🏃‍♂️ DAILY STANDUP WORKFLOW")
        self.log(f"  Date: {self.report['date']}")
        self.log(f"  Time: {self.report['timestamp']}")
        self.log(f"  Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        self.log(f"{'='*60}")

        # Test MCP connection before running workflow
        if not self.test_mcp_connection():
            self.alert_mcp_failure()
            self.report["errors"].append("MCP connection failed - workflow aborted")
            self.log("\n❌ Aborting workflow due to MCP connection failure")
            self.log("   Please reconnect MCP and try again: /mcp")
            return 1

        # Execute all 7 sections
        self.run_section_1_sprint_burndown()
        self.run_section_2_code_ticket_gaps()
        self.run_section_3_productivity_audit()
        self.run_section_4_timesheet_analysis()
        self.run_section_5_sla_monitoring()
        # Section 6 (Deadline Risk Dashboard) - Future implementation
        self.run_section_7_dor_enforcement()

        # Generate action items
        self.generate_action_items()

        # Format report
        markdown_report = self.format_report()

        # Save report
        self.save_report(markdown_report)

        # Post to Slack
        self.post_to_slack(markdown_report)

        # Post individual violations for threaded discussions
        self.post_violations_to_slack()

        # Final summary
        self.section_header("✅ STANDUP WORKFLOW COMPLETE")
        self.log(f"Sections completed: {len(self.report['sections'])}")
        self.log(f"Action items generated: {len(self.report['action_items'])}")
        self.log(f"Errors encountered: {len(self.report['errors'])}")

        if self.report['errors']:
            self.log("\n⚠️ Errors:")
            for error in self.report['errors']:
                self.log(f"  - {error}")

        return 0 if not self.report['errors'] else 1


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Daily Standup Workflow")
    parser.add_argument("--dry-run", action="store_true", help="Run without posting to Slack")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--date", type=str, help="Run for specific date (YYYY-MM-DD)")

    args = parser.parse_args()

    workflow = StandupWorkflow(dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(workflow.run())


if __name__ == "__main__":
    main()