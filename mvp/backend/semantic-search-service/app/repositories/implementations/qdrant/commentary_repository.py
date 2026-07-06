import os
import json
import logging
from typing import Optional

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository
from repositories.interfaces.commentary_repository import ICommentaryRepository
from domain.models.commentary import CommentaryDbEntry, CommentarySearchResult

logger = logging.getLogger(__name__)


class CommentaryRepository(
    QdrantBaseRepository[CommentaryDbEntry, CommentarySearchResult],
    ICommentaryRepository,
):
    def __init__(
        self,
        settings: Settings,
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        """
        Initialize the CommentaryRepository with the provided Settings instance.
        Uses QdrantEmbeddingsManager for unified storage with logical separation via content_type.

        Args:
        - settings: The Settings instance to be used by the CommentaryRepository.
        - embeddings_manager: Optional embeddings manager for dependency injection.
        """
        index_name = "commentary_index"
        content_type = "commentary"

        super().__init__(
            index_name,
            content_type,
            settings,
            CommentaryDbEntry,
            CommentarySearchResult,
            embeddings_manager,
        )

    def initialize_with_initial_data(self):
        """
        Initialize the CommentaryRepository with initial data from JSON files.

        Note: Commentaries are typically created dynamically through the ContentOrchestrator
        when processing statements_with_commentaries data. This method serves as a placeholder
        for any future direct commentary initialization needs.
        """
        logger.info(
            "CommentaryRepository: No direct initial data loading needed - commentaries are created by ContentOrchestrator"
        )
        # Commentaries are created dynamically by ContentOrchestrator when processing
        # statements_with_commentaries data
        pass
