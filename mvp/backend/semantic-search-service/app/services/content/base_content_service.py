from abc import ABC
from typing import List, Type, TypeVar, Generic
import uuid
import logging

from core.config import Settings
from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from repositories.interfaces.content_repository import IContentRepository
from domain.models.content import ContentDbEntry
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from domain.models.content_status import ContentStatus
from utils.data_utils import DataSource

logger = logging.getLogger(__name__)

TRepository = TypeVar("TRepository", bound=IBaseContentRepository)
TContentDbEntry = TypeVar("TContentDbEntry", bound=BaseContentDbEntry)
TContentSearchResult = TypeVar("TContentSearchResult", bound=BaseContentSearchResult)


class BaseContentService(
    ABC, Generic[TRepository, TContentDbEntry, TContentSearchResult]
):
    def __init__(
        self,
        settings: Settings,
        repository: TRepository,
        content_repository: IContentRepository,
        content_db_entry_model_class: Type[TContentDbEntry],
        content_search_result_model_class: Type[TContentSearchResult],
    ):
        self.settings = settings
        self._repository: TRepository = repository
        self._repository_class: Type[TRepository] = type(repository)
        self._content_repository: IContentRepository = content_repository
        self.content_db_entry_model_class = content_db_entry_model_class
        self.content_search_result_model_class = content_search_result_model_class

    async def initialize_repository(self) -> DataSource:
        """
        Initialize the repository data.

        This method is called by the ContentOrchestrator to initialize the repository data.
        It checks if content exists in the shared repository, and if not, loads initial data.
        """
        logger.info(f"Initializing {self._repository_class.__name__}")

        if await self._repository.has_content():
            logger.info(
                f"Initialized {self._repository_class.__name__} - found existing content"
            )
            return DataSource.STORAGE
        else:
            logger.info(f"Executing initial data load from JSON files")
            self._repository.initialize_with_initial_data()
            return DataSource.JSON

    def save(self):
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Save requested, but data is automatically persisted to Qdrant"
        )
        # Note: With PostgreSQL backend, data is automatically persisted on upsert
        # No explicit save operation needed

    async def search(
        self, query_text: str, limit: int = 10
    ) -> List[TContentSearchResult]:
        """
        Search the repository for items similar to the provided query text.
        """
        sanitized_query_text = query_text.replace(";", ",").replace("'", '"')

        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Searching for items similar to '{sanitized_query_text}'"
        )
        return await self._repository.search(sanitized_query_text, limit)

    async def get(self, item_id: uuid.UUID) -> TContentDbEntry:
        """
        Get an item from the repository by its ID.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting item with id: {item_id}"
        )
        return await self._repository.get(item_id)

    async def add(self, input_db_entry: TContentDbEntry) -> uuid.UUID:
        """
        Public, type-agnostic ingestion entry point for a fully-formed entry.

        Registry-driven content types (see domain/content_registry.py) have no
        per-type service subclass, so input handling lives at the API/router layer
        and persists via this generic method instead of a hand-written add_* method.
        """
        return await self._upsert(input_db_entry)

    async def _upsert(self, input_db_entry: TContentDbEntry) -> uuid.UUID:
        """
        Add a new item to both content repository and the specific repository or update an existing one.

        Args:
        - item_input: The TInput object to be stored.

        Returns:
        - The UUID of the upserted item.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Upserting item of type {type(input_db_entry).__name__} with id: {input_db_entry.id}"
        )

        content_db_entry: ContentDbEntry = ContentDbEntry(
            text=input_db_entry.text or "",  # coerce None → "" for captionless images
            content_type=input_db_entry.content_type,
            id=input_db_entry.id,
            created=input_db_entry.created,
            last_modified=input_db_entry.last_modified,
            original_author=input_db_entry.original_author,
            last_modified_by=input_db_entry.last_modified_by,
            authors=input_db_entry.authors,
            edit_history=input_db_entry.edit_history,
            status=input_db_entry.status,
            origin=input_db_entry.origin,
            most_similar_similarity_score=input_db_entry.most_similar_similarity_score,
            most_similar_content_id=input_db_entry.most_similar_content_id,
            report_count=input_db_entry.report_count,
            is_archived=input_db_entry.is_archived,
            report_flagged=input_db_entry.report_flagged,
            rejection_reason=input_db_entry.rejection_reason,
            block_reason=input_db_entry.block_reason,
            visibility=input_db_entry.visibility,
        )

        # Use injected content repository for aggregated view
        await self._content_repository.upsert(input_db_entry.id, content_db_entry)

        await self._repository.upsert(input_db_entry.id, input_db_entry)

        return input_db_entry.id

    def refresh_topics(self) -> None:
        """
        Refresh the topics of the repository.
        Adding items to the repository will only infer the topic of the item from the existing nearest topics.
        This method will recompute the topics of the repository from the items in the repository.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Refresh topics"
        )
        return self._repository.refresh_topics()

    def get_topics(self) -> List[str]:
        """
        Get the topics of the repository.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting topics"
        )
        return self._repository.get_topics()

    def get_items_of_topic(self, topic: str, limit: int) -> List[TContentDbEntry]:
        """
        Get the items of the repository that match the given topic.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting items of topics"
        )
        return self._repository.get_items_of_topic(topic, limit)

    def get_categories(self) -> List[str]:
        """
        Get the categories of the repository.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting categories"
        )
        return self._repository.get_categories()

    def get_items_of_category(self, category: str, limit: int) -> List[TContentDbEntry]:
        """
        Get the items of the repository that match the given category.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting items of category"
        )
        return self._repository.get_items_of_category(category, limit)

    async def count(self) -> int:
        """
        Get the number of items in the repository.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting count"
        )
        return await self._repository.count()

    async def count_last_week(self) -> int:
        """
        Get the number of items in the repository that were created or updated in the last week.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting count last week"
        )
        return await self._repository.count_last_week()

    async def get_all(self, limit: int, offset: int) -> List[TContentDbEntry]:
        """
        Get all items in the repository.
        """
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting all items"
        )
        return await self._repository.get_all(limit, offset)

    async def get_by_status(
        self, status: ContentStatus, limit: int
    ) -> List[TContentDbEntry]:
        """Get items filtered by lifecycle status (used by the description worker)."""
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Getting items with status {status}"
        )
        return await self._repository.get_by_status(status, limit)

    async def update_status(
        self, item_id: uuid.UUID, new_status: ContentStatus
    ) -> None:
        """Partial-payload update: change only the status field without re-embedding."""
        logger.debug(
            f"BaseContentService ({self._repository_class.__name__}): Updating status of {item_id} to {new_status}"
        )
        await self._repository.update_status(item_id, new_status)
