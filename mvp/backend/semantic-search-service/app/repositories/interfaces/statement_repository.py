from abc import abstractmethod
import uuid
from typing import AbstractSet, Iterable, List

from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.statement import AntwortKurz, StatementDbEntry, StatementSearchResult


class IStatementRepository(
    IBaseContentRepository[StatementDbEntry, StatementSearchResult]
):
    """
    Interface for statement-specific repository operations.

    Extends the base content repository interface with statement-specific functionality.
    """

    @abstractmethod
    def search_with_reply_filter(
        self, query_text: str, limit: int = 10, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search for statements with a minimum number of reply suggestions.

        Args:
            query_text: The text to search for
            limit: Maximum number of results to return
            min_replysuggestions_count: Minimum number of reply suggestions required

        Returns:
            List of statement search results that meet the criteria
        """
        pass

    @abstractmethod
    async def sichtbare_antworten_zaehlen(self, ids: Iterable[uuid.UUID]) -> int:
        """
        Wie viele der Beitraege zu diesen IDs die Suche findet: die Antwortzahl
        (replysuggestions_count) einer Aussage mit diesen Antwortvorschlaegen (#631).
        """
        pass

    @abstractmethod
    async def count_curated(
        self, ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset()
    ) -> int:
        """
        Count statements, leaving out search queries nobody has answered yet,
        except those in ueber_der_schwelle (search queries above the threshold, #436).

        Returns:
            Number of statements that carry curated substance
        """
        pass

    @abstractmethod
    async def search_curated(
        self,
        query_text: str,
        limit: int,
        ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset(),
    ) -> List[StatementSearchResult]:
        """
        Search statements, leaving out search queries nobody has answered yet
        (same criterion as count_curated, including ueber_der_schwelle).
        """
        pass

    @abstractmethod
    async def get_all_curated(
        self,
        limit: int,
        offset: int,
        ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset(),
    ) -> List[StatementDbEntry]:
        """
        List statements page by page, leaving out search queries nobody has
        answered yet (same criterion as count_curated, including ueber_der_schwelle).
        """
        pass

    @abstractmethod
    async def kuratierte(self) -> List[StatementDbEntry]:
        """
        Visible statements, leaving out search queries nobody has answered yet
        (as count_curated).
        """
        pass

    @abstractmethod
    async def ohne_kommentar(self) -> List[StatementDbEntry]:
        """
        Visible statements without a visible Kommentar among their reply
        suggestions, leaving out search queries nobody has answered yet (as
        count_curated). Blocked or deleted Kommentare do not count as an answer.
        """
        pass

    @abstractmethod
    async def zu_antwort(self, beitrag_id: uuid.UUID) -> List[StatementDbEntry]:
        """
        Visible statements the Beitrag answers (#603): those with the Beitrag among
        their reply suggestions, found through the payload field antwort_ids.
        """
        pass

    @abstractmethod
    async def beantwortet_einer(self, beitrag_ids: List[uuid.UUID]) -> bool:
        """
        Whether a visible statement lists one of the given Beitraege among its reply
        suggestions (Meilenstein "Erste Gegenrede", #351).
        """
        pass

    @abstractmethod
    async def sichtbare_antworten(self, ids: List[uuid.UUID]) -> List[AntwortKurz]:
        """
        Of the given reply-suggestion IDs, the Beitraege that are neither blocked
        nor deleted, with ID, type and Titel, in the given order (#603).
        """
        pass
