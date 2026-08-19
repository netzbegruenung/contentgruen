import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field
from typing import Optional
from dotenv import load_dotenv

# Set up logger for module
logger = logging.getLogger(__name__)

# Load .env file if it exists (for local development)
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logger.debug(f"Loaded environment from {env_file}")


class Settings(BaseSettings):

    # Qdrant configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "content_collection"

    # Application database configuration (PostgreSQL for usage tracking, votes, etc.)
    app_database_url: str = (
        "postgresql+psycopg2://app_user:changeme@localhost:5433/contentgruen_app"
    )

    def _get_project_root(self) -> str:
        """Get the project root directory path."""
        config_file_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up from core -> app -> semantic-search-service -> backend -> mvp
        return os.path.abspath(os.path.join(config_file_dir, "..", "..", "..", ".."))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trim any whitespace from the qdrant_url
        if self.qdrant_url:
            self.qdrant_url = self.qdrant_url.strip()

        # Set up paths based on environment (Docker vs Local)
        if os.getenv("DOCKER_CONTAINER") == "true":
            # Running in Docker - paths MUST be provided via environment variables
            if not self.data_path:
                self.data_path = os.getenv(
                    "SEMANTIC_SEARCH_DATA_PATH", "/data/seed/v1.0"
                )
            if not self.metadata_path:
                self.metadata_path = os.getenv(
                    "SEMANTIC_SEARCH_METADATA_PATH", "/metadata"
                )
        else:
            # Running locally - use relative paths from project root
            project_root = self._get_project_root()
            if not self.data_path:
                self.data_path = os.path.join(project_root, "data", "seed", "v1.0")
            if not self.metadata_path:
                self.metadata_path = os.path.join(project_root, "temp_data", "metadata")

        # Legacy compatibility - will be removed in future version
        self.initial_data_path = self.data_path
        self.index_initial_data_path = os.path.join(self.data_path, "index_data")

        # Validate paths at startup
        self._validate_paths()

        # Log configuration
        logger = logging.getLogger(__name__)
        logger.debug(f"Data path: {self.data_path}")
        logger.debug(f"Metadata path: {self.metadata_path}")

    initial_data_author: str = "ContentGruen Team"

    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def get_logging_config(self):
        """Get logging configuration object."""
        from core.logging import LoggingConfig
        import os

        # Show logger names only if explicitly requested
        show_names = (
            os.getenv("SEMANTIC_SEARCH_SHOW_LOGGER_NAMES", "").lower() == "true"
        )

        return LoggingConfig(
            level=self.log_level, file_path=self.log_file, show_logger_name=show_names
        )

    # Business logic configuration
    statement_similarity_threshold: float = 0.9
    commentary_similarity_threshold: float = 0.97
    default_search_limit: int = 10
    max_reply_suggestions: int = 50
    statement_search_limit: int = 5
    min_reply_suggestions_for_search: int = 1

    # OpenAI vision API (caption suggestion + async image description)
    # Accepts bare OPENAI_API_KEY (SDK default) or the prefixed SEMANTIC_SEARCH_OPENAI_API_KEY.
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENAI_API_KEY", "SEMANTIC_SEARCH_OPENAI_API_KEY"
        ),
    )
    openai_vision_model: str = "gpt-4o-mini"

    # Admin users (comma-separated list)
    admin_users: str = ""

    def is_admin_user(self, user_id: Optional[str]) -> bool:
        """Check if a user is an admin.

        Args:
            user_id: User identifier to check

        Returns:
            True if user is admin, False otherwise
        """
        if not user_id or not self.admin_users:
            return False
        admin_list = [u.strip() for u in self.admin_users.split(",") if u.strip()]
        return user_id in admin_list

    # Secret key for the daily search-actor pseudonym (see SearchTrackingService).
    # Set SEMANTIC_SEARCH_ACTOR_HASH_SECRET in production so the daily-active-user
    # count stays correct across service restarts. If it is left unset a random
    # secret is generated per process: privacy-safe, but every restart starts a new
    # pseudonym space and inflates the DAU count for that day.
    actor_hash_secret: Optional[str] = None

    # Usage tracking and cleanup configuration
    enable_usage_cleanup: bool = True
    usage_retention_days: int = 90
    cleanup_hour: int = 2  # 2 AM
    cleanup_minute: int = 0

    # Polarity filtering configuration
    enable_polarity_filtering: bool = (
        True  # Enable negation detection and polarity filtering
    )

    # Keyword overlap boosting configuration
    enable_keyword_overlap_boost: bool = (
        True  # Enable keyword overlap boosting for search results
    )
    keyword_overlap_boost_strength: float = (
        0.15  # Strength of keyword overlap boost/penalty (0.0-1.0)
    )

    # Path configuration
    # Override with SEMANTIC_SEARCH_DATA_PATH and SEMANTIC_SEARCH_METADATA_PATH env vars
    data_path: str = ""  # Path to seed data (e.g., /data/seed/v1.0)
    metadata_path: str = ""  # Path to persistent metadata storage

    # Legacy fields - deprecated, use data_path instead
    initial_data_path: str = ""  # Deprecated: use data_path
    index_initial_data_path: str = ""  # Deprecated: for backward compatibility only

    class Config:
        # Loads all env variables starting with the prefix
        env_prefix = "SEMANTIC_SEARCH_"
        # Also load standard environment variables for logging
        env_ignore_empty = True

    def _validate_paths(self):
        """Validate that required paths exist or can be created."""
        logger = logging.getLogger(__name__)

        # Data path validation
        if not os.path.exists(self.data_path):
            if os.getenv("DOCKER_CONTAINER") == "true":
                # In Docker, missing data path is critical
                raise ValueError(
                    f"Data path does not exist: {self.data_path}\n"
                    f"Please ensure the data volume is mounted correctly in docker-compose.yml"
                )
            else:
                # For local development, warn but continue
                logger.warning(
                    f"Data path not found at {self.data_path}. "
                    f"Seeding will not be available until path exists."
                )
        else:
            # Verify expected structure exists
            expected_dirs = [
                "statements_with_commentaries",
                "statements_with_generictexts",
            ]
            missing_dirs = [
                d
                for d in expected_dirs
                if not os.path.exists(os.path.join(self.data_path, d))
            ]
            if missing_dirs and os.listdir(
                self.data_path
            ):  # Only warn if directory is not empty
                logger.debug(
                    f"Expected directories not found in {self.data_path}: {missing_dirs}"
                )

        # Create metadata directory if it doesn't exist
        os.makedirs(self.metadata_path, exist_ok=True)
        logger.debug(f"Metadata directory ensured at: {self.metadata_path}")


# Create global settings instance
settings = Settings()
