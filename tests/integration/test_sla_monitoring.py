#!/usr/bin/env python3
"""
Test SLA Monitoring System

Tests the refactored check_jira_slas_direct() function without posting to Slack/Jira.
This is a DRY-RUN test that verifies violation detection logic.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the function we're testing
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sla_check_working",
    PROJECT_ROOT / "scripts" / "core" / "sla_check_working.py"
)
sla_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sla_module)


def create_mock_jira_ticket(
    key: str,
    status: str,
    updated_hours_ago: float,
    priority: str = "Medium",
    assignee: str = "developer@example.com"
):
    """Create a mock Jira ticket for testing"""
    updated_dt = datetime.now() - timedelta(hours=updated_hours_ago)

    return {
        "key": key,
        "status": status,
        "priority": priority,
        "assignee": assignee,
        "updated": updated_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00",
        "summary": f"Test ticket {key}",
        "labels": []
    }


def create_mock_search_response(tickets):
    """Create a mock response from Jira search tool"""
    return json.dumps({
        "issues": tickets,
        "total": len(tickets)
    })


class TestSLAMonitoring:
    """Test suite for SLA monitoring system"""

    def test_qa_violations_24h_threshold(self):
        """Test that tickets in QA > 24h are flagged as violations"""
        print("\n" + "=" * 60)
        print("TEST 1: QA Violations (24h Threshold)")
        print("=" * 60)

        # Create test tickets (using safe margins to account for timezone handling)
        tickets = [
            create_mock_jira_ticket("ECD-100", "In QA", updated_hours_ago=12),  # OK (well under 24h)
            create_mock_jira_ticket("ECD-101", "In QA", updated_hours_ago=26),  # WARNING
            create_mock_jira_ticket("ECD-102", "QA", updated_hours_ago=50),     # CRITICAL
            create_mock_jira_ticket("ECD-103", "Ready for QA", updated_hours_ago=30),  # WARNING
            create_mock_jira_ticket("ECD-104", "In Progress", updated_hours_ago=30),  # Not QA - OK
        ]

        mock_response = create_mock_search_response(tickets)

        # Mock the subprocess call
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Run the check
            violations = sla_module.check_jira_slas_direct()

        # Find QA violations
        qa_violations = [v for v in violations if v['type'] == 'qa_stale']

        print(f"\n📊 Found {len(qa_violations)} QA violations:")
        for v in qa_violations:
            print(f"  - {v['item_id']}: {v['severity']} ({v['hours_overdue']:.1f}h overdue)")
            print(f"    Message: {v['message']}")

        # Assertions
        assert len(qa_violations) == 3, f"Expected 3 QA violations, got {len(qa_violations)}"

        # Check ECD-101 (26h - warning)
        ecd101 = next((v for v in qa_violations if v['item_id'] == 'ECD-101'), None)
        assert ecd101 is not None, "ECD-101 should be flagged"
        assert ecd101['severity'] == 'warning', "ECD-101 should be warning (< 48h)"

        # Check ECD-102 (50h - critical)
        ecd102 = next((v for v in qa_violations if v['item_id'] == 'ECD-102'), None)
        assert ecd102 is not None, "ECD-102 should be flagged"
        assert ecd102['severity'] == 'critical', "ECD-102 should be critical (> 48h)"

        # Check ECD-103 (30h - warning)
        ecd103 = next((v for v in qa_violations if v['item_id'] == 'ECD-103'), None)
        assert ecd103 is not None, "ECD-103 (Ready for QA) should be flagged"
        assert ecd103['severity'] == 'warning', "ECD-103 should be warning"

        print("\n✅ QA violation detection working correctly!")


    def test_pending_approval_violations_48h_threshold(self):
        """Test that tickets in Pending Approval > 48h are flagged"""
        print("\n" + "=" * 60)
        print("TEST 2: Pending Approval Violations (48h Threshold)")
        print("=" * 60)

        tickets = [
            create_mock_jira_ticket("ECD-200", "Pending Approval", updated_hours_ago=40),  # OK
            create_mock_jira_ticket("ECD-201", "Pending Approval", updated_hours_ago=50),  # WARNING
            create_mock_jira_ticket("ECD-202", "Pending Approval", updated_hours_ago=75),  # CRITICAL
        ]

        mock_response = create_mock_search_response(tickets)

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            violations = sla_module.check_jira_slas_direct()

        approval_violations = [v for v in violations if v['type'] == 'pending_approval']

        print(f"\n📊 Found {len(approval_violations)} Pending Approval violations:")
        for v in approval_violations:
            print(f"  - {v['item_id']}: {v['severity']} ({v['hours_overdue']:.1f}h overdue)")

        assert len(approval_violations) == 2, f"Expected 2 violations, got {len(approval_violations)}"

        ecd201 = next((v for v in approval_violations if v['item_id'] == 'ECD-201'), None)
        assert ecd201 is not None
        assert ecd201['severity'] == 'warning'

        ecd202 = next((v for v in approval_violations if v['item_id'] == 'ECD-202'), None)
        assert ecd202 is not None
        assert ecd202['severity'] == 'critical'

        print("\n✅ Pending Approval violation detection working correctly!")


    def test_blocked_ticket_violations_24h_threshold(self):
        """Test that blocked tickets without updates > 24h are flagged"""
        print("\n" + "=" * 60)
        print("TEST 3: Blocked Ticket Violations (24h Threshold)")
        print("=" * 60)

        tickets = [
            create_mock_jira_ticket("ECD-300", "Blocked", updated_hours_ago=12),  # OK (well under 24h)
            create_mock_jira_ticket("ECD-301", "Blocked", updated_hours_ago=26),  # WARNING
            create_mock_jira_ticket("ECD-302", "Blocked", updated_hours_ago=50),  # CRITICAL
        ]

        # Add 'blocked' label to ticket
        tickets.append({
            **create_mock_jira_ticket("ECD-303", "In Progress", updated_hours_ago=30),
            "labels": ["blocked", "urgent"]
        })

        mock_response = create_mock_search_response(tickets)

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            violations = sla_module.check_jira_slas_direct()

        blocked_violations = [v for v in violations if v['type'] == 'blocked_ticket']

        print(f"\n📊 Found {len(blocked_violations)} Blocked ticket violations:")
        for v in blocked_violations:
            print(f"  - {v['item_id']}: {v['severity']} ({v['hours_overdue']:.1f}h overdue)")

        assert len(blocked_violations) == 3, f"Expected 3 violations, got {len(blocked_violations)}"

        # Check ECD-303 (labeled as blocked)
        ecd303 = next((v for v in blocked_violations if v['item_id'] == 'ECD-303'), None)
        assert ecd303 is not None, "ECD-303 with 'blocked' label should be flagged"

        print("\n✅ Blocked ticket violation detection working correctly!")


    def test_no_violations_when_within_sla(self):
        """Test that tickets within SLA are not flagged"""
        print("\n" + "=" * 60)
        print("TEST 4: No Violations (All Within SLA)")
        print("=" * 60)

        tickets = [
            create_mock_jira_ticket("ECD-400", "In QA", updated_hours_ago=12),
            create_mock_jira_ticket("ECD-401", "Pending Approval", updated_hours_ago=24),
            create_mock_jira_ticket("ECD-402", "Blocked", updated_hours_ago=8),
            create_mock_jira_ticket("ECD-403", "In Progress", updated_hours_ago=72),  # Not monitored
            create_mock_jira_ticket("ECD-404", "Done", updated_hours_ago=100),  # Done - not monitored
        ]

        mock_response = create_mock_search_response(tickets)

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            violations = sla_module.check_jira_slas_direct()

        print(f"\n📊 Found {len(violations)} total violations")

        assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"

        print("\n✅ SLA compliance detection working correctly!")


    def test_mixed_violations(self):
        """Test detection across multiple violation types"""
        print("\n" + "=" * 60)
        print("TEST 5: Mixed Violations (Multiple Types)")
        print("=" * 60)

        tickets = [
            create_mock_jira_ticket("ECD-500", "In QA", updated_hours_ago=30),
            create_mock_jira_ticket("ECD-501", "Pending Approval", updated_hours_ago=60),
            create_mock_jira_ticket("ECD-502", "Blocked", updated_hours_ago=40),
            create_mock_jira_ticket("ECD-503", "In QA", updated_hours_ago=10),  # OK
            create_mock_jira_ticket("ECD-504", "In Progress", updated_hours_ago=100),  # OK - not monitored
        ]

        mock_response = create_mock_search_response(tickets)

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            violations = sla_module.check_jira_slas_direct()

        # Categorize violations
        by_type = {}
        for v in violations:
            vtype = v['type']
            by_type.setdefault(vtype, []).append(v)

        print(f"\n📊 Found {len(violations)} total violations:")
        print(f"  - QA violations: {len(by_type.get('qa_stale', []))}")
        print(f"  - Pending Approval violations: {len(by_type.get('pending_approval', []))}")
        print(f"  - Blocked ticket violations: {len(by_type.get('blocked_ticket', []))}")

        assert len(violations) == 3, f"Expected 3 violations, got {len(violations)}"
        assert len(by_type.get('qa_stale', [])) == 1
        assert len(by_type.get('pending_approval', [])) == 1
        assert len(by_type.get('blocked_ticket', [])) == 1

        print("\n✅ Mixed violation detection working correctly!")


    def test_error_handling(self):
        """Test error handling when Jira search fails"""
        print("\n" + "=" * 60)
        print("TEST 6: Error Handling (Jira Search Failure)")
        print("=" * 60)

        with patch('subprocess.run') as mock_run:
            # Simulate subprocess error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Connection timeout"
            mock_run.return_value = mock_result

            violations = sla_module.check_jira_slas_direct()

        print(f"\n📊 Returned {len(violations)} violations (should be 0 on error)")

        # Should return empty list on error, not crash
        assert violations == [], "Should return empty list on error"

        print("\n✅ Error handling working correctly!")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 SLA MONITORING TEST SUITE (DRY-RUN)")
    print("=" * 60)
    print("\nTesting check_jira_slas_direct() function")
    print("No actual Slack/Jira API calls will be made\n")

    test_suite = TestSLAMonitoring()

    tests = [
        ("QA Violations (24h)", test_suite.test_qa_violations_24h_threshold),
        ("Pending Approval (48h)", test_suite.test_pending_approval_violations_48h_threshold),
        ("Blocked Tickets (24h)", test_suite.test_blocked_ticket_violations_24h_threshold),
        ("No Violations", test_suite.test_no_violations_when_within_sla),
        ("Mixed Violations", test_suite.test_mixed_violations),
        ("Error Handling", test_suite.test_error_handling),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR in {name}")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {len(tests)}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe SLA monitoring system is working correctly:")
        print("  ✅ QA violations detected (24h threshold)")
        print("  ✅ Pending Approval violations detected (48h threshold)")
        print("  ✅ Blocked ticket violations detected (24h threshold)")
        print("  ✅ Severity levels correct (warning vs critical)")
        print("  ✅ No false positives")
        print("  ✅ Error handling works")
        print("\nThis was a DRY-RUN test - no actual Slack/Jira calls made.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
