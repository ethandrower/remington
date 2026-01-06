"""
Database models for PM Agent - using SQLite
Stores agent reasoning cycles and webhook events
"""
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import JSON
from datetime import datetime
import os

Base = declarative_base()


class AgentCycle(Base):
    """
    Record of each agent reasoning cycle
    Tracks: trigger -> context -> plan -> actions -> outcome
    """
    __tablename__ = "agent_cycles"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    trigger_type = Column(String(50))  # "webhook", "schedule", "manual"
    trigger_data = Column(Text)  # JSON stored as text (SQLite compatible)
    context_gathered = Column(Text)  # JSON stored as text
    plan = Column(Text)  # JSON stored as text - Claude's reasoning
    actions_taken = Column(Text)  # JSON stored as text - what agent did
    status = Column(String(20))  # "complete", "failed", "partial"

    def __repr__(self):
        return f"<AgentCycle {self.id} - {self.trigger_type} at {self.created_at}>"


class WebhookEvent(Base):
    """
    Audit log of all webhooks received
    Stores raw webhook payloads for debugging and analysis
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(50))  # "jira", "bitbucket", "slack"
    event_type = Column(String(100))  # e.g., "jira:issue_created"
    payload = Column(Text)  # JSON stored as text - full webhook payload
    processed = Column(String(20), default="pending")  # "pending", "processed", "skipped"

    def __repr__(self):
        return f"<WebhookEvent {self.id} - {self.source}:{self.event_type}>"


# Database configuration
DB_PATH = os.getenv("DB_PATH", "./data/pm_agent.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries
    connect_args={"check_same_thread": False}  # Needed for SQLite with FastAPI
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    Safe to call multiple times (won't recreate existing tables)
    """
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DB_PATH}")
    print(f"   Tables: {', '.join(Base.metadata.tables.keys())}")


def get_session():
    """
    Get a database session
    Usage:
        session = get_session()
        try:
            # do database operations
            session.commit()
        finally:
            session.close()
    """
    return SessionLocal()


def get_stats():
    """
    Get database statistics
    Returns counts of cycles and webhooks
    """
    session = get_session()
    try:
        from sqlalchemy import func

        total_cycles = session.query(func.count(AgentCycle.id)).scalar()
        total_webhooks = session.query(func.count(WebhookEvent.id)).scalar()

        # Get recent cycles
        recent_cycles = session.query(AgentCycle).order_by(
            AgentCycle.created_at.desc()
        ).limit(5).all()

        return {
            "total_cycles": total_cycles,
            "total_webhooks": total_webhooks,
            "recent_cycles": [
                {
                    "id": c.id,
                    "trigger": c.trigger_type,
                    "status": c.status,
                    "created": c.created_at.isoformat()
                }
                for c in recent_cycles
            ]
        }
    finally:
        session.close()


if __name__ == "__main__":
    """
    Run this file directly to initialize the database:
    python src/database/models.py
    """
    print("\n🔧 Initializing PM Agent Database...\n")
    init_db()

    # Show stats
    stats = get_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Total cycles: {stats['total_cycles']}")
    print(f"   Total webhooks: {stats['total_webhooks']}")

    print(f"\n💾 Database location: {os.path.abspath(DB_PATH)}")
    print("\n✅ Database ready!\n")
