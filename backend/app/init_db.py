"""Database initialization script for HistoryAI-System.

Run from the backend directory:
    python -m app.init_db
"""

from app.database import Base, engine
from app import models  # noqa: F401  Ensures SQLAlchemy models are registered.


def init_database() -> None:
    """Create database tables declared by SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_database()
    print("Database tables initialized successfully.")
