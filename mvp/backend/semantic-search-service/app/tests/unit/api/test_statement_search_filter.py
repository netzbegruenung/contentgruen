"""
/statement/searchStatements mit den Filtern fuer das Beitragsformular. Ohne
Filter bleibt der Endpunkt fuer Admins, wie er war; was Nicht-Admins bekommen,
prueft test_aussagen_fuer_nicht_admins.py (#436).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service, get_suchen_ohne_treffer_service
from services.content.statement_service import AussageNichtGefunden

SEARCH_URL = "/api/v1/statement/searchStatements"
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def statement_service():
    service = MagicMock()
    service.search = AsyncMock(return_value=[])
    service.search_filtered = AsyncMock(return_value=[])
    app.dependency_overrides[get_statement_service] = lambda: service
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: MagicMock(
        ueber_der_schwelle=AsyncMock(return_value=frozenset())
    )
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestSearchStatementsFilter:
    def test_ohne_filter_wie_bisher(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "waermepumpe", "limit": 5}, headers=ADMIN
        )

        assert resp.status_code == 200
        statement_service.search.assert_awaited_once_with("waermepumpe", 5)
        statement_service.search_filtered.assert_not_awaited()

    def test_mit_filtern(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL,
            json={
                "query_text": "waermepumpe",
                "limit": 5,
                "nur_kuratiert": True,
                "min_similarity": 0.5,
            },
            headers=ADMIN,
        )

        assert resp.status_code == 200
        statement_service.search_filtered.assert_awaited_once_with(
            "waermepumpe",
            5,
            nur_kuratiert=True,
            min_similarity=0.5,
            ueber_der_schwelle=frozenset(),
        )
        statement_service.search.assert_not_awaited()

    def test_min_similarity_ausserhalb_gibt_422(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "waermepumpe", "min_similarity": 1.5}
        )

        assert resp.status_code == 422


@pytest.mark.api
class TestSearchStatementsAnfrage:
    """Aus tests/integration/api/v1/test_statement_api.py: Grenzen der Anfrage."""

    @pytest.mark.parametrize(
        "body",
        [
            {"limit": 5},
            {"query_text": ""},
            {"query_text": "klima " * 200},
            {"query_text": "klima", "limit": 0},
            {"query_text": "klima", "limit": 101},
        ],
        ids=["ohne_text", "leer", "ueber_1000_zeichen", "limit_0", "limit_101"],
    )
    def test_ungueltige_anfrage_gibt_422(self, statement_service, body):
        resp = TestClient(app).post(SEARCH_URL, json=body)

        assert resp.status_code == 422
        statement_service.search.assert_not_awaited()
        statement_service.search_filtered.assert_not_awaited()

    def test_kein_json_gibt_422(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL,
            content="kein json",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 422
        statement_service.search.assert_not_awaited()

    def test_ohne_treffer_leere_liste(self, statement_service):
        resp = TestClient(app).post(SEARCH_URL, json={"query_text": "klima"})

        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_fehler_im_service_gibt_500(self, statement_service):
        statement_service.search = AsyncMock(side_effect=RuntimeError("weg"))
        statement_service.search_filtered = AsyncMock(side_effect=RuntimeError("weg"))

        resp = TestClient(app).post(SEARCH_URL, json={"query_text": "klima"})

        assert resp.status_code == 500


@pytest.mark.api
class TestAddReplysuggestionUnbekannteAussage:
    def test_unbekannte_aussage_gibt_404(self, statement_service):
        import uuid

        statement_service.add_statementreplysuggestion_to_statement = AsyncMock(
            side_effect=AussageNichtGefunden("weg")
        )

        resp = TestClient(app).post(
            "/api/v1/statement/addReplysuggestionToStatement",
            json={
                "statement_id": str(uuid.uuid4()),
                "replysuggestion_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "relevance": 1.0,
            },
        )

        assert resp.status_code == 404

    def test_andere_fehler_sind_kein_404(self, statement_service):
        import uuid

        statement_service.add_statementreplysuggestion_to_statement = AsyncMock(
            side_effect=ValueError("irgendetwas anderes")
        )

        resp = TestClient(app).post(
            "/api/v1/statement/addReplysuggestionToStatement",
            json={
                "statement_id": str(uuid.uuid4()),
                "replysuggestion_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "relevance": 1.0,
            },
        )

        assert resp.status_code == 500
