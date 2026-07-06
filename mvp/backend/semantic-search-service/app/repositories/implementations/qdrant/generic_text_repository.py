import os
import json
import logging
from typing import Optional

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository
from repositories.interfaces.generic_text_repository import IGenericTextRepository
from domain.models.generic_text import GenericTextDbEntry, GenericTextSearchResult

logger = logging.getLogger(__name__)


class GenericTextRepository(
    QdrantBaseRepository[GenericTextDbEntry, GenericTextSearchResult],
    IGenericTextRepository,
):
    def __init__(
        self,
        settings: Settings,
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        """
        Initialize the GenericTextRepository with the provided Settings instance.
        Uses QdrantEmbeddingsManager for unified storage with logical separation via content_type.

        Args:
        - settings: The Settings instance to be used by the GenericTextRepository.
        - embeddings_manager: Optional embeddings manager for dependency injection.
        """
        index_name = "generic_text_index"
        content_type = "generic_text"

        super().__init__(
            index_name,
            content_type,
            settings,
            GenericTextDbEntry,
            GenericTextSearchResult,
            embeddings_manager,
        )

    def initialize_with_initial_data(self):
        """
        Initialize the GenericTextRepository with initial data.

        Note: Generic texts are typically created dynamically through the ContentOrchestrator
        when processing statements_with_generictexts data. This method serves as a placeholder
        for any future direct generic text initialization needs.
        """
        logger.info(
            "GenericTextRepository: No direct initial data loading needed - generic texts are created by ContentOrchestrator"
        )
        # Generic texts are created dynamically by ContentOrchestrator when processing
        # statements_with_generictexts data
        pass
