"""
/statement/getById: das Beitragsformular laedt damit die Aussage, auf die es
antwortet (?aussage=<id>). Nur ID und Text gehen raus.
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service

GET_BY_ID_URL = "/api/v1/statement/getById"

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def statement_service():
    service = MagicMock()
    app.dependency_overrides[get_statement_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestGetById:
    def test_get_by_id_liefert_id_und_text(self, statement_service):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=MagicMock(id=statement_id, text="Waermepumpen sind zu teuer")
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "statement_id": str(statement_id),
            "statement_text": "Waermepumpen sind zu teuer",
        }
        statement_service.get.assert_awaited_once_with(statement_id)

    def test_get_by_id_unbekannt_gibt_404(self, statement_service):
        statement_service.get = AsyncMock(side_effect=ValueError("not found"))

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(uuid.uuid4())}
        )

        assert resp.status_code == 404

    def test_get_by_id_ohne_uuid_gibt_422(self, statement_service):
        resp = TestClient(app).get(GET_BY_ID_URL, params={"statement_id": "None"})

        assert resp.status_code == 422

    def test_get_by_id_backendfehler_gibt_500(self, statement_service):
        statement_service.get = AsyncMock(side_effect=RuntimeError("qdrant weg"))

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(uuid.uuid4())}
        )

        assert resp.status_code == 500
