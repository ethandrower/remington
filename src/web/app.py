"""
PM Agent Webhook Server - Integrated with Orchestrator
Receives webhooks and triggers agent reasoning cycles
"""
from fastapi import FastAPI, Request, BackgroundTasks
from datetime import datetime
import json
import os

# Import orchestrator and database
from src.orchestration.claude_code_orchestrator import ClaudeCodeOrchestrator
from src.database.models import get_session, WebhookEvent, init_db

# Initialize database on startup
init_db()

app = FastAPI(
    title="PM Agent Webhook Server",
    description="Receives webhooks from Jira, Bitbucket, Slack with Claude Code intelligence",
    version="0.3.0"
)

# Initialize Claude Code orchestrator (singleton)
try:
    orchestrator = ClaudeCodeOrchestrator()
    print("✅ Claude Code orchestrator initialized")
except ValueError as e:
    print(f"⚠️  Claude Code orchestrator failed: {e}")
    print("   Attempting fallback to simple orchestrator...")
    try:
        from src.orchestration.simple_orchestrator import SimpleOrchestrator
        orchestrator = SimpleOrchestrator()
        print("✅ Simple orchestrator initialized (limited functionality)")
    except:
        orchestrator = None
        print("❌ No orchestrator available - webhooks will be logged only")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PM Agent",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "phase": "0 - Hello World"
    }

@app.post("/webhooks/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Jira webhooks and trigger orchestrator"""
    payload = await request.json()
    webhook_event = payload.get('webhookEvent', 'unknown')

    # Log webhook to database
    session = get_session()
    try:
        webhook = WebhookEvent(
            source="jira",
            event_type=webhook_event,
            payload=json.dumps(payload),
            processed="pending"
        )
        session.add(webhook)
        session.commit()
        webhook_id = webhook.id
    except Exception as e:
        print(f"⚠️  Failed to log webhook: {e}")
        session.rollback()
        webhook_id = None
    finally:
        session.close()

    # Pretty print to console
    print("\n" + "="*60)
    print("📥 JIRA WEBHOOK RECEIVED")
    print("="*60)
    print(f"Event: {webhook_event}")
    print(f"Time: {datetime.utcnow().isoformat()}")
    if webhook_id:
        print(f"Webhook ID: {webhook_id}")
    print("="*60 + "\n")

    # Process comment_created events
    if webhook_event == "comment_created" and orchestrator:
        try:
            # Extract data from Jira webhook payload
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})

            issue_key = issue.get("key")
            comment_text = comment.get("body", "")  # This will be ADF format, needs parsing
            commenter = comment.get("author", {}).get("displayName", "Unknown")

            # Parse ADF comment body to plain text (simplified)
            if isinstance(comment_text, dict):
                # ADF format - extract text recursively
                def extract_text(node):
                    if isinstance(node, dict):
                        if node.get("type") == "text":
                            return node.get("text", "")
                        elif "content" in node:
                            return " ".join(extract_text(child) for child in node["content"])
                    elif isinstance(node, list):
                        return " ".join(extract_text(item) for item in node)
                    return ""

                comment_text = extract_text(comment_text).strip()

            if issue_key and comment_text:
                print(f"🤖 Triggering orchestrator for {issue_key}...")

                # Process in background so webhook returns quickly
                background_tasks.add_task(
                    process_jira_comment_task,
                    webhook_id,
                    issue_key,
                    comment_text,
                    commenter
                )

                return {
                    "status": "processing",
                    "webhook_id": webhook_id,
                    "issue_key": issue_key,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                print(f"⚠️  Missing required data (issue_key or comment_text)")
                return {
                    "status": "skipped",
                    "reason": "missing_data",
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    else:
        # Not a comment event or orchestrator not available
        reason = "no_orchestrator" if not orchestrator else "not_comment_event"
        print(f"⏭️  Skipping (reason: {reason})")
        return {
            "status": "received",
            "processed": False,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }


def process_jira_comment_task(webhook_id: int, issue_key: str, comment_text: str, commenter: str):
    """Background task to process Jira comment"""
    try:
        result = orchestrator.process_jira_comment(issue_key, comment_text, commenter)

        # Mark webhook as processed
        session = get_session()
        try:
            webhook = session.query(WebhookEvent).filter_by(id=webhook_id).first()
            if webhook:
                webhook.processed = "processed"
                session.commit()
        finally:
            session.close()

        print(f"✅ Webhook {webhook_id} processed: {result}")

    except Exception as e:
        print(f"❌ Error in background task: {e}")
        import traceback
        traceback.print_exc()

        # Mark webhook as failed
        session = get_session()
        try:
            webhook = session.query(WebhookEvent).filter_by(id=webhook_id).first()
            if webhook:
                webhook.processed = "failed"
                session.commit()
        finally:
            session.close()

@app.post("/webhooks/bitbucket")
async def bitbucket_webhook(request: Request):
    """Receive Bitbucket webhooks"""
    payload = await request.json()

    print("\n" + "="*60)
    print("📥 BITBUCKET WEBHOOK RECEIVED")
    print("="*60)
    print(f"Event: {request.headers.get('X-Event-Key', 'unknown')}")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print(f"\nPayload:\n{json.dumps(payload, indent=2)}")
    print("="*60 + "\n")

    return {
        "status": "received",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Receive Slack webhooks"""
    payload = await request.json()

    # Handle Slack URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    print("\n" + "="*60)
    print("📥 SLACK WEBHOOK RECEIVED")
    print("="*60)
    print(f"Event: {payload.get('event', {}).get('type', 'unknown')}")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print(f"\nPayload:\n{json.dumps(payload, indent=2)}")
    print("="*60 + "\n")

    return {
        "status": "received",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "🚀 Starting PM Agent Webhook Server...")
    print("📍 Server running at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    print("💚 Health check: http://localhost:8000/health\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
