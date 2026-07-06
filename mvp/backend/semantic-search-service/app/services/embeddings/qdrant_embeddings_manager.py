from typing import Optional, Dict, Any, List, Tuple, Literal
import threading
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    HnswConfigDiff,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    UpdateStatus,
    CollectionInfo,
    ScrollRequest,
    OrderBy,
    Direction,
    FilterSelector,
)
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI

from core.config import Settings
from core.logging import get_logger
from domain.interfaces.embeddings_manager import IEmbeddingsManager

logger = get_logger(__name__)


class QdrantEmbeddingsManager(IEmbeddingsManager):
    """
    Singleton manager for Qdrant vector database with multilingual E5 embeddings.

    This manager ensures only one Qdrant client instance exists across all content types,
    using a single collection with content_type field for logical separation.
    """

    _instance: Optional["QdrantEmbeddingsManager"] = None
    _lock = threading.Lock()

    def __new__(cls, settings: Optional[Settings] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._init_instance(settings)
        return cls._instance

    def __init__(self, settings: Optional[Settings] = None):
        # __init__ is now a no-op since initialization happens in __new__
        pass

    def _init_instance(self, settings: Optional[Settings] = None):
        """Initialize the singleton instance. Called only once within the lock."""
        if self._initialized:
            return

        if settings is None:
            raise ValueError("Settings must be provided for first initialization")

        self.settings = settings
        self._client: Optional[QdrantClient] = None
        self._async_client: Optional[AsyncQdrantClient] = None
        self._model: Optional[SentenceTransformer] = None
        self._is_started = False
        self._initialized = True
        self.collection_name = (
            settings.qdrant_collection or "content_collection"
        ).strip()

        logger.info(
            f"🔧 QdrantEmbeddingsManager initialized for collection: {self.collection_name}"
        )

    async def start(self) -> None:
        """Start the Qdrant client and load the embedding model."""
        if self._is_started:
            logger.debug("QdrantEmbeddingsManager already started")
            return

        try:
            logger.info("🚀 Starting QdrantEmbeddingsManager...")

            # Initialize Qdrant client
            qdrant_url = self.settings.qdrant_url or "http://localhost:6333"
            logger.info(f"📥 Connecting to Qdrant at {qdrant_url}...")

            self._client = QdrantClient(url=qdrant_url, timeout=30)
            self._async_client = AsyncQdrantClient(url=qdrant_url, timeout=30)

            # Load E5 multilingual model
            logger.info(
                "📥 Loading multilingual E5 model (this may take a while on first startup)..."
            )
            self._model = SentenceTransformer("intfloat/multilingual-e5-base")

            # Create collection if it doesn't exist
            await self._ensure_collection()

            self._is_started = True
            logger.info(
                f"✅ QdrantEmbeddingsManager started successfully. Collection: {self.collection_name}"
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to start QdrantEmbeddingsManager: {e}", exc_info=True
            )
            raise

    async def _ensure_collection(self) -> None:
        """Ensure the Qdrant collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = await self._async_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"📦 Creating Qdrant collection: {self.collection_name}")

                # Create collection with optimized settings for <10k documents
                await self._async_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # E5-base has 768 dimensions
                        distance=Distance.COSINE,
                        hnsw_config=HnswConfigDiff(
                            m=8, ef_construct=100  # Optimal for <10k documents
                        ),
                    ),
                    on_disk_payload=False,  # In-memory for better performance
                )

                # Create payload index for content_type to speed up filtering
                try:
                    await self._async_client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="content_type",
                        field_schema="keyword",
                    )
                    logger.info("✅ Created payload index for content_type field")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not create payload index for content_type: {e}"
                    )
                    logger.info(
                        "Continuing without index - filtering will still work but may be slower"
                    )

                # Create payload index for status to speed up get_by_status scrolls
                try:
                    await self._async_client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="status",
                        field_schema="keyword",
                    )
                    logger.info("✅ Created payload index for status field")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not create payload index for status: {e}"
                    )

                logger.info(
                    f"✅ Collection {self.collection_name} created successfully"
                )
            else:
                # Get collection info for logging
                info = await self._async_client.get_collection(self.collection_name)
                logger.info(
                    f"✅ Using existing collection {self.collection_name} with {info.points_count} points"
                )

        except Exception as e:
            logger.error(f"❌ Failed to ensure collection: {e}", exc_info=True)
            raise

    async def shutdown(self) -> None:
        """Shutdown the Qdrant clients."""
        if not self._is_started:
            logger.debug("QdrantEmbeddingsManager not started, nothing to shutdown")
            return

        try:
            logger.info("🛑 Shutting down QdrantEmbeddingsManager...")
            if self._client:
                self._client.close()
                self._client = None
            if self._async_client:
                await self._async_client.close()
                self._async_client = None
            self._model = None
            self._is_started = False
            logger.info("✅ QdrantEmbeddingsManager shutdown complete")
        except Exception as e:
            logger.error(
                f"❌ Error during QdrantEmbeddingsManager shutdown: {e}", exc_info=True
            )

    @property
    def client(self) -> QdrantClient:
        """Get the synchronous Qdrant client."""
        if not self._is_started or not self._client:
            raise RuntimeError(
                "QdrantEmbeddingsManager not started. Call start() first."
            )
        return self._client

    @property
    def async_client(self) -> AsyncQdrantClient:
        """Get the asynchronous Qdrant client."""
        if not self._is_started or not self._async_client:
            raise RuntimeError(
                "QdrantEmbeddingsManager not started. Call start() first."
            )
        return self._async_client

    @property
    def model(self) -> SentenceTransformer:
        """Get the embedding model."""
        if not self._is_started or not self._model:
            raise RuntimeError(
                "QdrantEmbeddingsManager not started. Call start() first."
            )
        return self._model

    @property
    def is_started(self) -> bool:
        """Check if the manager is started."""
        return self._is_started

    @property
    def repository_name(self) -> str:
        """Get the repository name."""
        return "qdrant_embeddings"

    @property
    def embeddings(self):
        """
        Get the embeddings instance (compatibility with IEmbeddingsManager interface).
        For Qdrant, this returns self as we handle embeddings internally.
        """
        return self

    def encode_text(
        self, text: str, content_type: Literal["statement", "passage"] = "passage"
    ) -> List[float]:
        """
        Encode text to embeddings using E5 model.

        Args:
            text: The text to encode
            content_type:
                - "statement" for query-like short texts (statements, questions, claims)
                  Uses "query: " prefix for symmetric statement-to-statement matching
                - "passage" for document content (commentaries, generic text, articles)
                  Uses "passage: " prefix for asymmetric query-to-document matching

        Returns:
            Embedding vector as list of floats

        Note: E5 model requires different prefixes for optimal performance:
        - Use "query: " for statements/queries being matched to each other
        - Use "passage: " for longer informational content
        """
        if not self._model:
            raise RuntimeError("Model not loaded. Call start() first.")

        # Select appropriate prefix based on content type
        prefix = "query" if content_type == "statement" else "passage"
        prefixed_text = f"{prefix}: {text}"

        embedding = self._model.encode(prefixed_text, normalize_embeddings=True)
        return embedding.tolist()

    def encode_query(self, query: str) -> List[float]:
        """
        Encode query text for searching.

        This is a convenience wrapper around encode_text() with content_type="statement".
        Use this for user search queries.

        Returns:
            Embedding vector with "query: " prefix for optimal search performance
        """
        return self.encode_text(query, content_type="statement")

    async def upsert_batch(
        self, points: List[Tuple[str, Dict[str, Any], str]], content_type: str
    ) -> None:
        """
        Batch upsert points to Qdrant.

        Args:
            points: List of (id, document, text) tuples
            content_type: Type of content being inserted (statement, commentary, generic_text, etc.)
        """
        if not self._is_started:
            raise RuntimeError("QdrantEmbeddingsManager not started.")

        try:
            qdrant_points = []
            for point_id, document, text in points:
                # Determine encoding type based on content type
                # Statements use "query: " prefix, all other content uses "passage: " prefix
                encoding_type = (
                    "statement" if content_type == "statement" else "passage"
                )

                # Generate embedding with appropriate prefix
                embedding = self.encode_text(text, content_type=encoding_type)

                # Add content_type to document
                document["content_type"] = content_type

                # Ensure datetime fields are strings
                for date_field in ["created", "last_modified"]:
                    if date_field in document and isinstance(
                        document[date_field], datetime
                    ):
                        document[date_field] = document[date_field].isoformat()

                # Create point
                point = PointStruct(id=point_id, vector=embedding, payload=document)
                qdrant_points.append(point)

            # Batch upsert
            if qdrant_points:
                result = await self._async_client.upsert(
                    collection_name=self.collection_name, points=qdrant_points
                )

                if result.status == UpdateStatus.COMPLETED:
                    logger.info(
                        f"✅ Successfully upserted {len(qdrant_points)} points of type {content_type}"
                    )
                else:
                    logger.warning(f"⚠️ Upsert completed with status: {result.status}")

        except (UnexpectedResponse, ResponseHandlingException) as e:
            logger.error(
                f"❌ Qdrant client error during upsert batch: {e}", exc_info=True
            )
            raise RuntimeError(f"Vector database upsert failed: {e}") from e
        except Exception as e:
            logger.error(f"❌ Unexpected error during upsert batch: {e}", exc_info=True)
            raise

    async def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Qdrant.

        Args:
            query: Search query text
            content_type: Optional content type filter
            limit: Maximum results to return
            filter_dict: Additional filters (can include 'must' key with list of FieldConditions)

        Returns:
            List of search results with scores
        """
        if not self._is_started:
            raise RuntimeError("QdrantEmbeddingsManager not started.")

        try:
            # Encode query
            query_vector = self.encode_query(query)

            # Build filter
            must_conditions = []
            if content_type:
                must_conditions.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=content_type)
                    )
                )

            must_not_conditions = []
            if filter_dict:
                # Support structured filters with 'must' / 'must_not' keys.
                if "must" in filter_dict or "must_not" in filter_dict:
                    must_conditions.extend(filter_dict.get("must", []))
                    must_not_conditions.extend(filter_dict.get("must_not", []))
                else:
                    # Legacy support: simple key-value match filters
                    for key, value in filter_dict.items():
                        must_conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )

            search_filter = (
                Filter(
                    must=must_conditions or None,
                    must_not=must_not_conditions or None,
                )
                if (must_conditions or must_not_conditions)
                else None
            )

            # Perform search
            results = await self._async_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=False,
            )

            # Format results
            formatted_results = []
            for result in results:
                payload = result.payload or {}
                payload["score"] = result.score
                payload["id"] = str(result.id)
                formatted_results.append(payload)

            return formatted_results

        except (UnexpectedResponse, ResponseHandlingException) as e:
            logger.error(f"❌ Qdrant client error during search: {e}", exc_info=True)
            raise RuntimeError(f"Vector database search failed: {e}") from e
        except Exception as e:
            logger.error(f"❌ Unexpected error during search: {e}", exc_info=True)
            raise

    async def get_by_id(self, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a point by its ID."""
        try:
            result = await self._async_client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=False,
            )

            if result:
                point = result[0]
                payload = point.payload or {}
                payload["id"] = str(point.id)
                return payload
            return None

        except (UnexpectedResponse, ResponseHandlingException) as e:
            logger.error(
                f"❌ Qdrant client error getting point by ID: {e}", exc_info=True
            )
            raise RuntimeError(f"Vector database retrieval failed: {e}") from e
        except Exception as e:
            logger.error(f"❌ Unexpected error getting point by ID: {e}", exc_info=True)
            raise

    async def delete_by_id(self, point_id: str) -> bool:
        """Delete a point by its ID."""
        try:
            result = await self._async_client.delete(
                collection_name=self.collection_name, points_selector=[point_id]
            )
            return result.status == UpdateStatus.COMPLETED

        except Exception as e:
            logger.error(f"❌ Failed to delete point: {e}", exc_info=True)
            raise

    async def delete_by_filter(self, filter_condition: Filter) -> bool:
        """
        Delete points matching a filter condition.

        Args:
            filter_condition: Qdrant filter to match points for deletion

        Returns:
            bool: True if deletion was successful
        """
        try:
            result = await self._async_client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(filter=filter_condition),
            )
            logger.info(
                f"✅ Deleted points matching filter from {self.collection_name}"
            )
            return result.status == UpdateStatus.COMPLETED

        except Exception as e:
            logger.error(f"❌ Failed to delete points by filter: {e}", exc_info=True)
            raise

    async def count(self, content_type: Optional[str] = None) -> int:
        """
        Get count of points, optionally filtered by content_type.

        Args:
            content_type: Optional content type filter
        """
        try:
            if content_type:
                # Count with filter
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="content_type", match=MatchValue(value=content_type)
                        )
                    ]
                )
                result = await self._async_client.count(
                    collection_name=self.collection_name, count_filter=filter_condition
                )
                return result.count
            else:
                # Total count
                info = await self._async_client.get_collection(self.collection_name)
                return info.points_count

        except Exception as e:
            logger.error(f"❌ Failed to count points: {e}", exc_info=True)
            return 0

    async def get_content_types(self) -> List[str]:
        """Get all unique content types in the collection."""
        try:
            # Use scroll to get all unique content types
            content_types = set()
            offset = None

            while True:
                result = await self._async_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=None,
                    limit=100,
                    offset=offset,
                    with_payload=["content_type"],
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    if point.payload and "content_type" in point.payload:
                        content_types.add(point.payload["content_type"])

                offset = result[1]
                if offset is None:
                    break

            return list(content_types)

        except Exception as e:
            logger.error(f"❌ Failed to get content types: {e}", exc_info=True)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Qdrant connection.

        Returns:
            Dictionary with health status and metrics
        """
        try:
            # Get collection info
            info = await self._async_client.get_collection(self.collection_name)

            # Get content type counts
            content_types = await self.get_content_types()
            type_counts = {}
            for ct in content_types:
                type_counts[ct] = await self.count(ct)

            return {
                "status": "healthy",
                "collection": self.collection_name,
                "total_points": info.points_count,
                "vectors_count": info.vectors_count or info.points_count or 0,
                "indexed_vectors_count": info.indexed_vectors_count or 0,
                "content_types": type_counts,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value,
                },
            }

        except Exception as e:
            # Log connection errors without stack trace (expected during outages)
            error_msg = str(e)
            if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                logger.warning(
                    f"⚠️ Qdrant health check failed - connection unavailable: {error_msg}"
                )
            else:
                logger.error(f"❌ Qdrant health check failed: {e}", exc_info=True)
            return {"status": "unhealthy", "error": error_msg}


