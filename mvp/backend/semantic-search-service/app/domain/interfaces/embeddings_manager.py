"""
Interface for embeddings manager to enable dependency injection and testing.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple


class IEmbeddingsManager(ABC):
    """
    Interface for embeddings manager implementations.

    This interface defines the contract for embeddings managers, allowing
    for dependency injection and easier testing by decoupling from the
    singleton implementation.
    """

    @abstractmethod
    async def count(self, content_type: Optional[str] = None) -> int:
        """
        Count the number of items in the embeddings.

        Args:
            content_type: Optional content type to filter by

        Returns:
            int: Number of items matching the criteria
        """
        pass

    @abstractmethod
    async def search(
        self, query: str, content_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content.

        Args:
            query: Search query text
            content_type: Optional content type to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def upsert_batch(
        self, points: List[Tuple[str, Dict[str, Any], str]], content_type: str
    ) -> None:
        """
        Batch upsert points to the vector database.

        Args:
            points: List of (id, document, text) tuples
            content_type: Type of content being inserted
        """
        pass

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an item by its ID.

        Args:
            item_id: The ID of the item to retrieve

        Returns:
            The item data if found, None otherwise
        """
        pass

    @property
    @abstractmethod
    def repository_name(self) -> str:
        """
        Get the repository name.

        Returns:
            str: Name of the repository
        """
        pass
