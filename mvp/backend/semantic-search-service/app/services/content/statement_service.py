import asyncio
import datetime
from collections import defaultdict
from domain.models.zeit import utc_jetzt
from typing import Dict, List, Optional, Tuple
import uuid
import logging

from pydantic import ValidationError

from core.config import Settings
from services.content.base_content_service import BaseContentService
from repositories.interfaces.statement_repository import (
    IStatementRepository,
)
from repositories.interfaces.repository_factory import IRepositoryFactory
from domain.models.statement import (
    Statement,
    StatementDbEntry,
    StatementSearchResult,
    StatementReplysuggestion,
)
from domain.models.content_type import ContentType
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from utils.text_normalisierung import SperreJeText

logger = logging.getLogger(__name__)


class AussageNichtGefunden(ValueError):
    """Die Aussage zu einer ID gibt es nicht (mehr) - erwartbar, etwa bei einem alten Link."""


class StatementService(
    BaseContentService[IStatementRepository, StatementDbEntry, StatementSearchResult]
):
    def __init__(
        self,
        settings: Settings,
        repository_factory: Optional[IRepositoryFactory] = None,
    ):
        # Use provided factory or default to QdrantRepositoryFactory
        if repository_factory is None:
            from repositories.implementations.qdrant.qdrant_repository_factory import (
                QdrantRepositoryFactory,
            )

            repository_factory = QdrantRepositoryFactory()

        # Eine Sperre je Aussage um Lesen-Aendern-Schreiben der Antwortvorschlaege.
        # Prozesslokal: schuetzt parallele Anfragen in diesem Worker, nicht ueber
        # mehrere Prozesse hinweg.
        self._verknuepfungs_sperren: Dict[uuid.UUID, asyncio.Lock] = defaultdict(
            asyncio.Lock
        )
        # Eine Sperre je normalisiertem Text um Pruefen-und-Anlegen in add_statement.
        self._text_sperre = SperreJeText()

        repository = repository_factory.create_statement_repository(settings)
        content_repository = repository_factory.create_content_repository(settings)

        super().__init__(
            settings,
            repository,
            content_repository,
            StatementDbEntry,
            StatementSearchResult,
        )

    async def search_statements(
        self, query_text: str, limit: int = 10, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search the statement repository for statements similar to the provided query text with a minimum number of reply suggestions.

        Args:
        - query_text: The query text to search for.
        - limit: The maximum number of results to return.
        - min_replysuggestions_count: The minimum number of reply suggestions a statement must have to be included in the results.

        Returns:
        - A list of StatementResult objects representing the most similar statements to the query text.
        """
        sanitized_query_text = query_text.replace(";", ",").replace("'", '"')

        logger.debug(
            f"Searching for statements with at least {min_replysuggestions_count} reply suggestions"
        )

        return await self._repository.search_statements_with_replies(
            sanitized_query_text, limit, min_replysuggestions_count
        )

    async def search_filtered(
        self,
        query_text: str,
        limit: int = 10,
        nur_kuratiert: bool = False,
        min_similarity: Optional[float] = None,
    ) -> List[StatementSearchResult]:
        """
        Aehnliche Statements fuer die Vorschlaege im Beitragsformular.

        Args:
        - nur_kuratiert: Unbeantwortete Suchanfragen weglassen (Kriterium wie
          count_curated).
        - min_similarity: Nur Treffer mit mindestens diesem Score. Gefiltert wird
          nach der Suche; es kommen also hoechstens `limit` Treffer zurueck.
        """
        sanitized_query_text = query_text.replace(";", ",").replace("'", '"')

        if nur_kuratiert:
            results = await self._repository.search_curated(sanitized_query_text, limit)
        else:
            results = await self._repository.search(sanitized_query_text, limit)

        if min_similarity is None:
            return results
        return [r for r in results if r.score is not None and r.score >= min_similarity]

    async def count_curated(self) -> int:
        """
        Anzahl der Statements ohne die unbeantworteten Suchanfragen.

        Grundlage des Zaehlers "Aussagen" auf der Startseite; die Begruendung
        des Kriteriums steht in StatementRepository.count_curated.
        """
        return await self._repository.count_curated()

    async def add_statement(
        self,
        statement: Statement,
        author: str,
        status: ContentStatus,
        origin: ContentOrigin,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime.datetime] = None,
    ) -> tuple[bool, uuid.UUID, str]:
        """
        Eine Aussage anlegen - oder die vorhandene liefern, wenn es dieselbe schon gibt.

        Dieselbe ist: normalisiert gleicher Text (utils/text_normalisierung.py) oder
        query/query-Aehnlichkeit >= statement_similarity_threshold. Inhaltlich nur
        aehnliche Aussagen gelten nicht als dieselbe - sie schlaegt das Formular vor,
        uebernommen wird still nichts. Gilt fuer alle Wege: Formular, Suche, Seeding.

        Pruefen und Schreiben laufen unter einer Sperre je normalisiertem Text, damit
        zwei gleichzeitige Anfragen mit demselben neuen Text nicht zwei Aussagen anlegen.

        Returns:
            - (neu angelegt, ID, Text) - bei einer vorhandenen Aussage deren ID und Text.
        """
        async with self._text_sperre.halten(statement.text):
            vorhandene, bester = await self._vorhandenen_finden(
                statement.text,
                self.settings.statement_similarity_threshold,
                praefix="query",
            )
            if vorhandene is not None:
                logger.info(
                    f"Statement already exists with ID {vorhandene.id} "
                    f"(score {vorhandene.score:.3f}, threshold {self.settings.statement_similarity_threshold})"
                )
                return False, vorhandene.id, vorhandene.text

            now = created_at or utc_jetzt()
            statement_input = StatementDbEntry(
                text=statement.text,
                id=id or uuid.uuid4(),
                created=now,
                last_modified=now,
                original_author=author,
                last_modified_by=author,
                authors=[AuthorEntry(name=author)],
                edit_history=[],
                status=status,
                origin=origin,
                most_similar_similarity_score=bester.score if bester else None,
                most_similar_content_id=bester.id if bester else None,
                replysuggestions=statement.replysuggestions,
                replysuggestions_count=len(statement.replysuggestions),
            )

            await super()._upsert(statement_input)
            logger.info(
                f"Successfully created new statement with ID {statement_input.id}"
            )
            return True, statement_input.id, statement_input.text

    async def update_statement(self, updated_statement: StatementDbEntry) -> uuid.UUID:

        # TODO: Add any checks here?

        result = await super()._upsert(updated_statement)
        return result

    async def add_statementreplysuggestion_to_statement(
        self,
        statement_id: uuid.UUID,
        replysuggestion_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
    ) -> bool:
        """
        Add a reply suggestion to a statement in the index.

        Args:
        - statement_id: The ID of the statement to add the reply suggestion to.
        - statement_reply_suggestion: The reply suggestion to add to the statement.

        Returns:
        - True if the reply suggestion was successfully added to the statement, False otherwise.
        """

        sperre = self._verknuepfungs_sperren[statement_id]
        try:
            async with sperre:
                return await self._antwortvorschlag_anhaengen(
                    statement_id, replysuggestion_id, content_type, relevance
                )
        finally:
            # Aufraeumen, sobald niemand mehr die Sperre haelt oder auf sie wartet -
            # sonst sammelte sich je beruehrter Aussage eine Sperre an.
            if not sperre.locked() and not getattr(sperre, "_waiters", None):
                self._verknuepfungs_sperren.pop(statement_id, None)

    async def _antwortvorschlag_anhaengen(
        self,
        statement_id: uuid.UUID,
        replysuggestion_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
    ) -> bool:
        """Lesen, aendern, schreiben - nur unter der Sperre der Aussage aufrufen."""
        statement_db_entry = await self._aussage_laden(statement_id)

        # Zweimal dieselbe Antwort (etwa ein wiederholter Speicheraufruf) haengt
        # nicht doppelt an und zaehlt nicht doppelt.
        if any(
            vorschlag.id == replysuggestion_id
            for vorschlag in statement_db_entry.replysuggestions
        ):
            logger.info(
                f"Reply suggestion {replysuggestion_id} already linked to statement {statement_id}"
            )
            return True

        statement_replysuggestion = StatementReplysuggestion(
            id=replysuggestion_id,
            content_type=content_type,
            relevance=relevance,
            created=utc_jetzt(),
            updated=utc_jetzt(),
            number_of_usages=0,
        )

        statement_db_entry.replysuggestions.append(statement_replysuggestion)
        statement_db_entry.replysuggestions_count += 1

        await self.update_statement(statement_db_entry)

        return True

    async def _aussage_laden(self, statement_id: uuid.UUID) -> StatementDbEntry:
        """
        Die Aussage zur ID; AussageNichtGefunden, wenn es sie nicht gibt. Ein nicht
        lesbarer Datensatz (ValidationError) oder ein Speicherfehler geht unveraendert
        weiter - das ist kaputt, nicht abwesend.
        """
        try:
            return await self.get(statement_id)
        except ValidationError:
            raise
        except ValueError as fehler:
            raise AussageNichtGefunden(str(statement_id)) from fehler

    async def beitrag_als_antwort_verknuepfen(
        self,
        beitrag_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
        author: str,
        statement_id: Optional[uuid.UUID] = None,
        statement_text: Optional[str] = None,
    ) -> Optional[Tuple[uuid.UUID, str]]:
        """
        Einen gerade gespeicherten Beitrag als Antwort an seine Aussage haengen.

        Mit statement_id wird direkt verknuepft. Ist nur der Text bekannt, wird
        die Aussage jetzt gesucht oder angelegt (add_statement erkennt sehr
        aehnliche Aussagen selbst) - ausdruecklich benannt, also mit der Person
        als Autorin. Ohne beides passiert nichts.

        Returns:
        - ID und Text der tatsaechlich verknuepften Aussage (mit Text kann das eine
          schon vorhandene, sehr aehnliche sein), oder None ohne Aussage.

        Raises:
        - AussageNichtGefunden, wenn die Aussage zur ID nicht existiert; sonst, was
          Suche oder Speichern werfen. Der Beitrag selbst ist dann trotzdem gespeichert.
        """
        text = (statement_text or "").strip()
        if statement_id is None and not text:
            return None

        if statement_id is None:
            _, statement_id, aussage_text = await self.add_statement(
                Statement(text=text, replysuggestions=[]),
                author,
                ContentStatus.RELEASED_INTERNAL,
                ContentOrigin.MANUALLY_CREATED,
            )
        else:
            aussage_text = (await self._aussage_laden(statement_id)).text

        await self.add_statementreplysuggestion_to_statement(
            statement_id=statement_id,
            replysuggestion_id=beitrag_id,
            content_type=content_type,
            relevance=relevance,
        )
        return statement_id, aussage_text
