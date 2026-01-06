"""Quick test script for the webhook server"""
from fastapi.testclient import TestClient
from src.web.app import app

client = TestClient(app)

print("\n🧪 Testing FastAPI Server...\n")

# Test 1: Root endpoint
print("Test 1: GET /")
response = client.get("/")
assert response.status_code == 200
print(f"✅ Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 2: Health endpoint
print("\nTest 2: GET /health")
response = client.get("/health")
assert response.status_code == 200
print(f"✅ Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 3: Jira webhook endpoint
print("\nTest 3: POST /webhooks/jira")
test_payload = {
    "webhookEvent": "jira:issue_created",
    "issue": {"key": "TEST-123"}
}
response = client.post("/webhooks/jira", json=test_payload)
assert response.status_code == 200
print(f"✅ Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 4: Bitbucket webhook endpoint
print("\nTest 4: POST /webhooks/bitbucket")
test_payload = {
    "pullrequest": {"id": 456}
}
response = client.post("/webhooks/bitbucket", json=test_payload)
assert response.status_code == 200
print(f"✅ Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 5: Slack webhook endpoint (URL verification)
print("\nTest 5: POST /webhooks/slack (URL verification)")
test_payload = {
    "type": "url_verification",
    "challenge": "test_challenge_123"
}
response = client.post("/webhooks/slack", json=test_payload)
assert response.status_code == 200
assert response.json()["challenge"] == "test_challenge_123"
print(f"✅ Status: {response.status_code}")
print(f"   Response: {response.json()}")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\n📝 Next step: Run the server manually:")
print("   python src/web/app.py")
print("\n   Then test in browser:")
print("   http://localhost:8000")
print("   http://localhost:8000/docs (interactive API docs)")
print("\n")
