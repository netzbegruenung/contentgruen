import os
import json
import logging
from typing import Optional

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository
from repositories.interfaces.reference_repository import IReferenceRepository
from domain.models.reference import ReferenceDbEntry, ReferenceSearchResult

logger = logging.getLogger(__name__)


class ReferenceRepository(
    QdrantBaseRepository[ReferenceDbEntry, ReferenceSearchResult],
    IReferenceRepository,
):
    def __init__(
        self,
        settings: Settings,
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        """
        Initialize the ReferenceRepository with the provided Settings instance.
        Uses QdrantEmbeddingsManager for unified storage with logical separation via content_type.

        Args:
        - settings: The Settings instance to be used by the ReferenceRepository.
        - embeddings_manager: Optional embeddings manager for dependency injection.
        """
        index_name = "reference_index"
        content_type = "reference"

        super().__init__(
            index_name,
            content_type,
            settings,
            ReferenceDbEntry,
            ReferenceSearchResult,
            embeddings_manager,
        )

    def initialize_with_initial_data(self):
        """
        Initialize the ReferenceRepository with initial data.

        Note: References are typically loaded from external sources or created dynamically.
        This method serves as a placeholder for any future reference initialization needs.
        """
        logger.info(
            "ReferenceRepository: No direct initial data loading implemented - references are created dynamically"
        )
        # References could be loaded from JSON files if needed in the future
        pass
