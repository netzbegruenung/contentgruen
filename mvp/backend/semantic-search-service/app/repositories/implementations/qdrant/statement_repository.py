from typing import List, Optional
import asyncio
import logging

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import QdrantBaseRepository
from repositories.interfaces.statement_repository import IStatementRepository
from domain.models.statement import StatementDbEntry, StatementSearchResult
from domain.models.content_origin import ContentOrigin

logger = logging.getLogger(__name__)


class StatementRepository(
    QdrantBaseRepository[StatementDbEntry, StatementSearchResult],
    IStatementRepository,
):
    def __init__(
        self,
        settings: Settings,
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        """
        Initialize the StatementRepository with the provided Settings instance.
        Uses QdrantEmbeddingsManager for unified storage with logical separation via content_type.

        Args:
        - settings: The Settings instance to be used by the StatementRepository.
        - embeddings_manager: Optional embeddings manager for dependency injection.
        """
        index_name = "statement_index"
        content_type = "statement"

        super().__init__(
            index_name,
            content_type,
            settings,
            StatementDbEntry,
            StatementSearchResult,
            embeddings_manager,
        )

    # Implement IStatementRepository interface

    async def search_with_reply_filter(
        self, query_text: str, limit: int = 10, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search for statements with a minimum number of reply suggestions.
        """
        return await self.search_statements_with_replies(
            query_text, limit, min_replysuggestions_count
        )

    def initialize_with_initial_data(self):
        """
        Initialize the StatementRepository with initial data.

        Note: Statements are typically created dynamically through the ContentOrchestrator
        when processing statements_with_commentaries and statements_with_commentsuggestions data.
        This method serves as a placeholder for any future direct statement initialization needs.
        """
        logger.info(
            "StatementRepository: No direct initial data loading needed - statements are created by ContentOrchestrator"
        )
        # Statements are created dynamically by ContentOrchestrator when processing
        # statements_with_commentaries and statements_with_commentsuggestions data
        pass

    async def count_curated(self) -> int:
        """
        Zaehlt Statements ohne die unbeantworteten Suchanfragen.

        Nicht "origin != search_query": das Frontend haengt eine neue Antwort
        ueber findOrCreateStatement an ein bereits vorhandenes, hinreichend
        aehnliches Statement. Wer aus der Ergebnisansicht heraus einen Beitrag
        ergaenzt, landet deshalb im Regelfall auf genau dem Statement, das die
        eigene Suche vorher angelegt hat. Ein reiner Herkunftsfilter wuerde also
        gerade die kuratierten Aussagen unterschlagen.

        Massgeblich ist stattdessen, ob eine Aussage beantwortet ist:
        ausgeschlossen wird nur, was aus einer Suchanfrage stammt *und* bis
        heute ohne Antwortvorschlag geblieben ist. Der Zaehler auf der
        Startseite zeigt damit gepflegte Substanz, und eine Suchanfrage zaehlt
        in dem Moment mit, in dem ihr jemand Inhalt zur Seite stellt.
        """
        from qdrant_client.models import (
            Filter,
            FieldCondition,
            MatchValue,
            Range,
        )

        unbeantwortete_suchanfrage = Filter(
            must=[
                FieldCondition(
                    key="origin",
                    match=MatchValue(value=ContentOrigin.SEARCH_QUERY.value),
                ),
                FieldCondition(key="replysuggestions_count", range=Range(lt=1)),
            ]
        )

        try:
            result = await self._shared_manager.async_client.count(
                collection_name=self._shared_manager.collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="content_type",
                            match=MatchValue(value=self.content_type),
                        )
                    ],
                    must_not=[unbeantwortete_suchanfrage],
                ),
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count curated statements: {e}", exc_info=True)
            return 0

    async def search_statements_with_replies(
        self, query_text: str, limit: int, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search the statement index for items similar to the provided query text with a minimum number of reply suggestions.
        """
        return await self._async_search_with_replies(
            query_text, limit, min_replysuggestions_count
        )

    async def _async_search_with_replies(
        self, query_text: str, limit: int, min_replysuggestions_count: int
    ) -> List[StatementSearchResult]:
        """Async implementation of search with reply filter using Qdrant Range filters."""
        try:
            from qdrant_client.models import Range, FieldCondition, Filter

            # Build filter for replysuggestions_count using Qdrant Range
            filter_dict = None
            if min_replysuggestions_count > 0:
                # Use Qdrant's range filter for efficient server-side filtering
                filter_dict = {
                    "must": [
                        FieldCondition(
                            key="replysuggestions_count",
                            range=Range(gte=min_replysuggestions_count),
                        )
                    ]
                }

            # Perform search with server-side filtering
            search_results = await self._shared_manager.search(
                query=query_text,
                content_type=self.content_type,
                limit=limit,
                filter_dict=filter_dict,
            )

            logger.info(
                f"Search results for query '{query_text}': {len(search_results)} items "
                f"(filtered for min_replysuggestions_count >= {min_replysuggestions_count})"
            )

            return [
                self.content_search_result_model_class.model_validate(res)
                for res in search_results
            ]

        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            logger.error(f"Query: {query_text}")
            raise
