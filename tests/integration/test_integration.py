"""
Test the integrated webhook → orchestrator flow
Tests that webhooks are received, logged to database, and trigger orchestrator
"""
import requests
import json
import time
from src.database.models import get_session, WebhookEvent, AgentCycle

def test_integration():
    """Test full webhook to orchestrator integration"""
    print("\n🧪 Testing Webhook → Orchestrator Integration...\n")

    # Server should be running at localhost:8000
    base_url = "http://localhost:8000"

    # Test 1: Health check
    print("Test 1: Health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Server is running: {response.json()}")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Server not running!")
        print("   Start it with: python -m src.web.app")
        return

    # Test 2: Send simulated Jira comment webhook
    print("\nTest 2: Simulating Jira comment webhook...")

    webhook_payload = {
        "timestamp": int(time.time() * 1000),
        "webhookEvent": "comment_created",
        "issue": {
            "key": "ECD-999",
            "fields": {
                "summary": "Test Issue - Integration Test",
                "status": {"name": "In Progress"}
            }
        },
        "comment": {
            "id": "12345",
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a test comment to verify the integration!"
                            }
                        ]
                    }
                ]
            },
            "author": {
                "displayName": "Test User",
                "accountId": "test-account-123"
            },
            "created": time.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        }
    }

    try:
        response = requests.post(
            f"{base_url}/webhooks/jira",
            json=webhook_payload,
            timeout=10
        )

        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "processing":
                print(f"   ✅ Webhook accepted and processing!")
                webhook_id = result.get("webhook_id")

                # Wait a moment for background task
                print("\n   ⏳ Waiting 2 seconds for background processing...")
                time.sleep(2)

                # Check database
                print("\nTest 3: Checking database...")
                session = get_session()
                try:
                    # Check webhook was logged
                    webhook = session.query(WebhookEvent).filter_by(id=webhook_id).first()
                    if webhook:
                        print(f"   ✅ Webhook logged: ID={webhook.id}, Status={webhook.processed}")
                    else:
                        print(f"   ⚠️  Webhook not found in database")

                    # Check if agent cycle was created
                    cycles = session.query(AgentCycle).all()
                    print(f"   📊 Total agent cycles in DB: {len(cycles)}")

                    if cycles:
                        latest = cycles[-1]
                        print(f"   ✅ Latest cycle: {latest.trigger_type} at {latest.created_at}")
                        print(f"      Status: {latest.status}")
                    else:
                        print(f"   ℹ️  No agent cycles yet (orchestrator may need ANTHROPIC_API_KEY)")

                finally:
                    session.close()

            elif result.get("status") == "received":
                reason = result.get("reason", "unknown")
                print(f"   ℹ️  Webhook received but not processed")
                print(f"      Reason: {reason}")

                if reason == "no_orchestrator":
                    print("\n   💡 Orchestrator not initialized (missing ANTHROPIC_API_KEY)")
                    print("      Add your key to .env file:")
                    print("      ANTHROPIC_API_KEY=sk-ant-your-key-here")
            else:
                print(f"   ⚠️  Unexpected status: {result.get('status')}")

        else:
            print(f"   ❌ Failed to send webhook")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n✅ Integration test complete!\n")


if __name__ == "__main__":
    test_integration()