# Global shared manager instance
_shared_manager: Optional[QdrantEmbeddingsManager] = None


def get_qdrant_embeddings_manager(
    settings: Optional[Settings] = None,
) -> QdrantEmbeddingsManager:
    """
    Get the global Qdrant embeddings manager instance.

    Args:
        settings: Required for first initialization, ignored for subsequent calls
    """
    global _shared_manager
    if _shared_manager is None:
        _shared_manager = QdrantEmbeddingsManager(settings)
    return _shared_manager


@asynccontextmanager
async def qdrant_lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for QdrantEmbeddingsManager.
    """
    # Startup
    try:
        from core.config import settings

        manager = get_qdrant_embeddings_manager(settings)
        await manager.start()
        logger.info("✅ QdrantEmbeddingsManager started successfully")
        yield
    finally:
        # Shutdown
        try:
            if _shared_manager:
                await _shared_manager.shutdown()
                logger.info("✅ QdrantEmbeddingsManager shutdown successfully")
        except Exception as e:
            logger.error(
                f"❌ Error during QdrantEmbeddingsManager shutdown: {e}", exc_info=True
            )


def get_embeddings_manager() -> QdrantEmbeddingsManager:
    """
    Get the initialized Qdrant embeddings manager.
    Raises RuntimeError if not initialized.
    """
    if _shared_manager is None:
        raise RuntimeError(
            "QdrantEmbeddingsManager not initialized. "
            "Make sure to call get_qdrant_embeddings_manager(settings) during startup."
        )
    return _shared_manager
