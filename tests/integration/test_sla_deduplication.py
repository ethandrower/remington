#!/usr/bin/env python3
"""
Test SLA Alert Deduplication

This script tests the deduplication logic without posting to Slack.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sla_alert_tracker import should_alert_violation, record_alert, get_alert_history
from datetime import datetime, timedelta


def test_deduplication():
    """Test the SLA alert deduplication logic"""
    print("🧪 Testing SLA Alert Deduplication\n")

    # Test violation
    violation = {
        "item_id": "TEST-001",
        "type": "test_violation",
        "escalation_level": 1,
        "severity": "critical"
    }

    print("=" * 60)
    print("TEST 1: First Alert (Should Post)")
    print("=" * 60)
    result = should_alert_violation(violation)
    print(f"Result: {'✅ WILL ALERT' if result else '❌ WILL NOT ALERT'}")
    assert result == True, "First alert should always post"

    if result:
        record_alert(violation, slack_thread_ts="1234567890.123456")
        print("📝 Recorded alert\n")

    print("=" * 60)
    print("TEST 2: Immediate Re-run (Should Skip)")
    print("=" * 60)
    result = should_alert_violation(violation)
    print(f"Result: {'✅ WILL ALERT' if result else '❌ WILL NOT ALERT'}")
    assert result == False, "Should skip alert within 24 hours"
    print()

    print("=" * 60)
    print("TEST 3: Escalation Increase (Should Post)")
    print("=" * 60)
    violation["escalation_level"] = 2
    result = should_alert_violation(violation)
    print(f"Result: {'✅ WILL ALERT' if result else '❌ WILL NOT ALERT'}")
    assert result == True, "Should alert when escalation increases"

    if result:
        record_alert(violation, slack_thread_ts="1234567891.123456")
        print("📝 Recorded escalation alert\n")

    print("=" * 60)
    print("TEST 4: Same Escalation Level (Should Skip)")
    print("=" * 60)
    result = should_alert_violation(violation)
    print(f"Result: {'✅ WILL ALERT' if result else '❌ WILL NOT ALERT'}")
    assert result == False, "Should skip at same escalation level"
    print()

    print("=" * 60)
    print("TEST 5: Alert History")
    print("=" * 60)
    history = get_alert_history("TEST-001")
    print(f"Found {len(history)} alert(s) for TEST-001:")
    for alert in history:
        print(f"  - Alerted at: {alert['last_alerted_at']}")
        print(f"    Alert count: {alert['alert_count']}")
        print(f"    Escalation level: {alert['current_escalation_level']}")
        print(f"    Thread: {alert['slack_thread_ts']}")
    print()

    print("=" * 60)
    print("TEST 6: Different Violation Type (Should Post)")
    print("=" * 60)
    different_violation = {
        "item_id": "TEST-001",
        "type": "different_type",  # Different type for same item
        "escalation_level": 1,
        "severity": "warning"
    }
    result = should_alert_violation(different_violation)
    print(f"Result: {'✅ WILL ALERT' if result else '❌ WILL NOT ALERT'}")
    assert result == True, "Different violation type should alert"

    if result:
        record_alert(different_violation)
        print("📝 Recorded alert for different violation type\n")

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nDeduplication logic is working correctly!")
    print("\nNote: These test records remain in the database.")
    print("To clean up, you can delete them manually from:")
    print("  .claude/data/bot-state/slack_state.db")
    print("\nSQL to clean test data:")
    print("  DELETE FROM sla_alerts WHERE item_id LIKE 'TEST-%';")


if __name__ == "__main__":
    try:
        test_deduplication()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
