"""
Simple Orchestrator - Agent reasoning cycle
Flow: Webhook → Gather Context → Think (Claude) → Act → Log
"""
from src.database.models import get_session, AgentCycle, WebhookEvent
from src.clients.jira_api_client import JiraAPIClient
from anthropic import Anthropic
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class SimpleOrchestrator:
    """
    Core agent orchestration logic

    Responsibilities:
    1. Receive events (webhooks, scheduled triggers)
    2. Gather context from external systems
    3. Reason with Claude about what to do
    4. Execute actions
    5. Log everything for audit/learning
    """

    def __init__(self):
        # Initialize clients
        try:
            self.jira = JiraAPIClient()
        except ValueError:
            print("⚠️  Warning: Jira client not configured (missing credentials)")
            self.jira = None

        # Initialize Claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing ANTHROPIC_API_KEY! Set it in .env file.\n"
                "Get your key from: https://console.anthropic.com/"
            )

        self.claude = Anthropic(api_key=api_key)
        self.model = "claude-3-opus-20240229"  # Claude 3 Opus (fallback - upgrade to 3.5 Sonnet when available)

    def process_jira_comment(
        self,
        issue_key: str,
        comment_text: str,
        commenter: str
    ) -> Dict:
        """
        Process a new Jira comment
        Main entry point for comment webhook events
        """
        print(f"\n{'='*60}")
        print(f"🔄 STARTING AGENT CYCLE")
        print(f"{'='*60}")
        print(f"Trigger: Jira comment on {issue_key}")
        print(f"Commenter: {commenter}")
        print(f"Comment: {comment_text[:100]}...")
        print(f"{'='*60}\n")

        # Step 1: Gather context
        context = self._gather_context(issue_key)

        # Step 2: Think (ask Claude)
        plan = self._make_plan(issue_key, comment_text, commenter, context)

        # Step 3: Act
        actions = self._execute_plan(issue_key, plan)

        # Step 4: Log
        self._log_cycle(
            trigger_type="jira_comment",
            trigger_data={
                "issue_key": issue_key,
                "comment": comment_text,
                "commenter": commenter
            },
            context=context,
            plan=plan,
            actions=actions,
            status="complete"
        )

        print(f"\n{'='*60}")
        print(f"✅ CYCLE COMPLETE")
        print(f"{'='*60}\n")

        return {
            "status": "complete",
            "actions_count": len(actions),
            "responded": plan.get("should_respond", False)
        }

    def _gather_context(self, issue_key: str) -> Dict:
        """
        Gather context about the issue

        In a real implementation, this would:
        - Fetch issue details from Jira
        - Get recent comments
        - Check sprint status
        - Look up team member info
        """
        print(f"📊 Gathering context for {issue_key}...")

        if self.jira:
            try:
                issue = self.jira.get_issue(issue_key)
                comments = self.jira.get_comments(issue_key)

                context = {
                    "issue": {
                        "key": issue["key"],
                        "summary": issue["summary"],
                        "description": issue.get("description", "No description"),
                        "status": issue["status"],
                        "assignee": issue["assignee"],
                        "priority": issue["priority"]
                    },
                    "recent_comments": comments[-5:] if len(comments) > 5 else comments,
                    "comment_count": len(comments)
                }

                print(f"   ✓ Issue: {issue['key']} - {issue['summary']}")
                print(f"   ✓ Status: {issue['status']}")
                print(f"   ✓ Assignee: {issue['assignee']}")
                print(f"   ✓ Recent comments: {len(context['recent_comments'])}")

            except Exception as e:
                print(f"   ⚠️  Failed to fetch from Jira: {e}")
                # Use mock data for testing
                context = self._mock_context(issue_key)

        else:
            # Jira not configured, use mock data
            context = self._mock_context(issue_key)

        return context

    def _mock_context(self, issue_key: str) -> Dict:
        """Mock context for testing without Jira"""
        print(f"   ⚠️  Using mock data (Jira not configured)")
        return {
            "issue": {
                "key": issue_key,
                "summary": "Test Issue - Authentication improvements",
                "description": "Improve OAuth authentication flow",
                "status": "In Progress",
                "assignee": "Sarah Johnson",
                "priority": "High"
            },
            "recent_comments": [
                {
                    "author": "Mike Chen",
                    "body": "Started working on this",
                    "created": "2025-11-05T10:00:00Z"
                }
            ],
            "comment_count": 1
        }

    def _make_plan(
        self,
        issue_key: str,
        comment: str,
        commenter: str,
        context: Dict
    ) -> Dict:
        """
        Ask Claude to make a plan

        Claude analyzes:
        - The new comment
        - Issue context
        - Should we respond?
        - What should we say/do?
        """
        print(f"\n🧠 Asking Claude for guidance...")

        issue_data = context.get("issue", {})

        prompt = f"""You are a PM agent monitoring a software development project.

CONTEXT:
- Issue: {issue_data.get('key')} - {issue_data.get('summary')}
- Status: {issue_data.get('status')}
- Assignee: {issue_data.get('assignee')}
- Priority: {issue_data.get('priority')}

NEW COMMENT (from {commenter}):
"{comment}"

TASK:
Analyze this comment and decide if the PM agent should respond or take action.

Consider:
1. Is this a question that needs answering?
2. Is this a blocker that needs escalation?
3. Is this just an update (no response needed)?
4. Is there something actionable for the PM agent?

RESPOND IN JSON:
{{
  "should_respond": true/false,
  "response": "Your response text (if should_respond is true)",
  "reasoning": "Brief explanation of your decision",
  "urgency": "low/medium/high",
  "suggested_actions": ["action1", "action2"]
}}

Keep responses professional, concise, and helpful.
"""

        try:
            message = self.claude.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                plan = json.loads(json_match.group())
                print(f"   ✓ Decision: {'Respond' if plan.get('should_respond') else 'No action needed'}")
                print(f"   ✓ Reasoning: {plan.get('reasoning', 'N/A')[:100]}...")
                print(f"   ✓ Urgency: {plan.get('urgency', 'unknown')}")
            else:
                # Fallback if JSON parsing fails
                plan = {
                    "should_respond": False,
                    "reasoning": "Could not parse Claude's response",
                    "raw_response": response_text
                }
                print(f"   ⚠️  Failed to parse Claude response as JSON")

        except Exception as e:
            print(f"   ❌ Error calling Claude API: {e}")
            plan = {
                "should_respond": False,
                "reasoning": f"Error: {str(e)}",
                "error": str(e)
            }

        return plan

    def _execute_plan(self, issue_key: str, plan: Dict) -> List[Dict]:
        """
        Execute the plan

        For now: simulate actions (don't actually post to Jira)
        In production: call jira.add_comment() here
        """
        print(f"\n⚡ Executing plan...")
        actions = []

        if plan.get("should_respond"):
            response_text = plan.get("response", "")

            # SIMULATION MODE: Just log what we would do
            print(f"   💬 Would add Jira comment:")
            print(f"      \"{response_text[:100]}...\"")

            actions.append({
                "type": "jira_comment",
                "issue_key": issue_key,
                "text": response_text,
                "status": "simulated",  # Change to "executed" when ready for production
                "timestamp": datetime.utcnow().isoformat()
            })

            # To actually post to Jira (enable when ready):
            # if self.jira:
            #     try:
            #         self.jira.add_comment(issue_key, response_text)
            #         actions[-1]["status"] = "executed"
            #     except Exception as e:
            #         actions[-1]["status"] = "failed"
            #         actions[-1]["error"] = str(e)

        else:
            print(f"   ⏭️  No action needed")
            print(f"      Reason: {plan.get('reasoning', 'N/A')}")

        return actions

    def _log_cycle(
        self,
        trigger_type: str,
        trigger_data: Dict,
        context: Dict,
        plan: Dict,
        actions: List[Dict],
        status: str
    ):
        """
        Log the complete cycle to database
        This creates an audit trail of agent decisions
        """
        print(f"\n💾 Logging cycle to database...")

        session = get_session()
        try:
            cycle = AgentCycle(
                trigger_type=trigger_type,
                trigger_data=json.dumps(trigger_data),
                context_gathered=json.dumps(context),
                plan=json.dumps(plan),
                actions_taken=json.dumps(actions),
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


if __name__ == "__main__":
    """
    Test the orchestrator with a simulated webhook
    Run: python src/orchestration/simple_orchestrator.py
    """
    print("\n🧪 Testing Simple Orchestrator...\n")

    try:
        orchestrator = SimpleOrchestrator()

        # Simulate a Jira comment webhook
        result = orchestrator.process_jira_comment(
            issue_key="ECD-123",
            comment_text="Can someone review this PR? It's been waiting for 2 days.",
            commenter="Sarah Johnson"
        )

        print(f"\n📊 Result: {json.dumps(result, indent=2)}")
        print("\n✅ Orchestrator test complete!\n")

        # Show what was logged
        from src.database.models import get_stats
        stats = get_stats()
        print(f"📈 Database stats:")
        print(f"   Total cycles: {stats['total_cycles']}")
        if stats['recent_cycles']:
            print(f"   Most recent cycle: {stats['recent_cycles'][0]}")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure .env has:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
