"""
Vormoderation bis zur API (Entscheidung des Maintainers vom 13.11.2026): mit echtem
SuchenOhneTrefferService und gemocktem Repository. Eine unbeantwortete Suchanfrage
ueber der Schwelle, die nicht freigegeben ist, gibt es fuer Nicht-Admins weder in
getById noch in getAll.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service, get_suchen_ohne_treffer_service
from domain.models.content_origin import ContentOrigin
from services.suchen_ohne_treffer_service import (
    PersonenDesTages,
    SuchenOhneTrefferService,
)

SUCHANFRAGE = uuid.UUID(int=7)
MITWIRKENDE = {"X-User": "person-1"}

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


def _repository(freigegeben: bool):
    """Ueber der Schwelle liegt SUCHANFRAGE; freigegeben nur, wenn angegeben."""
    repository = MagicMock()

    def ueber_der_schwelle(seit_woche, mindestanzahl, freigabe=None):
        if freigabe == "freigegebene" and not freigegeben:
            return []
        return [SUCHANFRAGE]

    repository.ueber_der_schwelle.side_effect = ueber_der_schwelle
    return repository


@pytest.fixture
def statement_service():
    service = MagicMock()
    service.get = AsyncMock(
        return_value=MagicMock(
            id=SUCHANFRAGE,
            text="Suchtext mit einem Namen",
            origin=ContentOrigin.SEARCH_QUERY,
            replysuggestions_count=0,
        )
    )
    service.get_all_curated = AsyncMock(return_value=[])
    service.count_curated = AsyncMock(return_value=0)
    app.dependency_overrides[get_statement_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


def _mit_repository(statement_service, freigegeben):
    app.dependency_overrides[get_suchen_ohne_treffer_service] = (
        lambda: SuchenOhneTrefferService(
            _repository(freigegeben), statement_service, PersonenDesTages()
        )
    )


@pytest.mark.api
class TestNichtFreigegeben:
    def test_get_by_id_404(self, statement_service):
        _mit_repository(statement_service, freigegeben=False)

        resp = TestClient(app).get(
            "/api/v1/statement/getById",
            params={"statement_id": str(SUCHANFRAGE)},
            headers=MITWIRKENDE,
        )

        assert resp.status_code == 404
        assert "Suchtext" not in resp.text

    def test_get_all_ohne_die_suchanfrage(self, statement_service):
        _mit_repository(statement_service, freigegeben=False)

        resp = TestClient(app).get("/api/v1/statement/getAll", headers=MITWIRKENDE)

        assert resp.status_code == 200
        statement_service.get_all_curated.assert_awaited_once_with(
            limit=20, offset=0, ueber_der_schwelle=frozenset()
        )

    def test_freigegeben_kommt_sie(self, statement_service):
        _mit_repository(statement_service, freigegeben=True)

        resp = TestClient(app).get(
            "/api/v1/statement/getById",
            params={"statement_id": str(SUCHANFRAGE)},
            headers=MITWIRKENDE,
        )

        assert resp.status_code == 200
        statement_service.get_all_curated.assert_not_awaited()
