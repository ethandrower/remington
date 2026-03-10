"""
Database connection factory.

Returns a SQLAlchemy engine configured for either PostgreSQL (production/Heroku)
or SQLite (local development and tests).

Priority:
  1. DATABASE_URL environment variable  →  PostgreSQL (or any supported URL)
  2. default_path argument              →  SQLite at the given file path

Usage:
    from src.database.connection import get_engine

    # Production: reads DATABASE_URL from environment
    engine = get_engine(default_path=".claude/data/bot-state/dashboard.db")

    # Tests: pass an engine directly to the DB class instead
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///path/to/test.db")
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_engine(default_path: str = None) -> Engine:
    """
    Return a SQLAlchemy engine.

    Args:
        default_path: Relative or absolute path to use for SQLite when
                      DATABASE_URL is not set. Parent directories are
                      created automatically.

    Returns:
        A configured SQLAlchemy Engine instance.

    Raises:
        ValueError: If neither DATABASE_URL nor default_path is provided.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Heroku sets postgres:// but SQLAlchemy 1.4+ requires postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return create_engine(database_url, pool_pre_ping=True)

    if default_path:
        path = Path(default_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False required for multi-threaded Flask/FastAPI use
        return create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )

    raise ValueError(
        "No database URL configured. Set the DATABASE_URL environment variable "
        "or provide a default_path."
    )
