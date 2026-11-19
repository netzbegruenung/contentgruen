"""
Test module for StatementRepository using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from domain.models.statement import StatementDbEntry, StatementSearchResult
from domain.models.content_type import ContentType
from repositories.implementations.qdrant.base_repository import nur_sichtbar_bedingungen
from tests.conftest import create_base_content_fields, create_statement_data


@pytest.mark.unit
class TestStatementRepository:
    """Test cases for StatementRepository."""

    @pytest.fixture
    def repository(self, test_settings, test_embeddings_manager):
        """Create a statement repository with injected test embeddings manager."""
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        return StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )

    def test_repository_initialization(self, repository):
        """Test that repository initializes correctly."""
        assert repository.repository_name == "statement_index"
        assert repository.content_type == "statement"
        assert repository._shared_manager is not None

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_data(self, repository):
        """Test search returns empty list when no matching data exists."""
        results = await repository.search("climate change", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_matching_results(
        self, repository, test_embeddings_manager
    ):
        """Test search returns matching results."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(text="Climate change is a critical issue"),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Search
        results = await repository.search("climate change", limit=10)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], StatementSearchResult)
        assert results[0].id == test_id
        assert results[0].text == "Climate change is a critical issue"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_get_by_id_returns_item(self, repository, test_embeddings_manager):
        """Test getting an item by ID."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Get by ID
        result = await repository.get(test_id)

        # Assert
        assert isinstance(result, StatementDbEntry)
        assert result.id == test_id
        assert result.text == "Climate change requires immediate action"

    @pytest.mark.asyncio
    async def test_get_by_id_raises_when_not_found(self, repository):
        """Test get raises ValueError when item not found."""
        test_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            await repository.get(test_id)

        assert f"Entry with id {test_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upsert_adds_new_item(self, repository, test_embeddings_manager):
        """Test upserting a new item."""
        # Create new item
        test_id = uuid.uuid4()
        new_item = StatementDbEntry(
            id=test_id,
            content_type=ContentType.STATEMENT,
            **create_base_content_fields(),
            **create_statement_data(),
        )

        # Upsert
        result_id = await repository.upsert(test_id, new_item)

        # Assert
        assert result_id == test_id

        # Verify it was stored
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data
        assert (
            stored_data[str(test_id)]["text"]
            == "Climate change requires immediate action"
        )

    @pytest.mark.asyncio
    async def test_count_returns_correct_number(
        self, repository, test_embeddings_manager
    ):
        """Test count returns correct number of items."""
        # Initially empty
        assert await repository.count() == 0

        # Add some test data
        test_data = [
            {
                **create_base_content_fields(),
                **create_statement_data(text=f"Statement {i}"),
                "id": str(uuid.uuid4()),
                "content_type": "statement",
            }
            for i in range(3)
        ]
        test_embeddings_manager.add_test_data("statement", test_data)

        # Count should now be 3
        assert await repository.count() == 3

    @pytest.mark.asyncio
    async def test_has_content_returns_correct_boolean(
        self, repository, test_embeddings_manager
    ):
        """Test has_content returns correct boolean."""
        # Initially empty
        assert await repository.has_content() is False

        # Add one item
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(),
            "id": str(uuid.uuid4()),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Now has content
        assert await repository.has_content() is True

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, test_embeddings_manager):
        """Test getting all items with pagination."""
        # Add 5 test items
        test_data = [
            {
                **create_base_content_fields(),
                **create_statement_data(text=f"Statement {i}"),
                "id": str(uuid.uuid4()),
                "content_type": "statement",
            }
            for i in range(5)
        ]
        test_embeddings_manager.add_test_data("statement", test_data)

        # Get first 3 items
        results = await repository.get_all(limit=3, offset=0)
        assert len(results) == 3
        assert all(isinstance(r, StatementDbEntry) for r in results)

        # Get next 2 items
        results = await repository.get_all(limit=3, offset=3)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, repository, test_embeddings_manager):
        """Test that SQL injection attempts are properly escaped.

        This test verifies that SQL injection attempts are safely escaped
        and don't break the system. The actual SQL prevention happens at
        the repository level through proper escaping.
        """
        # Add test data with specific content
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(text="Climate change requires action"),
            "id": str(uuid.uuid4()),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Try SQL injection in search - this should be safely escaped
        malicious_query = "'; DROP TABLE users; --"

        # The key test is that this doesn't raise an exception
        # In a real SQL injection, this would fail with a SQL error
        try:
            results = await repository.search(malicious_query, limit=10)
            # The search completes without error
            search_succeeded = True
        except Exception as e:
            # If there was a SQL injection, we'd get an error here
            search_succeeded = False

        assert search_succeeded, "Search should complete without SQL errors"

        # Verify data is still accessible (wasn't dropped)
        real_results = await repository.search("climate", limit=10)
        assert len(real_results) == 1
        assert await repository.count() == 1


@pytest.mark.unit
class TestCountCurated:
    """
    Zaehlkriterium fuer den Startseiten-Zaehler "Aussagen".

    Ausgeschlossen wird nur, was aus einer Suchanfrage stammt *und* noch ohne
    Antwortvorschlag ist. Ein reiner Herkunftsfilter waere falsch: das Frontend
    haengt neue Antworten ueber findOrCreateStatement an ein vorhandenes,
    hinreichend aehnliches Statement, und wer aus der Ergebnisansicht heraus
    einen Beitrag ergaenzt, landet dadurch im Regelfall genau auf dem Statement,
    das die eigene Suche angelegt hat.
    """

    @pytest.fixture
    def repository_mit_zaehler(self, test_settings, test_embeddings_manager):
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        client = MagicMock()
        client.count = AsyncMock(return_value=MagicMock(count=16))

        # async_client ist am TestEmbeddingsManager schreibgeschuetzt; hier zaehlt
        # ohnehin nur, welchen Filter das Repository an Qdrant reicht.
        manager = MagicMock()
        manager.async_client = client
        manager.collection_name = "content_collection"

        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager
        return repository, client

    @pytest.mark.asyncio
    async def test_zaehlt_nur_statements(self, repository_mit_zaehler):
        repository, client = repository_mit_zaehler

        assert await repository.count_curated() == 16

        count_filter = client.count.call_args.kwargs["count_filter"]
        must_keys = {
            bedingung.key: bedingung
            for bedingung in count_filter.must
            if hasattr(bedingung, "key")
        }
        assert must_keys["content_type"].match.value == "statement"

    @pytest.mark.asyncio
    async def test_schliesst_nur_unbeantwortete_suchanfragen_aus(
        self, repository_mit_zaehler
    ):
        repository, client = repository_mit_zaehler

        await repository.count_curated()

        count_filter = client.count.call_args.kwargs["count_filter"]
        verbunden = [b for b in count_filter.must_not if getattr(b, "must", None)]
        assert len(verbunden) == 1

        # Beide Bedingungen muessen zusammen zutreffen, damit ausgeschlossen wird.
        ausschluss = verbunden[0]
        bedingungen = {bedingung.key: bedingung for bedingung in ausschluss.must}
        assert bedingungen["origin"].match.value == "search_query"
        assert bedingungen["replysuggestions_count"].range.lt == 1

    @pytest.mark.asyncio
    async def test_count_curated_zaehlt_nur_sichtbare(self, repository_mit_zaehler):
        """Wie die Suche nur sichtbare Aussagen, gesperrte fehlen im Startseiten-Zaehler."""
        repository, client = repository_mit_zaehler

        await repository.count_curated()

        count_filter = client.count.call_args.kwargs["count_filter"]
        assert all(b in count_filter.must for b in nur_sichtbar_bedingungen())

    @pytest.mark.asyncio
    async def test_gibt_null_zurueck_statt_zu_scheitern(
        self, test_settings, test_embeddings_manager
    ):
        """Der Zaehler ist Beiwerk - er darf die Startseite nicht mitreissen."""
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        manager = MagicMock()
        manager.async_client.count = AsyncMock(side_effect=RuntimeError("Qdrant weg"))

        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager

        assert await repository.count_curated() == 0


@pytest.mark.unit
class TestSearchCurated:
    """Vorschlaege im Beitragsformular: dasselbe Kriterium wie count_curated."""

    @pytest.mark.asyncio
    async def test_schliesst_unbeantwortete_suchanfragen_aus(
        self, test_settings, test_embeddings_manager
    ):
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        manager = MagicMock()
        manager.search = AsyncMock(return_value=[])
        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager

        await repository.search_curated("waermepumpe", 5)

        aufruf = manager.search.call_args.kwargs
        assert aufruf["content_type"] == "statement"
        assert aufruf["limit"] == 5
        # Wie die normale Suche nur sichtbare, ohne die unbeantworteten Suchanfragen
        assert aufruf["filter_dict"]["must"] == nur_sichtbar_bedingungen()
        ausschluss = aufruf["filter_dict"]["must_not"]
        suchanfrage = [b for b in ausschluss if getattr(b, "must", None)]
        assert len(suchanfrage) == 1
        bedingungen = {b.key: b for b in suchanfrage[0].must}
        assert bedingungen["origin"].match.value == "search_query"
        assert bedingungen["replysuggestions_count"].range.lt == 1


@pytest.mark.unit
class TestSearchWithReplyFilter:
    """Die Aussagen-Suche der Hauptsuche findet wie search() nur sichtbare Aussagen."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mindestens", [0, 1])
    async def test_search_with_reply_filter_nur_sichtbare(
        self, test_settings, test_embeddings_manager, mindestens
    ):
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        manager = MagicMock()
        manager.search = AsyncMock(return_value=[])
        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager

        await repository.search_with_reply_filter("waermepumpe", 5, mindestens)

        bedingungen = manager.search.call_args.kwargs["filter_dict"]["must"]
        assert (
            bedingungen[: len(nur_sichtbar_bedingungen())] == nur_sichtbar_bedingungen()
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestMitKommentar:
    """
    Welche Aussagen schon einen sichtbaren Kommentar haben ("Hier fehlt eine
    Antwort"): Qdrants retrieve ist gemockt, geprueft wird die Auswertung.
    """

    AUSSAGE = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    ZWEITE = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
    KOMMENTAR = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
    TEXT = uuid.UUID("dddddddd-0000-0000-0000-000000000001")

    @staticmethod
    def _vorschlag(beitrag_id, content_type="commentary"):
        return {
            "id": str(beitrag_id),
            "content_type": content_type,
            "relevance": 0.9,
            "created": "2026-11-01T10:00:00Z",
            "updated": "2026-11-01T10:00:00Z",
            "number_of_usages": 0,
        }

    @staticmethod
    def _punkt(punkt_id, **payload):
        from types import SimpleNamespace

        return SimpleNamespace(id=str(punkt_id), payload=payload)

    def _repository(self, test_settings, test_embeddings_manager, punkte):
        """retrieve liefert je ID den Punkt aus ``punkte``, unbekannte fehlen."""
        from unittest.mock import AsyncMock, MagicMock
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        async def retrieve(collection_name, ids, with_payload, with_vectors):
            return [punkte[i] for i in ids if i in punkte]

        manager = MagicMock()
        manager.collection_name = "content_collection"
        manager.async_client.retrieve = AsyncMock(side_effect=retrieve)
        repository = StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )
        repository._shared_manager = manager
        return repository, manager.async_client.retrieve

    async def test_sichtbarer_kommentar_heisst_beantwortet(
        self, test_settings, test_embeddings_manager
    ):
        punkte = {
            str(self.AUSSAGE): self._punkt(
                self.AUSSAGE,
                content_type="statement",
                replysuggestions=[self._vorschlag(self.KOMMENTAR)],
            ),
            str(self.KOMMENTAR): self._punkt(
                self.KOMMENTAR, content_type="commentary", status="visible"
            ),
        }
        repository, _ = self._repository(test_settings, test_embeddings_manager, punkte)

        assert await repository.mit_kommentar([self.AUSSAGE]) == {self.AUSSAGE}

    async def test_nur_gesperrter_kommentar_heisst_nicht_beantwortet(
        self, test_settings, test_embeddings_manager
    ):
        punkte = {
            str(self.AUSSAGE): self._punkt(
                self.AUSSAGE,
                content_type="statement",
                replysuggestions=[self._vorschlag(self.KOMMENTAR)],
            ),
            str(self.KOMMENTAR): self._punkt(
                self.KOMMENTAR, content_type="commentary", status="blocked"
            ),
        }
        repository, _ = self._repository(test_settings, test_embeddings_manager, punkte)

        assert await repository.mit_kommentar([self.AUSSAGE]) == set()

    async def test_antwortvorschlaege_als_json_text(
        self, test_settings, test_embeddings_manager
    ):
        """Aeltere Punkte tragen die Antwortvorschlaege als JSON-Text."""
        import json

        punkte = {
            str(self.AUSSAGE): self._punkt(
                self.AUSSAGE,
                content_type="statement",
                replysuggestions=json.dumps([self._vorschlag(self.KOMMENTAR)]),
            ),
            str(self.KOMMENTAR): self._punkt(
                self.KOMMENTAR, content_type="commentary", status="visible"
            ),
        }
        repository, _ = self._repository(test_settings, test_embeddings_manager, punkte)

        assert await repository.mit_kommentar([self.AUSSAGE]) == {self.AUSSAGE}

    async def test_fremder_content_type_zaehlt_nicht(
        self, test_settings, test_embeddings_manager
    ):
        """Weder ein Punkt, der keine Aussage ist, noch ein Text statt Kommentar."""
        punkte = {
            str(self.AUSSAGE): self._punkt(
                self.AUSSAGE,
                content_type="commentary",
                replysuggestions=[self._vorschlag(self.KOMMENTAR)],
            ),
            str(self.ZWEITE): self._punkt(
                self.ZWEITE,
                content_type="statement",
                replysuggestions=[self._vorschlag(self.TEXT, "generic_text")],
            ),
            str(self.KOMMENTAR): self._punkt(
                self.KOMMENTAR, content_type="commentary", status="visible"
            ),
            str(self.TEXT): self._punkt(
                self.TEXT, content_type="generic_text", status="visible"
            ),
        }
        repository, _ = self._repository(test_settings, test_embeddings_manager, punkte)

        assert await repository.mit_kommentar([self.AUSSAGE, self.ZWEITE]) == set()

    async def test_gescheiterter_abruf_geht_an_den_aufrufer(
        self, test_settings, test_embeddings_manager
    ):
        """Was dann gilt, entscheidet der Service (UnbeantworteteAussagenService)."""
        repository, retrieve = self._repository(
            test_settings, test_embeddings_manager, {}
        )
        retrieve.side_effect = RuntimeError("Qdrant weg")

        with pytest.raises(RuntimeError):
            await repository.mit_kommentar([self.AUSSAGE])

    async def test_ruft_in_paketen_ab(self, test_settings, test_embeddings_manager):
        from repositories.implementations.qdrant import statement_repository

        repository, retrieve = self._repository(
            test_settings, test_embeddings_manager, {}
        )
        ids = [uuid.uuid4() for _ in range(statement_repository._IDS_JE_ABRUF + 1)]

        assert await repository.mit_kommentar(ids) == set()
        groessen = [len(c.kwargs["ids"]) for c in retrieve.call_args_list]
        assert groessen == [statement_repository._IDS_JE_ABRUF, 1]

    async def test_kommentare_auch_in_paketen(
        self, test_settings, test_embeddings_manager
    ):
        """Der zweite Abruf (Zustand der Kommentare) teilt ebenfalls in Pakete."""
        from repositories.implementations.qdrant import statement_repository

        kommentare = [
            uuid.uuid4() for _ in range(statement_repository._IDS_JE_ABRUF + 1)
        ]
        punkte = {
            str(self.AUSSAGE): self._punkt(
                self.AUSSAGE,
                content_type="statement",
                replysuggestions=[self._vorschlag(k) for k in kommentare],
            ),
            str(kommentare[-1]): self._punkt(
                kommentare[-1], content_type="commentary", status="visible"
            ),
        }
        repository, retrieve = self._repository(
            test_settings, test_embeddings_manager, punkte
        )

        assert await repository.mit_kommentar([self.AUSSAGE]) == {self.AUSSAGE}
        groessen = [len(c.kwargs["ids"]) for c in retrieve.call_args_list]
        assert groessen == [1, statement_repository._IDS_JE_ABRUF, 1]
