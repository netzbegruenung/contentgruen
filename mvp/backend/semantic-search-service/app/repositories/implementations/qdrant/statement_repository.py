from typing import List, Optional, Set
import asyncio
import logging
import uuid

from pydantic import ValidationError

from core.config import Settings
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.base_repository import (
    QdrantBaseRepository,
    nur_sichtbar_bedingungen,
)
from repositories.interfaces.statement_repository import IStatementRepository
from domain.models.statement import StatementDbEntry, StatementSearchResult
from domain.models.content_origin import ContentOrigin
from domain.models.content_type import ContentType
from domain.models.content_status import AUSGEBLENDET_WERTE

logger = logging.getLogger(__name__)


def _unbeantwortete_suchanfrage():
    """
    Eine Suchanfrage, auf die noch niemand geantwortet hat - das, was nicht als
    kuratiert gilt. Warum nicht allein die Herkunft zaehlt: count_curated.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

    return Filter(
        must=[
            FieldCondition(
                key="origin",
                match=MatchValue(value=ContentOrigin.SEARCH_QUERY.value),
            ),
            FieldCondition(key="replysuggestions_count", range=Range(lt=1)),
        ]
    )


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
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            result = await self._shared_manager.async_client.count(
                collection_name=self._shared_manager.collection_name,
                count_filter=Filter(
                    # Nur sichtbare Aussagen, wie in der Suche.
                    must=[
                        FieldCondition(
                            key="content_type",
                            match=MatchValue(value=self.content_type),
                        ),
                        *nur_sichtbar_bedingungen(),
                    ],
                    must_not=[_unbeantwortete_suchanfrage()],
                ),
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count curated statements: {e}", exc_info=True)
            return 0

    async def kuratierte(self) -> List[StatementDbEntry]:
        """
        Alle sichtbaren Aussagen ohne die unbeantworteten Suchanfragen (Kriterium
        wie count_curated), fuer die nachtraegliche Zuordnung von Themen. Alle
        Treffer auf einmal, unsortiert; Qdrant scrollt in ID-Reihenfolge.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="content_type", match=MatchValue(value=self.content_type)
                ),
                *nur_sichtbar_bedingungen(),
            ],
            must_not=[_unbeantwortete_suchanfrage()],
        )

        aussagen: List[StatementDbEntry] = []
        offset = None
        while True:
            seite, naechster = await self._shared_manager.async_client.scroll(
                collection_name=self._shared_manager.collection_name,
                scroll_filter=scroll_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for punkt in seite:
                payload = dict(punkt.payload or {})
                payload["id"] = str(punkt.id)
                try:
                    aussagen.append(
                        self.content_db_entry_model_class.model_validate(payload)
                    )
                except ValidationError as fehler:
                    logger.warning(
                        f"kuratierte: Punkt {punkt.id} uebersprungen, "
                        f"Payload ungueltig ({fehler.error_count()} Fehler)"
                    )
            if not seite or naechster is None or naechster == offset:
                break
            offset = naechster
        return aussagen

    async def ohne_kommentar(self) -> List[StatementDbEntry]:
        """
        Sichtbare Aussagen ohne sichtbaren Kommentar unter ihren
        Antwortvorschlaegen, fuer "Hier fehlt eine Antwort".

        Ein gesperrter oder geloeschter Kommentar zaehlt nicht als Antwort: Sein
        Antwortvorschlag bleibt an der Aussage stehen (Sperren und Loeschen aendern
        nur den Zustand des Beitrags), deshalb wird der Zustand der verknuepften
        Kommentare in einem zweiten Schritt nachgeschlagen.

        Ohne die unbeantworteten Suchanfragen (kuratierte): Das
        waere die Suchanfrage einer einzelnen Person. Suchanfragen, nach denen
        mehrere ohne Treffer gesucht haben, kommen ueber die Kennzahl "Suchen ohne
        Treffer" dazu (UnbeantworteteAussagenService). Alle Treffer auf einmal,
        unsortiert; Qdrant scrollt in ID-Reihenfolge.
        """
        aussagen = await self.kuratierte()

        sichtbar = await self._sichtbare_kommentare(
            {
                vorschlag.id
                for aussage in aussagen
                for vorschlag in aussage.replysuggestions
                if vorschlag.content_type == ContentType.COMMENTARY
            }
        )
        return [
            aussage
            for aussage in aussagen
            if not any(
                vorschlag.id in sichtbar for vorschlag in aussage.replysuggestions
            )
        ]

    async def _sichtbare_kommentare(self, ids: Set[uuid.UUID]) -> Set[uuid.UUID]:
        """Welche der IDs einen Kommentar bezeichnen, der weder gesperrt noch geloescht ist."""
        if not ids:
            return set()
        punkte = await self._shared_manager.async_client.retrieve(
            collection_name=self._shared_manager.collection_name,
            ids=[str(i) for i in ids],
            with_payload=["content_type", "status"],
            with_vectors=False,
        )
        return {
            uuid.UUID(str(punkt.id))
            for punkt in punkte
            if (punkt.payload or {}).get("content_type") == ContentType.COMMENTARY.value
            and (punkt.payload or {}).get("status") not in AUSGEBLENDET_WERTE
        }

    async def search_curated(
        self, query_text: str, limit: int
    ) -> List[StatementSearchResult]:
        """
        Aehnliche Statements ohne die unbeantworteten Suchanfragen.

        Dasselbe Kriterium wie count_curated: Wer im Beitragsformular eine
        Aussage sucht, soll gepflegte Aussagen vorgeschlagen bekommen, nicht die
        Suchanfragen anderer Leute, auf die nie jemand geantwortet hat.
        """
        try:
            search_results = await self._shared_manager.search(
                query=query_text,
                content_type=self.content_type,
                limit=limit,
                # Wie die normale Suche nur sichtbare, ohne die unbeantworteten
                # Suchanfragen.
                filter_dict={
                    "must": nur_sichtbar_bedingungen(),
                    "must_not": [_unbeantwortete_suchanfrage()],
                },
            )
            return [
                self.content_search_result_model_class.model_validate(res)
                for res in search_results
            ]
        except Exception as e:
            # Suchtext nicht ins Log, siehe _async_search_with_replies.
            logger.error(
                f"Error during curated statement search: {e} (limit={limit})",
                exc_info=True,
            )
            raise

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

            # Wie search() nur sichtbare Aussagen; der Text einer gesperrten
            # erschiene sonst als statement_text an den Treffern.
            filter_dict = {"must": nur_sichtbar_bedingungen()}
            if min_replysuggestions_count > 0:
                # Use Qdrant's range filter for efficient server-side filtering
                filter_dict["must"].append(
                    FieldCondition(
                        key="replysuggestions_count",
                        range=Range(gte=min_replysuggestions_count),
                    )
                )

            # Perform search with server-side filtering
            search_results = await self._shared_manager.search(
                query=query_text,
                content_type=self.content_type,
                limit=limit,
                filter_dict=filter_dict,
            )

            # DEBUG: je Suche, siehe base_repository.search (#239).
            logger.debug(
                f"Search results: {len(search_results)} items "
                f"(filtered for min_replysuggestions_count >= {min_replysuggestions_count})"
            )

            return [
                self.content_search_result_model_class.model_validate(res)
                for res in search_results
            ]

        except Exception as e:
            # Der Suchtext gehoert auch in den Fehlerzweig nicht ins Log -- er ist
            # dort so schutzwuerdig wie auf dem Anfragepfad (api/v1/search.py:78-83),
            # und die Datenschutzerklaerung sagt zu, dass in den Anwendungslogs
            # nicht steht, wonach jemand gesucht hat. Zum Einordnen des Fehlers
            # genuegen die Fehlerklasse und die Suchparameter.
            logger.error(
                f"Error during search: {e} "
                f"(content_type={self.content_type}, limit={limit}, "
                f"min_replysuggestions_count={min_replysuggestions_count})",
                exc_info=True,
            )
            raise
