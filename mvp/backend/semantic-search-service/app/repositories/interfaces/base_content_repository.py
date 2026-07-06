from abc import ABC, abstractmethod
from typing import List, TypeVar, Generic, Optional
import uuid

from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from domain.models.content_status import ContentStatus
from utils.data_utils import DataSource

TContentDbEntry = TypeVar("TContentDbEntry", bound=BaseContentDbEntry)
TContentSearchResult = TypeVar("TContentSearchResult", bound=BaseContentSearchResult)


class IBaseContentRepository(ABC, Generic[TContentDbEntry, TContentSearchResult]):
    """
    Abstract base interface for all content repositories.

    This interface defines the common operations that all content repositories must support,
    regardless of the underlying persistence technology.
    """

    @abstractmethod
    async def initialize_repository(self) -> DataSource:
        """
        Initialize the repository with initial data if needed.

        Returns:
            DataSource: Indicates whether data was loaded from storage or JSON files
        """
        pass

    @abstractmethod
    async def search(
        self, query_text: str, limit: int = 10
    ) -> List[TContentSearchResult]:
        """
        Search for content similar to the provided query text.

        Args:
            query_text: The text to search for
            limit: Maximum number of results to return

        Returns:
            List of search results with similarity scores
        """
        pass

    @abstractmethod
    async def get(self, item_id: uuid.UUID) -> TContentDbEntry:
        """
        Retrieve a specific content item by its ID.

        Args:
            item_id: Unique identifier of the content item

        Returns:
            The content item

        Raises:
            ValueError: If item not found
        """
        pass

    @abstractmethod
    async def upsert(self, item_id: uuid.UUID, content: TContentDbEntry) -> uuid.UUID:
        """
        Insert or update a content item.

        Args:
            item_id: Unique identifier for the content
            content: The content item to store

        Returns:
            The UUID of the stored content
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        Get the total number of items in the repository.

        Returns:
            Total count of items
        """
        pass

    @abstractmethod
    async def get_all(self, limit: int, offset: int) -> List[TContentDbEntry]:
        """
        Retrieve all items with pagination.

        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of content items
        """
        pass

    @abstractmethod
    async def get_by_author(
        self, user_id: str, limit: int, offset: int
    ) -> List[TContentDbEntry]:
        """
        Retrieve items by a specific author with pagination.

        Args:
            user_id: The author's user ID
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of content items by the author
        """
        pass

    @abstractmethod
    async def get_count_by_author(self, user_id: str) -> int:
        """
        Get the count of items by a specific author.

        Args:
            user_id: The author's user ID

        Returns:
            Count of items by the author
        """
        pass

    # Topic and category methods (optional - can be implemented by repositories that support them)

    def get_topics(self) -> List[str]:
        """
        Get available topics. Default implementation returns empty list.
        Override in repositories that support topic functionality.

        Returns:
            List of available topics
        """
        return []

    def get_items_of_topic(self, topic: str, limit: int) -> List[TContentDbEntry]:
        """
        Get items by topic. Default implementation returns empty list.
        Override in repositories that support topic functionality.

        Args:
            topic: The topic to filter by
            limit: Maximum number of items to return

        Returns:
            List of content items for the topic
        """
        return []

    def get_categories(self) -> List[str]:
        """
        Get available categories. Default implementation returns empty list.
        Override in repositories that support category functionality.

        Returns:
            List of available categories
        """
        return []

    def get_items_of_category(self, category: str, limit: int) -> List[TContentDbEntry]:
        """
        Get items by category. Default implementation returns empty list.
        Override in repositories that support category functionality.

        Args:
            category: The category to filter by
            limit: Maximum number of items to return

        Returns:
            List of content items for the category
        """
        return []

    def refresh_topics(self) -> None:
        """
        Refresh topic assignments. Default implementation does nothing.
        Override in repositories that support topic functionality.
        """
        pass

    @abstractmethod
    async def has_content(self) -> bool:
        """
        Check if the repository contains any content.

        Returns:
            True if the repository has content, False otherwise
        """
        pass

    @abstractmethod
    def initialize_with_initial_data(self) -> None:
        """
        Initialize the repository with initial data from JSON files.
        This method is called when the repository is empty and needs to be populated.
        """
        pass

    async def get_by_status(
        self, status: ContentStatus, limit: int
    ) -> List[TContentDbEntry]:
        """
        Get items filtered by lifecycle status.
        Default implementation returns empty list.
        Override in repositories that support status-based queries.
        """
        return []

    async def update_status(
        self, item_id: uuid.UUID, new_status: ContentStatus
    ) -> None:
        """
        Partial-payload update: change only the status field without re-embedding.
        Default implementation is a no-op.
        Override in repositories that support status updates.
        """
        pass

    async def count_last_week(self) -> int:
        """
        Get the count of items created or modified in the last week.
        Default implementation returns 0.
        Override in repositories that support date-based queries.

        Returns:
            Count of recent items
        """
        return 0

    async def get_recent(self, limit: int = 10) -> List[TContentDbEntry]:
        """
        Get the most recently created content items.
        Default implementation returns empty list.
        Override in repositories that support date-based queries.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of content items ordered by creation date (newest first)
        """
        return []
