#!/usr/bin/env python3
"""
Hybrid Agent Architecture Prototype

Demonstrates how to preserve hardcore deterministic processes
while adding intelligent decision-making via Claude Agent SDK.

Key Principle:
- Math/Logic = Pure Python (deterministic)
- Decisions/Communication = LLM (intelligent, adaptive)
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========================================
# LAYER 1: Deterministic Core (Pure Python)
# ========================================

class DeterministicSLAChecker:
    """
    Hardcore SLA checking with ZERO LLM interpretation.
    Always produces same output for same input.
    """

    # EXPLICIT THRESHOLDS - No ambiguity
    QA_SLA_HOURS = 24
    APPROVAL_SLA_HOURS = 48
    BLOCKED_SLA_HOURS = 24

    # EXPLICIT STATUS NAMES - No interpretation needed
    QA_STATUSES = ['In QA', 'QA', 'Ready for QA']
    APPROVAL_STATUSES = ['Pending Approval']
    BLOCKED_STATUSES = ['Blocked']

    @staticmethod
    def check_qa_violations(tickets: List[Dict]) -> List[Dict]:
        """
        Deterministic QA violation detection.
        No LLM involved - pure boolean logic.
        """
        violations = []

        for ticket in tickets:
            status = ticket['status']

            # EXPLICIT CONDITION - No interpretation
            if status not in DeterministicSLAChecker.QA_STATUSES:
                continue

            # DETERMINISTIC CALCULATION
            updated = datetime.fromisoformat(ticket['updated'].replace('Z', '+00:00'))
            now = datetime.now(updated.tzinfo)
            hours_in_status = (now - updated).total_seconds() / 3600

            # EXPLICIT THRESHOLD CHECK
            if hours_in_status > DeterministicSLAChecker.QA_SLA_HOURS:
                # DETERMINISTIC SEVERITY CALCULATION
                severity = 'critical' if hours_in_status > 48 else 'warning'
                hours_overdue = hours_in_status - DeterministicSLAChecker.QA_SLA_HOURS

                violations.append({
                    'ticket_key': ticket['key'],
                    'type': 'qa_stale',
                    'status': status,
                    'hours_in_status': round(hours_in_status, 1),
                    'threshold': DeterministicSLAChecker.QA_SLA_HOURS,
                    'hours_overdue': round(hours_overdue, 1),
                    'severity': severity,
                    'assignee': ticket.get('assignee', 'Unassigned'),
                    'last_comment': ticket.get('last_comment'),
                    'detected_at': now.isoformat()
                })

        return violations

    @staticmethod
    def check_approval_violations(tickets: List[Dict]) -> List[Dict]:
        """Deterministic approval SLA check"""
        violations = []

        for ticket in tickets:
            if ticket['status'] not in DeterministicSLAChecker.APPROVAL_STATUSES:
                continue

            updated = datetime.fromisoformat(ticket['updated'].replace('Z', '+00:00'))
            now = datetime.now(updated.tzinfo)
            hours_in_status = (now - updated).total_seconds() / 3600

            if hours_in_status > DeterministicSLAChecker.APPROVAL_SLA_HOURS:
                severity = 'critical' if hours_in_status > 72 else 'warning'

                violations.append({
                    'ticket_key': ticket['key'],
                    'type': 'pending_approval',
                    'status': ticket['status'],
                    'hours_in_status': round(hours_in_status, 1),
                    'threshold': DeterministicSLAChecker.APPROVAL_SLA_HOURS,
                    'hours_overdue': round(hours_in_status - DeterministicSLAChecker.APPROVAL_SLA_HOURS, 1),
                    'severity': severity,
                    'assignee': ticket.get('assignee'),
                    'detected_at': now.isoformat()
                })

        return violations

    @staticmethod
    def check_blocked_violations(tickets: List[Dict]) -> List[Dict]:
        """Deterministic blocked ticket check"""
        violations = []

        for ticket in tickets:
            is_blocked = (
                ticket['status'] in DeterministicSLAChecker.BLOCKED_STATUSES or
                'blocked' in [label.lower() for label in ticket.get('labels', [])]
            )

            if not is_blocked:
                continue

            updated = datetime.fromisoformat(ticket['updated'].replace('Z', '+00:00'))
            now = datetime.now(updated.tzinfo)
            hours_in_status = (now - updated).total_seconds() / 3600

            if hours_in_status > DeterministicSLAChecker.BLOCKED_SLA_HOURS:
                severity = 'critical' if hours_in_status > 48 else 'warning'

                violations.append({
                    'ticket_key': ticket['key'],
                    'type': 'blocked_ticket',
                    'status': ticket['status'],
                    'hours_in_status': round(hours_in_status, 1),
                    'threshold': DeterministicSLAChecker.BLOCKED_SLA_HOURS,
                    'hours_overdue': round(hours_in_status - DeterministicSLAChecker.BLOCKED_SLA_HOURS, 1),
                    'severity': severity,
                    'assignee': ticket.get('assignee'),
                    'detected_at': now.isoformat()
                })

        return violations


# ========================================
# LAYER 2: LLM Decision Layer
# ========================================

class PMAgentDecisionLayer:
    """
    Uses LLM ONLY for:
    1. Deciding escalation strategy
    2. Drafting contextual messages
    3. Learning from past outcomes

    Does NOT use LLM for:
    1. Calculating hours
    2. Determining thresholds
    3. Boolean logic
    """

    def __init__(self):
        self.memory = []  # Would be persistent session in real implementation

    def decide_escalation(self, violation: Dict) -> Dict:
        """
        LLM decides on escalation strategy based on:
        - Violation context (provided by deterministic layer)
        - Past escalation outcomes (memory)
        - Current team situation

        NOTE: In real implementation, this would use Claude Agent SDK
        """

        # Violation details already calculated (deterministic)
        ticket = violation['ticket_key']
        hours_overdue = violation['hours_overdue']
        severity = violation['severity']
        last_comment = violation.get('last_comment')

        # DECISION PROMPT (this is where LLM is appropriate)
        decision_prompt = f"""
