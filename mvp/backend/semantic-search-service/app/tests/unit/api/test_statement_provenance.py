"""
Herkunft und Autor der Statements, die beim Suchen entstehen.

Suchanfragen landen weiterhin als Statement im Index - das ist gewollt, es ist
das Rohmaterial dafuer, wo Inhalt fehlt. Zwei Dinge muessen dabei aber halten,
und beide werden hier festgenagelt:

- Herkunft: ContentOrigin.SEARCH_QUERY statt MANUALLY_CREATED, damit sich eine
  Suchanfrage im Bestand vom kuratierten Material unterscheiden laesst.
- Autor: SEARCH_QUERY_AUTHOR statt der suchenden Person. Wer gesucht hat, darf
  nicht am Statement haengen.

Geschrieben wird auf zwei Wegen: das Backend legt in /searchByText selbst an,
und das Frontend ruft aus der Ergebnisansicht zusaetzlich /statement/addStatement
auf. Beide sind hier abgedeckt. /statement/addStatement bedient ausserdem den
ausdruecklichen Weg "Beitrag ergaenzen" - derselbe Endpunkt, unterschieden allein
ueber das Feld `source`; nur dort bleibt die Person Autorin.
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.search import router as search_router
from api.v1.statement import router as statement_router
from dependencies import (
    get_statement_service,
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_voting_service,
)
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus

SEARCH_URL = "/api/v1/search/searchByText"
ADD_STATEMENT_URL = "/api/v1/statement/addStatement"

app = FastAPI()
app.include_router(search_router, prefix="/api/v1/search")
app.include_router(statement_router, prefix="/api/v1/statement")


def _statement_service() -> MagicMock:
    service = MagicMock()
    service.add_statement = AsyncMock(return_value=(True, uuid.uuid4(), "klimaschutz"))
    service.search_statements = AsyncMock(return_value=[])
    service.search = AsyncMock(return_value=[])
    return service


@pytest.fixture
def statement_service():
    """Einen gefakten StatementService in beide Router haengen."""
    service = _statement_service()

    leerer_dienst = MagicMock()
    leerer_dienst.get = AsyncMock(return_value=None)
    leerer_dienst.search = AsyncMock(return_value=[])

    app.dependency_overrides[get_statement_service] = lambda: service
    app.dependency_overrides[get_commentary_service] = lambda: leerer_dienst
    app.dependency_overrides[get_generic_text_service] = lambda: leerer_dienst
    app.dependency_overrides[get_post_service] = lambda: leerer_dienst
    app.dependency_overrides[get_reference_service] = lambda: leerer_dienst
    app.dependency_overrides[get_voting_service] = lambda: MagicMock(
        get_user_votes_for_contents=MagicMock(return_value={})
    )

    patches = [
        patch("api.v1.search.get_polarity_filter_service"),
        patch("api.v1.search.get_keyword_overlap_service"),
        patch("api.v1.search.get_usage_service"),
        patch("api.v1.search.get_search_tracking_service"),
    ]
    gestartet = [p.start() for p in patches]
    gestartet[0].return_value.analyze_and_filter_statement_results.return_value = (
        [],
        {},
    )
    gestartet[1].return_value.analyze_and_boost_results.return_value = ([], {})

    yield service

    for p in patches:
        p.stop()
    app.dependency_overrides.clear()


def _aufruf_argumente(service: MagicMock) -> tuple:
    """(statement, author, status, origin), wie add_statement gerufen wurde."""
    service.add_statement.assert_called_once()
    return service.add_statement.call_args[0]


@pytest.mark.api
class TestSuchpfadBackend:
    """/searchByText legt das Statement selbst an."""

    def test_suche_legt_statement_als_suchanfrage_an(self, statement_service):
        client = TestClient(app)

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        _, author, status, origin = _aufruf_argumente(statement_service)
        assert origin is ContentOrigin.SEARCH_QUERY
        assert author == SEARCH_QUERY_AUTHOR
        assert status is ContentStatus.RELEASED_INTERNAL

    def test_angemeldete_person_haengt_nicht_am_statement(self, statement_service):
        """Auch mit X-User wird der Systemautor gespeichert, nicht die Person."""
        client = TestClient(app)

        resp = client.post(
            SEARCH_URL,
            json={"query_text": "klimaschutz", "limit": 10},
            headers={"X-User": "testuser"},
        )

        assert resp.status_code == 200
        _, author, _, origin = _aufruf_argumente(statement_service)
        assert author == SEARCH_QUERY_AUTHOR
        assert "testuser" not in author
        assert origin is ContentOrigin.SEARCH_QUERY


@pytest.mark.api
class TestAddStatementEndpunkt:
    """
    Derselbe Endpunkt fuer beide Wege; `source` entscheidet ueber den Autor.
    """

    def test_source_search_query_verwirft_die_person(self, statement_service):
        client = TestClient(app)

        resp = client.post(
            ADD_STATEMENT_URL,
            json={
                "statement": {"text": "klimaschutz", "replysuggestions": []},
                "source": "search_query",
            },
            headers={"X-User": "testuser"},
        )

        assert resp.status_code == 200
        _, author, _, origin = _aufruf_argumente(statement_service)
        assert author == SEARCH_QUERY_AUTHOR
        assert origin is ContentOrigin.SEARCH_QUERY

    def test_source_manually_created_behaelt_die_person(self, statement_service):
        """Der ausdrueckliche Weg "Beitrag ergaenzen" bleibt eine Autorenleistung."""
        client = TestClient(app)

        resp = client.post(
            ADD_STATEMENT_URL,
            json={
                "statement": {
                    "text": "Die Gruenen sind eine Verbotspartei!",
                    "replysuggestions": [],
                },
                "source": "manually_created",
            },
            headers={"X-User": "testuser"},
        )

        assert resp.status_code == 200
        _, author, _, origin = _aufruf_argumente(statement_service)
        assert author == "testuser"
        assert origin is ContentOrigin.MANUALLY_CREATED

    def test_ohne_source_gilt_die_datensparsame_voreinstellung(self, statement_service):
        """Ein Aufrufer, der nichts angibt, erzeugt kein Statement mit Personenbezug."""
        client = TestClient(app)

        resp = client.post(
            ADD_STATEMENT_URL,
            json={"statement": {"text": "klimaschutz", "replysuggestions": []}},
            headers={"X-User": "testuser"},
        )

        assert resp.status_code == 200
        _, author, _, origin = _aufruf_argumente(statement_service)
        assert author == SEARCH_QUERY_AUTHOR
        assert origin is ContentOrigin.SEARCH_QUERY

    @pytest.mark.parametrize("source", ["initial_data", "ai-generated", "ingested"])
    def test_andere_herkuenfte_sind_ueber_die_api_nicht_setzbar(
        self, statement_service, source
    ):
        """
        Seeding- und KI-Herkunft gehoeren nicht in die Hand eines API-Aufrufers;
        deshalb ist `source` ein eigenes, zweiwertiges Enum.
        """
        client = TestClient(app)

        resp = client.post(
            ADD_STATEMENT_URL,
            json={
                "statement": {"text": "klimaschutz", "replysuggestions": []},
                "source": source,
            },
            headers={"X-User": "testuser"},
        )

        assert resp.status_code == 422
        statement_service.add_statement.assert_not_called()
