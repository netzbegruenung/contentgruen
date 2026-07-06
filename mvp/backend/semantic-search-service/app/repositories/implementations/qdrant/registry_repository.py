import logging
from typing import Optional, Type

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository

logger = logging.getLogger(__name__)


class RegistryQdrantRepository(
    QdrantBaseRepository[BaseContentDbEntry, BaseContentSearchResult]
):
    """
    Generic Qdrant repository built directly from a content-type spec.

    This is the persistence counterpart to the declarative content-type registry
    (see ``domain/content_registry.py``): a single, type-parametrized repository
    that replaces the per-type ``*Repository`` clones. New registry-driven content
    types reuse this class with their own ``index_name`` / ``content_type`` / model
    classes -- no new repository subclass is required (rung-1 Step 6 gate).

    All storage/search behavior is inherited unchanged from ``QdrantBaseRepository``;
    only the abstract ``initialize_with_initial_data`` hook is implemented here, as a
    no-op (registry types are created dynamically, not seeded from JSON).
    """

    def __init__(
        self,
        index_name: str,
        content_type: Optional[str],
        settings: Settings,
        db_entry_model_class: Type[BaseContentDbEntry],
        search_result_model_class: Type[BaseContentSearchResult],
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        super().__init__(
            index_name,
            content_type,
            settings,
            db_entry_model_class,
            search_result_model_class,
            embeddings_manager,
        )

    def initialize_with_initial_data(self) -> None:
        """No JSON seed for registry-driven types; content is created dynamically."""
        logger.info(
            f"RegistryQdrantRepository ({self.repository_name}): no initial data load "
            f"(registry-driven content type '{self.content_type}')"
        )