**Violation Context (Already Calculated):**
- Ticket: {ticket}
- Hours overdue: {hours_overdue}h
- Severity: {severity}
- Last comment: {last_comment}

**Your Memory of Similar Cases:**
{self._recall_similar_cases(violation)}

**Decision Needed:**
1. Should we escalate immediately or wait for next check?
2. Who should be notified? (assignee, team, leadership?)
3. What tone? (gentle reminder, urgent alert, critical escalation?)
4. Should we add a Jira comment or just Slack?

**Output format:**
{{
    "action": "escalate_now" or "wait",
    "notify": ["assignee", "qa_lead", "tech_lead"],
    "tone": "gentle" or "urgent" or "critical",
    "channels": ["slack", "jira"],
    "reasoning": "Why this approach based on past outcomes"
}}
        """

        # In real implementation: Claude Agent SDK would process this
        # For prototype: return mock decision
        return {
            'action': 'escalate_now' if hours_overdue > 12 else 'wait',
            'notify': ['assignee'] if severity == 'warning' else ['assignee', 'qa_lead'],
            'tone': 'gentle' if severity == 'warning' else 'urgent',
            'channels': ['slack'] if severity == 'warning' else ['slack', 'jira'],
            'reasoning': 'Based on deterministic severity calculation'
        }

    def draft_message(self, violation: Dict, decision: Dict) -> str:
        """
        LLM drafts contextual message.
        Uses exact numbers from deterministic layer.
        """

        # MESSAGE DRAFTING PROMPT (LLM appropriate for natural language)
        draft_prompt = f"""
**Violation Facts (Exact Numbers):**
- Ticket: {violation['ticket_key']}
- Hours overdue: {violation['hours_overdue']}h (threshold: {violation['threshold']}h)
- Total time in status: {violation['hours_in_status']}h
- Severity: {violation['severity']}

**Tone Required:** {decision['tone']}
**Recipients:** {', '.join(decision['notify'])}

**Your Memory:** You previously escalated similar violations with {decision['tone']} tone
and it worked well.

