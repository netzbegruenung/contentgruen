"""
getAll und searchStatements fuer Nicht-Admins nur mit Aussagen, die auch die
Oberflaeche zeigt (#436): gepflegte und Suchanfragen ueber der Schwelle der
Kennzahl "Suchen ohne Treffer". Admins wie bisher. Ob der Filter in Qdrant
greift, pruefen die Integrationstests (test_aussagen_fuer_nicht_admins.py).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service, get_suchen_ohne_treffer_service

GET_ALL_URL = "/api/v1/statement/getAll"
SEARCH_URL = "/api/v1/statement/searchStatements"

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "person-1"}
BESUCHER = {"X-User": "anonymous"}
NICHT_ADMINS = [MITWIRKENDE, BESUCHER, {}]
NICHT_ADMIN_IDS = ["mitwirkende", "besucher", "ohne_kopf"]

GEFRAGT = frozenset({uuid.UUID(int=7)})

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def statement_service():
    service = MagicMock()
    service.get_all = AsyncMock(return_value=[])
    service.count = AsyncMock(return_value=40)
    service.get_all_curated = AsyncMock(return_value=[])
    service.count_curated = AsyncMock(return_value=12)
    service.search = AsyncMock(return_value=[])
    service.search_filtered = AsyncMock(return_value=[])
    suchen_ohne_treffer = MagicMock()
    suchen_ohne_treffer.ueber_der_schwelle = AsyncMock(return_value=GEFRAGT)
    service.suchen_ohne_treffer = suchen_ohne_treffer
    app.dependency_overrides[get_statement_service] = lambda: service
    app.dependency_overrides[get_suchen_ohne_treffer_service] = (
        lambda: suchen_ohne_treffer
    )
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestGetAll:
    def test_admin_bekommt_alle_aussagen(self, statement_service):
        resp = TestClient(app).get(
            GET_ALL_URL, params={"page": 2, "page_size": 5}, headers=ADMIN
        )

        assert resp.status_code == 200
        assert resp.json()["total_records_count"] == 40
        statement_service.get_all.assert_awaited_once_with(limit=5, offset=5)
        statement_service.get_all_curated.assert_not_awaited()
        statement_service.suchen_ohne_treffer.ueber_der_schwelle.assert_not_awaited()

    @pytest.mark.parametrize("headers", NICHT_ADMINS, ids=NICHT_ADMIN_IDS)
    def test_nicht_admin_nur_gepflegte_und_ueber_der_schwelle(
        self, statement_service, headers
    ):
        resp = TestClient(app).get(
            GET_ALL_URL, params={"page": 2, "page_size": 5}, headers=headers
        )

        assert resp.status_code == 200
        assert resp.json()["total_records_count"] == 12
        statement_service.get_all_curated.assert_awaited_once_with(
            limit=5, offset=5, auch=GEFRAGT
        )
        statement_service.count_curated.assert_awaited_once_with(auch=GEFRAGT)
        statement_service.get_all.assert_not_awaited()
        statement_service.count.assert_not_awaited()

    def test_admin_kopf_ohne_anmeldung_zaehlt_nicht(self, statement_service):
        resp = TestClient(app).get(
            GET_ALL_URL, headers={"X-User": "anonymous", "X-Is-Admin": "true"}
        )

        assert resp.status_code == 200
        statement_service.get_all.assert_not_awaited()
        statement_service.get_all_curated.assert_awaited_once()

    def test_fehler_bei_der_schwelle_gibt_500(self, statement_service):
        statement_service.suchen_ohne_treffer.ueber_der_schwelle.side_effect = (
            RuntimeError("Datenbank weg")
        )

        resp = TestClient(app).get(GET_ALL_URL, headers=MITWIRKENDE)

        assert resp.status_code == 500
        statement_service.get_all.assert_not_awaited()


@pytest.mark.api
class TestSearchStatements:
    def test_admin_ohne_filter_wie_bisher(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "waermepumpe", "limit": 5}, headers=ADMIN
        )

        assert resp.status_code == 200
        statement_service.search.assert_awaited_once_with("waermepumpe", 5)
        statement_service.search_filtered.assert_not_awaited()
        statement_service.suchen_ohne_treffer.ueber_der_schwelle.assert_not_awaited()

    @pytest.mark.parametrize("headers", NICHT_ADMINS, ids=NICHT_ADMIN_IDS)
    def test_nicht_admin_nur_gepflegte_und_ueber_der_schwelle(
        self, statement_service, headers
    ):
        resp = TestClient(app).post(
            SEARCH_URL,
            json={"query_text": "waermepumpe", "limit": 5},
            headers=headers,
        )

        assert resp.status_code == 200
        statement_service.search_filtered.assert_awaited_once_with(
            "waermepumpe", 5, nur_kuratiert=True, min_similarity=None, auch=GEFRAGT
        )
        statement_service.search.assert_not_awaited()

    @pytest.mark.parametrize("headers", [ADMIN, MITWIRKENDE], ids=["admin", "nicht"])
    def test_nur_kuratiert_bleibt_fuer_alle_ohne_suchanfragen(
        self, statement_service, headers
    ):
        """Das Antwort-auf-Feld schlaegt nur gepflegte Aussagen vor, fuer jede Rolle."""
        resp = TestClient(app).post(
            SEARCH_URL,
            json={
                "query_text": "waermepumpe",
                "limit": 3,
                "nur_kuratiert": True,
                "min_similarity": 0.885,
            },
            headers=headers,
        )

        assert resp.status_code == 200
        statement_service.search_filtered.assert_awaited_once_with(
            "waermepumpe", 3, nur_kuratiert=True, min_similarity=0.885, auch=frozenset()
        )
        statement_service.suchen_ohne_treffer.ueber_der_schwelle.assert_not_awaited()

    def test_admin_mit_min_similarity_ohne_kuratiert(self, statement_service):
        resp = TestClient(app).post(
            SEARCH_URL,
            json={"query_text": "waermepumpe", "limit": 5, "min_similarity": 0.5},
            headers=ADMIN,
        )

        assert resp.status_code == 200
        statement_service.search_filtered.assert_awaited_once_with(
            "waermepumpe", 5, nur_kuratiert=False, min_similarity=0.5, auch=frozenset()
        )
