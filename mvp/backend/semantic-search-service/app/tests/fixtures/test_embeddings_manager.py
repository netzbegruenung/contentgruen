"""
Test implementation of IEmbeddingsManager for unit testing.

This module provides a test-specific embeddings manager that simulates
the behavior of the real QdrantEmbeddingsManager without requiring
actual Qdrant connections or database connections.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock
import uuid
from datetime import datetime

from domain.interfaces.embeddings_manager import IEmbeddingsManager


class TestEmbeddingsManager(IEmbeddingsManager):
    """
    Test implementation of embeddings manager for unit testing.

    This class simulates the Qdrant behavior by filtering in-memory data
    and returning appropriate test results.
    """

    def __init__(self):
        """Initialize the test embeddings manager with in-memory storage."""
        self._data: Dict[str, Dict[str, Any]] = {}
        self._embeddings_mock = MagicMock()
        self._embeddings_mock.search = self._search_impl
        self._embeddings_mock.upsert = self._upsert_impl
        self._embeddings_mock.count = self._count_impl
        self._embeddings_mock.exists = lambda: bool(self._data)
        self._embeddings_mock.load = MagicMock()
        self._embeddings_mock.save = MagicMock()
        self._repository_name = "test_embeddings"

        # Setup async_client mock for Qdrant operations
        self._async_client = MagicMock()

        # Setup proper async methods
        async def mock_scroll(*args, **kwargs):
            """Mock scroll that returns data from our storage."""
            scroll_filter = kwargs.get("scroll_filter")
            limit = kwargs.get("limit", 100)
            offset = kwargs.get("offset")
            with_payload = kwargs.get("with_payload", True)

            # Filter data based on content_type if filter is provided
            filtered_data = []
            for item_id, item_data in self._data.items():
                # Check if we should include this item
                include = True
                if scroll_filter and hasattr(scroll_filter, "must"):
                    for condition in scroll_filter.must:
                        if (
                            hasattr(condition, "key")
                            and condition.key == "content_type"
                        ):
                            if hasattr(condition.match, "value"):
                                ct = condition.match.value
                                if (
                                    item_data.get("content_type", "").lower()
                                    != ct.lower()
                                ):
                                    include = False
                                    break

                if include:
                    # Create a point-like object
                    point = MagicMock()
                    point.id = item_id
                    point.payload = item_data if with_payload else None
                    filtered_data.append(point)

            # Return limited results (simple pagination)
            if len(filtered_data) <= limit:
                return (filtered_data, None)
            else:
                return (filtered_data[:limit], "next_offset")

        self._async_client.scroll = mock_scroll

        async def mock_count(*args, **kwargs):
            """Mock count that uses our test data."""
            count_filter = kwargs.get("count_filter")
            if count_filter and hasattr(count_filter, "must"):
                # Try to find content_type in filter
                for condition in count_filter.must:
                    if hasattr(condition, "key") and condition.key == "content_type":
                        if hasattr(condition.match, "value"):
                            ct = condition.match.value
                            count = sum(
                                1
                                for item in self._data.values()
                                if item.get("content_type", "").lower() == ct.lower()
                            )
                            return MagicMock(count=count)
            # Return total count if no filter
            return MagicMock(count=len(self._data))

        self._async_client.count = mock_count

    @property
    def embeddings(self):
        """Return the mock embeddings object."""
        return self._embeddings_mock

    @property
    def repository_name(self) -> str:
        """Return the repository name."""
        return self._repository_name

    async def count(self, content_type: Optional[str] = None) -> int:
        """
        Async count items in the test storage.

        Args:
            content_type: Optional content type to filter by

        Returns:
            Number of items matching the criteria
        """
        if content_type is None:
            return len(self._data)

        count = 0
        for item_id, item in self._data.items():
            if item.get("content_type", "").lower() == content_type.lower():
                count += 1
        return count

    def search(
        self, query: str, content_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        High-level search method (not typically used by repositories).

        Args:
            query: Search query text
            content_type: Optional content type filter
            limit: Maximum results

        Returns:
            List of search results
        """
        results = []
        for item_id, item in self._data.items():
            if (
                content_type
                and item.get("content_type", "").lower() != content_type.lower()
            ):
                continue
            # Simple text matching for testing
            if query.lower() in item.get("text", "").lower():
                result = item.copy()
                result["score"] = 0.95  # Mock score
                results.append(result)
                if len(results) >= limit:
                    break
        return results

    def upsert(self, items: List[tuple], content_type: str = None) -> None:
        """
        Insert or update items in test storage.

        Args:
            items: List of (id, data, text) tuples
            content_type: Content type being upserted
        """
        for item_id, data, text in items:
            if isinstance(data, dict):
                self._data[str(item_id)] = data
            else:
                # Convert other formats to dict
                self._data[str(item_id)] = {
                    "id": str(item_id),
                    "text": text,
                    "content_type": content_type or "unknown",
                    **getattr(data, "__dict__", {}),
                }

    def _search_impl(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Implement search by filtering in-memory data.

        This method simulates Qdrant's search interface by filtering test data
        and returning appropriate results.

        Args:
            sql_query: SQL query string

        Returns:
            List of results as dictionaries
        """
        # Parse limit
        limit_match = re.search(r"limit\s+(\d+)", sql_query, re.IGNORECASE)
        limit = int(limit_match.group(1)) if limit_match else 10

        # Parse offset
        offset_match = re.search(r"offset\s+(\d+)", sql_query, re.IGNORECASE)
        offset = int(offset_match.group(1)) if offset_match else 0

        # Check if it's a get by ID query
        id_match = re.search(r"id\s*=\s*'([^']+)'", sql_query)
        if id_match:
            item_id = id_match.group(1)
            if item_id in self._data:
                return [self._data[item_id]]
            return []

        # Parse content type filter
        content_type_match = re.search(
            r"content_type\s*=\s*'([^']+)'", sql_query, re.IGNORECASE
        )
        content_type = content_type_match.group(1) if content_type_match else None

        # Parse search query
        similar_match = re.search(
            r"similar\s*\(\s*'([^']+)'\s*\)", sql_query, re.IGNORECASE
        )
        search_query = similar_match.group(1) if similar_match else None

        # Check if this is a similar() query (semantic search)
        is_similar_query = similar_match is not None

        # Filter and return results
        results = []
        for item_id, item in self._data.items():
            # Apply content type filter
            if (
                content_type
                and item.get("content_type", "").lower() != content_type.lower()
            ):
                continue

            # Apply search filter
            if search_query:
                # Unescape SQL strings (double single quotes)
                search_query = search_query.replace("''", "'")
                # For semantic search, an empty query or special characters don't match
                if not search_query.strip() or search_query.strip() in [
                    "';",
                    "'; DROP TABLE users; --",
                ]:
                    continue  # No semantic match for SQL injection attempts
                if search_query.lower() not in item.get("text", "").lower():
                    continue

            # Add score for search results
            result = item.copy()
            if search_query:
                result["score"] = 0.95
            else:
                result["score"] = 1.0

            results.append(result)

        # Apply offset and limit
        return results[offset : offset + limit]

    def _upsert_impl(self, items: List[tuple]) -> None:
        """
        Implement upsert for the mock.

        Args:
            items: List of (id, data) tuples
        """
        for item_id, data in items:
            if isinstance(data, dict):
                self._data[str(item_id)] = data.copy()
            else:
                # Handle objects
                self._data[str(item_id)] = {
                    "id": str(item_id),
                    **getattr(data, "__dict__", {}),
                }

    def _count_impl(self) -> int:
        """Return total count of items."""
        return len(self._data)

    def add_test_data(self, content_type: str, items: List[Dict[str, Any]]) -> None:
        """
        Helper method to add test data directly.

        Args:
            content_type: Type of content being added
            items: List of item dictionaries
        """
        for item in items:
            item_id = item.get("id", str(uuid.uuid4()))
            self._data[str(item_id)] = {
                **item,
                "id": str(item_id),
                "content_type": content_type.lower(),
                "created": item.get("created", datetime.now().isoformat()),
                "last_modified": item.get("last_modified", datetime.now().isoformat()),
            }

    def clear(self) -> None:
        """Clear all test data."""
        self._data.clear()

    def get_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored data for assertions."""
        return self._data.copy()

    # Additional methods for Qdrant compatibility
    async def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Async search method for Qdrant compatibility with Range filter support.

        Args:
            query: Search query text
            content_type: Optional content type filter
            limit: Maximum results
            filter_dict: Additional filters including Range filters

        Returns:
            List of search results
        """
        results = []
        for item_id, item in self._data.items():
            # Apply content_type filter
            if (
                content_type
                and item.get("content_type", "").lower() != content_type.lower()
            ):
                continue

            # Apply filter_dict filters (including Range filters)
            if filter_dict and "must" in filter_dict:
                include_item = True
                for condition in filter_dict["must"]:
                    # Check if it's a Range filter
                    if hasattr(condition, "range") and hasattr(condition, "key"):
                        field_value = item.get(condition.key, 0)
                        range_filter = condition.range

                        # Apply gte (greater than or equal)
                        if (
                            hasattr(range_filter, "gte")
                            and range_filter.gte is not None
                        ):
                            if field_value < range_filter.gte:
                                include_item = False
                                break

                        # Apply gt (greater than)
                        if hasattr(range_filter, "gt") and range_filter.gt is not None:
                            if field_value <= range_filter.gt:
                                include_item = False
                                break

                        # Apply lte (less than or equal)
                        if (
                            hasattr(range_filter, "lte")
                            and range_filter.lte is not None
                        ):
                            if field_value > range_filter.lte:
                                include_item = False
                                break

                        # Apply lt (less than)
                        if hasattr(range_filter, "lt") and range_filter.lt is not None:
                            if field_value >= range_filter.lt:
                                include_item = False
                                break

                if not include_item:
                    continue

            # Simple text matching for testing
            if query.lower() in item.get("text", "").lower():
                result = item.copy()
                result["score"] = 0.95  # Mock score
                results.append(result)
                if len(results) >= limit:
                    break
        return results

    async def upsert_batch(self, points: List[tuple], content_type: str) -> None:
        """
        Async batch upsert for Qdrant compatibility.

        Args:
            points: List of (id, data, text) tuples
            content_type: Content type being upserted
        """
        for item_id, data, text in points:
            if isinstance(data, dict):
                data["content_type"] = content_type
                self._data[str(item_id)] = data
            else:
                # Convert other formats to dict
                self._data[str(item_id)] = {
                    "id": str(item_id),
                    "text": text,
                    "content_type": content_type,
                    **getattr(data, "__dict__", {}),
                }

    @property
    def is_started(self) -> bool:
        """Check if manager is started."""
        return True

    @property
    def client(self):
        """Return mock Qdrant client."""
        return self._embeddings_mock

    @property
    def async_client(self):
        """Return mock async Qdrant client."""
        return self._async_client

    @property
    def collection_name(self) -> str:
        """Return collection name."""
        return "test_collection"

    async def get_by_id(self, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a point by its ID."""
        return self._data.get(point_id)

    async def delete_by_id(self, point_id: str) -> bool:
        """Delete a point by its ID."""
        if point_id in self._data:
            del self._data[point_id]
            return True
        return False

    async def health_check(self) -> Dict[str, Any]:
        """Health check method."""
        return {
            "status": "healthy",
            "collection": "test_collection",
            "total_points": len(self._data),
        }

    def encode_text(self, text: str) -> List[float]:
        """Mock encode text."""
        return [0.1] * 768  # Return 768-dimensional mock vector

    def encode_query(self, query: str) -> List[float]:
        """Mock encode query."""
        return [0.1] * 768  # Return 768-dimensional mock vector
