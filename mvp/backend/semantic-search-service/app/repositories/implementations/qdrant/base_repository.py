from abc import abstractmethod
import datetime
import json
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
import os
import uuid
import logging
import asyncio

from core.config import Settings
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from domain.models.model_utils import ModelInformationExtractor
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from utils.data_utils import DataSource

logger = logging.getLogger(__name__)

TContentDbEntry = TypeVar("TContentDbEntry", bound=BaseContentDbEntry)
TContentSearchResult = TypeVar("TContentSearchResult", bound=BaseContentSearchResult)


def _search_query_origin_conditions() -> list:
    """
    must_not-Bedingung, die Statements aus Suchanfragen ausschliesst.

    Gedacht fuer alles, was Inhalte einer Person zuordnet (get_by_author,
    get_count_by_author). Eine Suchanfrage faellt automatisch an und hat keinen
    Autor - sie ist kein Beitrag und darf in "Meine Beitraege" nicht auftauchen.
    Der Filter greift zusaetzlich zum Systemautor aus SEARCH_QUERY_AUTHOR, damit
    auch Altbestand aussen vor bleibt, an dem noch eine Person haengt.
    """
    from qdrant_client.models import FieldCondition, MatchValue

    return [
        FieldCondition(
            key="origin", match=MatchValue(value=ContentOrigin.SEARCH_QUERY.value)
        )
    ]


