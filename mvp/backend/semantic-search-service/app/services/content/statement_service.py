import datetime
from typing import List, Optional
import uuid
import logging

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

logger = logging.getLogger(__name__)


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

    async def _check_statement_similarity(
        self, statement_text: str
    ) -> tuple[Optional[float], Optional[uuid.UUID]]:
        """
        Check if a statement is too similar to existing statements.

        Returns:
            - Tuple of (similarity_score, content_id) for most similar statement, or (None, None)
        """
        logger.debug("Checking for similar existing statements")

        similar_statements = await self.search(statement_text, limit=1)
        if similar_statements and similar_statements[0].score:
            return similar_statements[0].score, similar_statements[0].id
        return None, None

    async def _is_statement_too_similar(
        self, statement_text: str
    ) -> tuple[bool, Optional[StatementSearchResult]]:
        """
        Determine if a statement is too similar to existing ones based on configured threshold.

        Returns:
            - Tuple of (is_too_similar, existing_statement_if_duplicate)
        """
        similar_statements = await self.search(statement_text, limit=1)

        if similar_statements and similar_statements[0].score:
            is_duplicate = (
                similar_statements[0].score
                > self.settings.statement_similarity_threshold
            )
            return is_duplicate, similar_statements[0] if is_duplicate else None
        return False, None

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
        Add a new statement to the repository (only if it is not too similar to an existing statement).
        If no ID is provided, a new UUID is generated.

        Args:
         - statement: The Statement object to be added.
         - id: Optional UUID for the statement. If None, a new UUID is generated.

        Returns:
            - A tuple containing:
                - A boolean indicating if the statement was added (True) or a synonymous statement was already present (False).
                - The ID of the statement, either the newly added one or the ID of the synonymous statement.
                - The text of the statement (either the newly added one or the synonymous statement).
        """
        # Qdrant handles concurrent operations correctly without needing locks
        # Check for similarity using extracted business logic
        most_similar_similarity_score, most_similar_content_id = (
            await self._check_statement_similarity(statement.text)
        )
        is_too_similar, existing_statement = await self._is_statement_too_similar(
            statement.text
        )

        if is_too_similar and existing_statement:
            logger.info(
                f"Statement already exists with ID {existing_statement.id}. "
                f"Similarity score: {existing_statement.score:.3f} > threshold: {self.settings.statement_similarity_threshold}"
            )
            return False, existing_statement.id, existing_statement.text

        # Create StatementInput object from Statement object
        now = created_at or datetime.datetime.now()
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
            most_similar_similarity_score=most_similar_similarity_score,
            most_similar_content_id=most_similar_content_id,
            replysuggestions=statement.replysuggestions,
            replysuggestions_count=len(statement.replysuggestions),
        )

        # Handle potential race conditions gracefully
        try:
            await super()._upsert(statement_input)
            logger.info(
                f"Successfully created new statement with ID {statement_input.id}"
            )
            return True, statement_input.id, statement_input.text
        except Exception as e:
            # If we get a duplicate key error here, it means another thread created the statement
            # between our check and our insert. This is less likely with Qdrant but still possible.
            if "duplicate key" in str(e).lower() or "already exists" in str(e).lower():
                logger.info(
                    f"Statement was created by another thread, fetching existing statement"
                )
                # Try to find the existing statement
                existing_statements = await self.search(statement.text, limit=1)
                if (
                    existing_statements
                    and existing_statements[0].score
                    > self.settings.statement_similarity_threshold
                ):
                    logger.info(
                        f"Found existing statement with ID {existing_statements[0].id}"
                    )
                    return (
                        False,
                        existing_statements[0].id,
                        existing_statements[0].text,
                    )
            # Re-raise if it's not a duplicate error or we couldn't find the existing statement
            raise

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

        # Wirft ValueError, wenn es die Aussage nicht (mehr) gibt.
        statement_db_entry = await self.get(statement_id)

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

        # Lesen, aendern, schreiben ohne Sperre: zwei gleichzeitige Verknuepfungen
        # derselben Aussage koennen sich gegenseitig ueberschreiben.

        statement_replysuggestion = StatementReplysuggestion(
            id=replysuggestion_id,
            content_type=content_type,
            relevance=relevance,
            created=datetime.datetime.now(),
            updated=datetime.datetime.now(),
            number_of_usages=0,
        )

        statement_db_entry.replysuggestions.append(statement_replysuggestion)
        statement_db_entry.replysuggestions_count += 1

        await self.update_statement(statement_db_entry)

        return True

    async def beitrag_als_antwort_verknuepfen(
        self,
        beitrag_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
        author: str,
        statement_id: Optional[uuid.UUID] = None,
        statement_text: Optional[str] = None,
    ) -> Optional[uuid.UUID]:
        """
        Einen gerade gespeicherten Beitrag als Antwort an seine Aussage haengen.

        Mit statement_id wird direkt verknuepft. Ist nur der Text bekannt, wird
        die Aussage jetzt gesucht oder angelegt (add_statement erkennt sehr
        aehnliche Aussagen selbst) - ausdruecklich benannt, also mit der Person
        als Autorin. Ohne beides passiert nichts.

        Returns:
        - Die ID der verknuepften Aussage, oder None ohne Aussage.

        Raises:
        - ValueError, wenn die Aussage zur ID nicht existiert; sonst, was Suche
          oder Speichern werfen. Der Beitrag selbst ist dann trotzdem gespeichert.
        """
        text = (statement_text or "").strip()
        if statement_id is None and not text:
            return None

        if statement_id is None:
            _, statement_id, _ = await self.add_statement(
                Statement(text=text, replysuggestions=[]),
                author,
                ContentStatus.RELEASED_INTERNAL,
                ContentOrigin.MANUALLY_CREATED,
            )

        await self.add_statementreplysuggestion_to_statement(
            statement_id=statement_id,
            replysuggestion_id=beitrag_id,
            content_type=content_type,
            relevance=relevance,
        )
        return statement_id