**Draft a message that:**
1. States exact facts (use the numbers above - don't recalculate)
2. Uses appropriate tone for severity
3. Provides clear action items
4. References specific ticket details

Output the message only, no explanation.
        """

        # In real implementation: Claude Agent SDK would draft
        # For prototype: return template
        if decision['tone'] == 'gentle':
            return f"Hi {violation['assignee']}, {violation['ticket_key']} has been in {violation['status']} for {violation['hours_in_status']}h ({violation['hours_overdue']}h over our {violation['threshold']}h SLA). Could you provide a quick update when you have a moment? Thanks!"
        else:
            return f"⚠️ **SLA Alert**: {violation['ticket_key']} is {violation['hours_overdue']}h overdue (in {violation['status']} for {violation['hours_in_status']}h, SLA: {violation['threshold']}h). @{violation['assignee']} please prioritize or escalate if blocked."

    def _recall_similar_cases(self, violation: Dict) -> str:
        """Recall similar past violations from memory"""
        # In real implementation: Claude Agent SDK session would provide this
        return "Past similar QA violations were resolved by gentle reminders to assignee first."


# ========================================
# LAYER 3: Orchestration
# ========================================

class HybridPMAgent:
    """
    Orchestrates deterministic detection + LLM decisions.
    Best of both worlds.
    """

    def __init__(self):
        self.detector = DeterministicSLAChecker()
        self.decision_layer = PMAgentDecisionLayer()

    def run_daily_standup(self, tickets: List[Dict]) -> Dict:
        """
        Run daily standup with hybrid approach:
        1. Deterministic detection (pure Python)
        2. LLM decision-making (Claude Agent SDK)
        3. Deterministic execution (Python APIs)
        """

        print("=" * 60)
        print("HYBRID PM AGENT - DAILY STANDUP")
        print("=" * 60)

        # STEP 1: Deterministic Detection (FAST, RELIABLE)
        print("\n📊 STEP 1: Deterministic SLA Detection")
        print("-" * 60)

        qa_violations = self.detector.check_qa_violations(tickets)
        approval_violations = self.detector.check_approval_violations(tickets)
        blocked_violations = self.detector.check_blocked_violations(tickets)

        all_violations = qa_violations + approval_violations + blocked_violations

        print(f"✅ Checked {len(tickets)} tickets")
        print(f"✅ Found {len(qa_violations)} QA violations")
        print(f"✅ Found {len(approval_violations)} approval violations")
        print(f"✅ Found {len(blocked_violations)} blocked violations")
        print(f"✅ Total violations: {len(all_violations)}")

        # STEP 2: LLM Decision-Making (INTELLIGENT, ADAPTIVE)
        print("\n🧠 STEP 2: LLM Decision Layer")
        print("-" * 60)

        actions = []
        for violation in all_violations:
            print(f"\nProcessing {violation['ticket_key']}...")
            print(f"  Facts: {violation['hours_overdue']}h overdue, severity={violation['severity']}")

            # LLM decides strategy
            decision = self.decision_layer.decide_escalation(violation)
            print(f"  Decision: {decision['action']} - notify {decision['notify']}")

            # LLM drafts message
            message = self.decision_layer.draft_message(violation, decision)
            print(f"  Message: {message[:100]}...")

            actions.append({
                'violation': violation,
                'decision': decision,
                'message': message
            })

        # STEP 3: Deterministic Execution (RELIABLE)
        print("\n📤 STEP 3: Execute Actions")
        print("-" * 60)

        for action in actions:
            if action['decision']['action'] == 'escalate_now':
                print(f"✅ Would post to Slack: {action['violation']['ticket_key']}")
                if 'jira' in action['decision']['channels']:
                    print(f"✅ Would comment on Jira: {action['violation']['ticket_key']}")

        return {
            'violations_detected': len(all_violations),
            'actions_taken': len([a for a in actions if a['decision']['action'] == 'escalate_now']),
            'actions': actions
        }


# ========================================
# DEMO
# ========================================

def run_demo():
    """Demonstrate hybrid architecture with mock data"""

    # Mock tickets (in real system, this comes from Jira API)
    now = datetime.now()
    mock_tickets = [
        {
            'key': 'ECD-585',
            'status': 'In QA',
            'updated': (now - timedelta(hours=36)).isoformat(),
            'assignee': 'Mohamed',
            'last_comment': {'author': 'QA Lead', 'text': 'Found 2 issues'},
            'labels': []
        },
        {
            'key': 'ECD-601',
            'status': 'Pending Approval',
            'updated': (now - timedelta(hours=55)).isoformat(),
            'assignee': 'Ahmed',
            'labels': []
        },
        {
            'key': 'ECD-520',
            'status': 'In Progress',
            'updated': (now - timedelta(hours=30)).isoformat(),
            'assignee': 'Thanh',
            'labels': ['blocked']
        },
        {
            'key': 'ECD-410',
            'status': 'In QA',
            'updated': (now - timedelta(hours=12)).isoformat(),
            'assignee': 'Valentin',
            'labels': []
        }
    ]

    # Run hybrid agent
    agent = HybridPMAgent()
    result = agent.run_daily_standup(mock_tickets)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Violations detected: {result['violations_detected']}")
    print(f"✅ Actions taken: {result['actions_taken']}")
    print("\n✨ Hybrid Architecture Benefits:")
    print("  - Deterministic SLA detection (always accurate)")
    print("  - Intelligent decision-making (context-aware)")
    print("  - Learning capability (improves over time)")
    print("  - No shoe-horning (each layer does what it's best at)")


if __name__ == "__main__":
    run_demo()
