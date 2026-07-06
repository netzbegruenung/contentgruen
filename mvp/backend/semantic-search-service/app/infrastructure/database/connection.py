"""
Database connection management for application-specific data.
Separate from Qdrant vector database used for semantic search.
"""

import os
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from infrastructure.database.models import Base


class AppDatabase:
    """Manages connection to the application database."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection URL. If not provided, reads from Settings.
        """
        if database_url is None:
            from core.config import settings

            database_url = settings.app_database_url

        self.database_url = database_url

        # Create engine with connection pooling appropriate for FastAPI
        self.engine = create_engine(
            self.database_url,
            poolclass=NullPool,  # Use NullPool for thread safety in async context
            echo=os.getenv("APP_DATABASE_ECHO", "false").lower() == "true",
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.

        Yields:
            Session: SQLAlchemy database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close the database connection."""
        self.engine.dispose()


# Global database instance
_app_db: Optional[AppDatabase] = None


def get_app_database() -> AppDatabase:
    """
    Get or create the global application database instance.

    Returns:
        AppDatabase: The application database instance
    """
    global _app_db
    if _app_db is None:
        _app_db = AppDatabase()
        _app_db.create_tables()  # Ensure tables exist
    return _app_db


def close_app_database():
    """Close the global database connection."""
    global _app_db
    if _app_db is not None:
        _app_db.close()
        _app_db = None
