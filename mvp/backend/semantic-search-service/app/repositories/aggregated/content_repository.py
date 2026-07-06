from typing import List, Optional
import datetime
import uuid
import logging

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import (
    QdrantBaseRepository as BaseRepository,
)
from repositories.interfaces.content_repository import IContentRepository
from domain.models.content import (
    Content,
    ContentDbEntry,
    ContentSearchResult,
)
from utils.data_utils import DataLoader, DataSource
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin

logger = logging.getLogger(__name__)


class ContentRepository(
    BaseRepository[ContentDbEntry, ContentSearchResult], IContentRepository
):
    def __init__(
        self,
        settings: Settings,
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        """
        Initialize the ContentRepository with the provided Settings instance.
        Uses QdrantEmbeddingsManager for unified vector storage.

        The ContentRepository is an aggregated repository that shows ALL content types together.
        It uses content_type = None to query across all content types.

        Args:
        - settings: The Settings instance to be used by the ContentRepository.
        - embeddings_manager: Optional embeddings manager for dependency injection.
        """
        index_name = "content_index"
        content_type = None  # No filtering - shows all content types

        super().__init__(
            index_name,
            content_type,
            settings,
            ContentDbEntry,
            ContentSearchResult,
            embeddings_manager,
        )

    # ContentRepository provides aggregated view across all content types
    # No separate service wrapper needed as it's used directly by the factory
    async def initialize_index(self) -> DataSource:
        """
        Initialize the repository data.

        This method is called by the ContentOrchestrator to initialize the repository data.
        It checks if there's any content in the shared repository.
        """
        logger.info(f"Initializing {self.__class__.__name__}")

        if await self.has_content():
            logger.info(
                f"Initialized {self.__class__.__name__} - found existing content"
            )
            return DataSource.STORAGE
        else:
            logger.info(f"Executing initial data load from JSON files")
            self.initialize_with_initial_data()
            return DataSource.JSON

    def initialize_with_initial_data(self):
        """
        Initialize the ContentRepository with initial data.
        """
        # Define JSON schema for initial load data
        content_data_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "content_type": {"type": "string"},
                },
                "required": ["text", "content_type"],
                "additionalProperties": False,
            },
        }

        # Load initial data from JSON files
        initial_content_data = DataLoader.load_json_data_files(
            self.initial_data_path, content_data_schema
        )

        # Create uuids for content items without id
        for item in initial_content_data:
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

        # Parse initial content data into Content objects
        initial_content = [
            Content.model_validate(item) for item in initial_content_data
        ]

        # Create ContentInput objects from the initial content data
        now = datetime.datetime.now()
        initial_content_inputs = [
            ContentDbEntry(
                text=content.text,
                id=uuid.uuid4(),
                created=now,
                last_modified=now,
                original_author=self.initial_data_author,
                last_modified_by=self.initial_data_author,
                authors=[AuthorEntry(name=self.initial_data_author)],
                edit_history=[],
                content_type=content.content_type,
                status=ContentStatus.RELEASED_INTERNAL,
                origin=ContentOrigin.INITIAL_DATA,
            )
            for content in initial_content
        ]

        # Add the initial content data to the content repository
        for item in initial_content_inputs:
            self.upsert(item.id, item)

        logger.info(
            f"Executed initial load of data into {self.repository_name}, number of items: {len(initial_content_inputs)}"
        )
        # Note: Data is automatically persisted to Qdrant

        # Initialize usage tracking with realistic seed data
        try:
            from services.usage_tracking_service import get_usage_service
            import random

            usage_service = get_usage_service()
            for i, item in enumerate(initial_content_inputs):
                # Give initial content realistic usage numbers (5-47)
                # More popular content at the beginning
                if i < len(initial_content_inputs) * 0.2:  # Top 20%
                    usage_count = random.randint(25, 47)
                elif i < len(initial_content_inputs) * 0.5:  # Next 30%
                    usage_count = random.randint(10, 25)
                else:  # Bottom 50%
                    usage_count = random.randint(5, 15)

                usage_service.initialize_content_usage(str(item.id), usage_count)

            logger.info(
                f"Initialized usage tracking for {len(initial_content_inputs)} items"
            )
        except Exception as e:
            logger.warning(f"Could not initialize usage tracking: {e}")
            # Non-critical error - continue without usage data

    async def search(
        self, query_text: str, limit: int = 10
    ) -> List[ContentSearchResult]:
        return await super().search(query_text, limit)

    async def getAll(self, limit: int, offset: int) -> List[ContentDbEntry]:
        return await self.get_all(limit, offset)

    async def getByAuthor(
        self, user_id: str, limit: int, offset: int
    ) -> List[ContentDbEntry]:
        return await self.get_by_author(user_id, limit, offset)

    async def getCountByAuthor(self, user_id: str) -> int:
        return await self.get_count_by_author(user_id)

    async def upsert_content(self, content_input: ContentDbEntry) -> uuid.UUID:
        """
        Add or update a content item in the content index.

        Args:
        - content_input: The ContentInput object to be indexed.

        Returns:
        - The UUID of the upserted content.
        """
        await self.upsert(content_input.id, content_input)
        return content_input.id
