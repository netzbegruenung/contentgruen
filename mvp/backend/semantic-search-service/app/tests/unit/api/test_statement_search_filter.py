"""
/statement/searchStatements mit den Filtern fuer das Beitragsformular. Ohne
Filter bleibt der Endpunkt, wie er war.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service

SEARCH_URL = "/api/v1/statement/searchStatements"

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def statement_service():
    service = MagicMock()
    service.search = AsyncMock(return_value=[])
    service.search_filtered = AsyncMock(return_value=[])
    app.dependency_overrides[get_statement_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestSearchStatementsFilter:
    def test_ohne_filter_wie_bisher(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "waermepumpe", "limit": 5}
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
        )

        assert resp.status_code == 200
        statement_service.search_filtered.assert_awaited_once_with(
            "waermepumpe", 5, nur_kuratiert=True, min_similarity=0.5
        )
        statement_service.search.assert_not_awaited()

    def test_min_similarity_ausserhalb_gibt_422(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "waermepumpe", "min_similarity": 1.5}
        )

        assert resp.status_code == 422


@pytest.mark.api
class TestAddReplysuggestionUnbekannteAussage:
    def test_unbekannte_aussage_gibt_404(self, statement_service):
        import uuid

        statement_service.add_statementreplysuggestion_to_statement = AsyncMock(
            side_effect=ValueError("not found")
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