class QdrantBaseRepository(
    IBaseContentRepository[TContentDbEntry, TContentSearchResult]
):
    """
    Base repository implementation for Qdrant vector database.

    This class provides common functionality for all content repositories using Qdrant,
    with content types logically separated using the content_type field.
    """

    def __init__(
        self,
        index_name: str,
        content_type: Optional[str],
        settings: Settings,
        content_db_entry_model_class: Type[TContentDbEntry],
        content_search_result_model_class: Type[TContentSearchResult],
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        self.repository_name = index_name
        self.content_type = content_type  # None means no filtering (aggregated view)
        self.initial_data_path = os.path.join(
            settings.index_initial_data_path, index_name
        )
        self.content_db_entry_model_class = content_db_entry_model_class
        self.content_search_result_model_class = content_search_result_model_class
        self.initial_data_author = settings.initial_data_author

        self._embedding_fields, self._embedding_fields_str = (
            ModelInformationExtractor.get_all_fields(content_db_entry_model_class)
        )

        logger.info(
            f"Configured {self.repository_name} (content_type: {self.content_type}) "
            f"with fields: {self._embedding_fields_str}"
        )

        # Use injected embeddings manager or get default singleton
        self._shared_manager = embeddings_manager or get_embeddings_manager()

    # Public interface methods (implementing IBaseContentRepository)

    async def initialize_repository(self) -> DataSource:
        """
        Initialize the repository with initial data if needed.

        Returns:
            DataSource: Indicates whether data was loaded from storage or JSON files
        """
        logger.info(f"=== Initializing {self.__class__.__name__} ===")

        if await self.has_content():
            logger.info(
                f"Initialized {self.__class__.__name__} - found existing content"
            )
            return DataSource.STORAGE
        else:
            logger.info(f"Executing initial data load from JSON files")
            self.initialize_with_initial_data()
            return DataSource.JSON

    async def search(self, query_text: str, limit: int) -> List[TContentSearchResult]:
        """Async implementation of search."""
        try:
            from qdrant_client.models import FieldCondition, MatchValue

            # Exclude lifecycle statuses that must not surface in search results.
            # Using must_not + MatchValue (instead of MatchExcept on must) so that legacy
            # points without a status field are left unaffected (MatchExcept on must would
            # drop fieldless points because the must clause is not satisfied).
            # PENDING_REVIEW is excluded because images in that status await human review.
            filter_dict = {
                "must_not": [
                    FieldCondition(
                        key="status",
                        match=MatchValue(value=ContentStatus.PENDING_DESCRIPTION.value),
                    ),
                    FieldCondition(
                        key="status",
                        match=MatchValue(value=ContentStatus.DESCRIPTION_FAILED.value),
                    ),
                    FieldCondition(
                        key="status",
                        match=MatchValue(value=ContentStatus.PENDING_REVIEW.value),
                    ),
                ]
            }

            # Perform search with optional content_type filter
            search_results = await self._shared_manager.search(
                query=query_text,
                content_type=self.content_type,
                limit=limit,
                filter_dict=filter_dict,
            )

            content_desc = (
                f"all content types" if self.content_type is None else self.content_type
            )
            logger.info(
                f"Search results for query '{query_text}' in {content_desc}: "
                f"found {len(search_results)} results"
            )

            # Convert to result models
            return [
                self.content_search_result_model_class.model_validate(res)
                for res in search_results
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise

    async def get(self, item_id: uuid.UUID) -> TContentDbEntry:
        """Async implementation of get."""
        try:
            result = await self._shared_manager.get_by_id(str(item_id))

            if result is None:
                content_desc = (
                    f"all content types"
                    if self.content_type is None
                    else f"content_type: {self.content_type}"
                )
                raise ValueError(
                    f"Entry with id {item_id} not found in {self.repository_name} ({content_desc})"
                )

            # Verify content_type if filtering is enabled
            if self.content_type and result.get("content_type") != self.content_type:
                raise ValueError(
                    f"Entry with id {item_id} has wrong content_type: {result.get('content_type')}"
                )

            logger.info(f"Found entry with id {item_id} in {self.repository_name}")
            return self.content_db_entry_model_class.model_validate(result)

        except Exception as e:
            logger.error(f"Failed to get item by ID: {e}", exc_info=True)
            raise

    async def get_by_id(self, item_id: uuid.UUID) -> TContentDbEntry:
        """
        Retrieve a specific content item by its ID.
        This is an alias for get() method for consistency with test expectations.
        """
        return await self.get(item_id)

    async def upsert(
        self, item_id: uuid.UUID, item_input: TContentDbEntry
    ) -> uuid.UUID:
        """Async implementation of upsert."""
        try:
            data_dict = json.loads(item_input.model_dump_json())

            if "text" not in data_dict:
                raise ValueError(
                    f"Item with id {item_id} does not contain a 'text' field"
                )

            # For aggregated repositories, use the content_type from the data itself
            if self.content_type is None:
                if "content_type" not in data_dict:
                    raise ValueError(
                        f"Aggregated index requires content_type in data, but not found for id {item_id}"
                    )
                upsert_content_type = data_dict["content_type"]
            else:
                upsert_content_type = self.content_type
                data_dict["content_type"] = self.content_type

            logger.info(
                f"QdrantBaseRepository ({self.__class__.__name__}): Upserting item with id {item_id} "
                f"into {self.repository_name} (using content_type: {upsert_content_type})"
            )

            # Extract text for embedding; coerce None to "" for captionless images
            # (Phase B path). The "" vector is low-signal but allows the point to exist
            # so get_by_status/update_status can operate on it; status filter in search()
            # prevents it from surfacing in results until a real caption is stored.
            text = data_dict.get("text") or ""

            # Upsert to Qdrant
            await self._shared_manager.upsert_batch(
                points=[(str(item_id), data_dict, text)],
                content_type=upsert_content_type,
            )

            return item_id

        except Exception as e:
            logger.error(f"Failed to upsert item: {e}", exc_info=True)
            raise

    async def count(self) -> int:
        """
        Get the total count of items in the repository.
        """
        return await self._shared_manager.count(self.content_type)

    async def get_all(self, limit: int, offset: int) -> List[TContentDbEntry]:
        """Async implementation of get_all."""
        try:
            # Build filter for content_type if needed
            filter_dict = (
                {"content_type": self.content_type} if self.content_type else None
            )

            # Use search with empty query to get all items
            # This is a workaround since Qdrant doesn't have direct pagination like SQL
            all_results = []
            batch_size = 100
            current_offset = None

            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Build filter
            search_filter = None
            if self.content_type:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="content_type",
                            match=MatchValue(value=self.content_type),
                        )
                    ]
                )

            # Scroll through results
            points_collected = 0
            points_to_skip = offset

            while points_collected < limit:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=min(batch_size, limit - points_collected + points_to_skip),
                    offset=current_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    if points_to_skip > 0:
                        points_to_skip -= 1
                        continue

                    if points_collected >= limit:
                        break

                    payload = point.payload or {}
                    payload["id"] = str(point.id)
                    all_results.append(
                        self.content_db_entry_model_class.model_validate(payload)
                    )
                    points_collected += 1

                current_offset = result[1]
                if current_offset is None or points_collected >= limit:
                    break

            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(
                f"Retrieved {len(all_results)} items from {self.repository_name} ({content_desc})"
            )

            return all_results

        except Exception as e:
            logger.error(f"Failed to get all items: {e}", exc_info=True)
            raise

    async def get_by_author(
        self, user_id: str, limit: int, offset: int
    ) -> List[TContentDbEntry]:
        """Async implementation of get_by_author."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Build filter conditions
            must_conditions = [
                FieldCondition(key="original_author", match=MatchValue(value=user_id))
            ]

            if self.content_type:
                must_conditions.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=self.content_type)
                    )
                )

            search_filter = Filter(
                must=must_conditions, must_not=_search_query_origin_conditions()
            )

            # Scroll through results with pagination
            all_results = []
            current_offset = None
            points_to_skip = offset
            points_collected = 0

            while points_collected < limit:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=min(100, limit - points_collected + points_to_skip),
                    offset=current_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    if points_to_skip > 0:
                        points_to_skip -= 1
                        continue

                    if points_collected >= limit:
                        break

                    payload = point.payload or {}
                    payload["id"] = str(point.id)
                    all_results.append(
                        self.content_db_entry_model_class.model_validate(payload)
                    )
                    points_collected += 1

                current_offset = result[1]
                if current_offset is None or points_collected >= limit:
                    break

            content_desc = (
                f"all content types" if self.content_type is None else self.content_type
            )
            logger.info(
                f"Search results for user '{user_id}' in {content_desc}: {len(all_results)} items"
            )

            return all_results

        except Exception as e:
            logger.error(f"Failed to get items by author: {e}", exc_info=True)
            raise

    async def get_count_by_author(self, user_id: str) -> int:
        """Async implementation of get_count_by_author."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Build filter conditions
            must_conditions = [
                FieldCondition(key="original_author", match=MatchValue(value=user_id))
            ]

            if self.content_type:
                must_conditions.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=self.content_type)
                    )
                )

            search_filter = Filter(
                must=must_conditions, must_not=_search_query_origin_conditions()
            )

            # Count with filter
            result = await self._shared_manager.async_client.count(
                collection_name=self._shared_manager.collection_name,
                count_filter=search_filter,
            )

            return result.count

        except Exception as e:
            logger.error(f"Failed to count items by author: {e}", exc_info=True)
            return 0

    async def has_content(self) -> bool:
        """
        Check if there's any content for this content_type in the collection.
        If content_type is None, checks for any content across all types.

        Returns:
            True if content exists, False otherwise.
        """
        try:
            count = await self.count()
            has_content = count > 0
            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(f"{self.repository_name} ({content_desc}) has {count} items")
            return has_content
        except Exception as e:
            logger.error(f"Error checking content for {self.repository_name}: {e}")
            return False

    async def get_recent(self, limit: int = 10) -> List[TContentDbEntry]:
        """Async implementation of get_recent. For MVP, fetches a reasonable batch and sorts."""
        try:
            from qdrant_client.models import (
                Filter,
                FieldCondition,
                MatchValue,
            )

            # Build filter for content_type if needed
            search_filter = None
            if self.content_type:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="content_type",
                            match=MatchValue(value=self.content_type),
                        )
                    ]
                )

            # For MVP: Fetch a reasonable batch (10x requested limit) and sort in memory
            # This is acceptable for small datasets. For production with large datasets,
            # consider adding a 'created' payload index with ordering support.
            batch_size = min(limit * 10, 1000)  # Cap at 1000 to avoid memory issues
            all_results = []
            current_offset = None
            fetched = 0

            while fetched < batch_size:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=min(100, batch_size - fetched),
                    offset=current_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    payload = point.payload or {}
                    payload["id"] = str(point.id)
                    all_results.append(payload)
                    fetched += 1

                current_offset = result[1]
                if current_offset is None:
                    break

            # Sort by created date (newest first)
            all_results.sort(key=lambda x: x.get("created", ""), reverse=True)

            # Take only the requested limit
            recent_results = all_results[:limit]

            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(
                f"Recent content results for {self.repository_name} ({content_desc}): "
                f"found {len(recent_results)} items (fetched {len(all_results)} to sort)"
            )

            return [
                self.content_db_entry_model_class.model_validate(res)
                for res in recent_results
            ]

        except Exception as e:
            logger.error(f"Failed to get recent items: {e}", exc_info=True)
            return []

    async def count_last_week(self) -> int:
        """Async implementation of count_last_week."""
        try:
            from datetime import datetime, timedelta
            from qdrant_client.models import (
                Filter,
                FieldCondition,
                MatchValue,
                DateRange,
            )

            # Calculate date one week ago
            one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            # Build filter conditions
            must_conditions = []

            if self.content_type:
                must_conditions.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=self.content_type)
                    )
                )

            # Note: Qdrant doesn't support OR conditions directly in the same way,
            # and date range filtering requires proper field indexing
            # For now, we'll count items created in the last week
            # This is a simplified implementation

            # Get all items and filter in memory (acceptable for small datasets)
            search_filter = Filter(must=must_conditions) if must_conditions else None

            count = 0
            current_offset = None

            while True:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=100,
                    offset=current_offset,
                    with_payload=["created", "last_modified"],
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    payload = point.payload or {}
                    created = payload.get("created", "")
                    last_modified = payload.get("last_modified", "")

                    # Check if created or modified in the last week
                    if created >= one_week_ago or last_modified >= one_week_ago:
                        count += 1

                current_offset = result[1]
                if current_offset is None:
                    break

            return count

        except Exception as e:
            logger.error(f"Error counting items from last week: {e}", exc_info=True)
            return 0

    async def get_by_status(
        self, status: ContentStatus, limit: int
    ) -> List[TContentDbEntry]:
        """Payload-filtered scroll for items in the given lifecycle status."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            must = [FieldCondition(key="status", match=MatchValue(value=status.value))]
            if self.content_type:
                must.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=self.content_type)
                    )
                )

            result = await self._shared_manager.async_client.scroll(
                collection_name=self._shared_manager.collection_name,
                scroll_filter=Filter(must=must),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            return [
                self.content_db_entry_model_class.model_validate(
                    {**p.payload, "id": str(p.id)}
                )
                for p in result[0]
            ]
        except Exception as e:
            logger.error(f"Failed to get items by status {status}: {e}", exc_info=True)
            raise

    async def update_status(
        self, item_id: uuid.UUID, new_status: ContentStatus
    ) -> None:
        """Partial-payload update: change only the status field without re-embedding."""
        try:
            await self._shared_manager.async_client.set_payload(
                collection_name=self._shared_manager.collection_name,
                payload={"status": new_status.value},
                points=[str(item_id)],
            )
            logger.debug(f"Updated status of {item_id} to {new_status.value}")
        except Exception as e:
            logger.error(
                f"Failed to update status of {item_id} to {new_status}: {e}",
                exc_info=True,
            )
            raise

    @abstractmethod
    def initialize_with_initial_data(self):
        """
        Initialize this repository with initial data from JSON files.
        This will only load into this repository, and not have side effects on other repositories!

        Derived classes should override this method to implement specific data loading logic.
        """
        pass

    # Topic and category methods are not implemented for Qdrant
    # These may be added in future versions if needed
