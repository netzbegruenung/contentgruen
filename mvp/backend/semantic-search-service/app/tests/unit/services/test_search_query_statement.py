"""
Aussage aus der Suchanfrage: Rate-Limit je Aufrufer.

Die Suche ist offen erreichbar und schreibt dabei dauerhaft. Ist das Limit
erreicht, entfaellt nur das Anlegen; die Suche selbst laeuft weiter (siehe
TestSuchpfad unten). Die Sperre je Text sitzt in add_statement
(test_statement_service.py, TestAddStatementDubletten).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.search import router as search_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_statement_service,
    get_voting_service,
)
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from services.search.search_query_statement import (
    SearchQueryStatementRecorder,
    get_search_query_statement_recorder,
)
from utils.rate_limiter import RateLimiter


def _recorder(max_requests: int = 100) -> SearchQueryStatementRecorder:
    return SearchQueryStatementRecorder(
        RateLimiter(max_requests=max_requests, window_minutes=10)
    )


def _dienst() -> MagicMock:
    service = MagicMock()
    service.add_statement = AsyncMock(return_value=(True, uuid.uuid4(), "klima"))
    return service


@pytest.mark.asyncio
class TestRecorder:
    async def test_anlegen_als_suchanfrage_mit_systemautor(self):
        service = _dienst()

        await _recorder().anlegen(service, "klima", "ip:a")

        statement, author, _, origin = service.add_statement.call_args[0]
        assert statement.text == "klima"
        assert statement.replysuggestions == []
        assert author == SEARCH_QUERY_AUTHOR
        assert origin is ContentOrigin.SEARCH_QUERY

    async def test_limit_erreicht_legt_nichts_an(self):
        service = _dienst()
        recorder = _recorder(max_requests=2)

        await recorder.anlegen(service, "eins", "ip:a")
        await recorder.anlegen(service, "zwei", "ip:a")
        ergebnis = await recorder.anlegen(service, "drei", "ip:a")

        assert ergebnis == (False, None, "drei")
        assert service.add_statement.await_count == 2

    async def test_limit_gilt_je_aufrufer(self):
        service = _dienst()
        recorder = _recorder(max_requests=1)

        await recorder.anlegen(service, "eins", "ip:a")
        _, statement_id, _ = await recorder.anlegen(service, "eins", "ip:b")

        assert statement_id is not None
        assert service.add_statement.await_count == 2


SEARCH_URL = "/api/v1/search/searchByText"


@pytest.fixture
def suchapp():
    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1/search")

    service = _dienst()
    service.search_statements = AsyncMock(return_value=[])
    leerer_dienst = MagicMock()
    leerer_dienst.get = AsyncMock(return_value=None)
    leerer_dienst.search = AsyncMock(return_value=[])

    app.dependency_overrides[get_statement_service] = lambda: service
    for abhaengigkeit in (
        get_commentary_service,
        get_generic_text_service,
        get_post_service,
        get_reference_service,
    ):
        app.dependency_overrides[abhaengigkeit] = lambda: leerer_dienst
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

    yield app, service

    for p in patches:
        p.stop()


@pytest.mark.api
class TestSuchpfad:
    def test_suche_laeuft_ohne_aussage_weiter_wenn_limit_erreicht(self, suchapp):
        app, service = suchapp
        app.dependency_overrides[get_search_query_statement_recorder] = lambda: (
            _recorder(max_requests=0)
        )

        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "klima", "limit": 10}
        )

        assert resp.status_code == 200
        assert resp.json()["statement_id"] is None
        assert resp.json()["query_was_newly_added_as_statement"] is False
        service.add_statement.assert_not_called()
        service.search_statements.assert_awaited()

    def test_limit_haengt_an_der_adresse_nicht_an_der_session(self, suchapp):
        """Eine neue X-Session-Id je Anfrage umgeht das Limit nicht."""
        app, service = suchapp
        recorder = _recorder(max_requests=1)
        app.dependency_overrides[get_search_query_statement_recorder] = lambda: recorder
        client = TestClient(app)

        for _ in range(3):
            client.post(
                SEARCH_URL,
                json={"query_text": "klima", "limit": 10},
                headers={"X-Session-Id": str(uuid.uuid4())},
            )

        assert service.add_statement.await_count == 1
