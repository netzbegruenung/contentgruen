"""
/statement/getById: das Beitragsformular laedt damit die Aussage, auf die es
antwortet (?aussage=<id>). Nur ID und Text gehen raus. Fuer Nicht-Admins dieselbe
Auswahl wie getAll (#436): Eine unbeantwortete Suchanfrage unter der Schwelle gibt
es fuer sie nicht (404).
"""

import logging
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service, get_suchen_ohne_treffer_service
from domain.models.content_origin import ContentOrigin
from tests.conftest import create_base_content_fields, create_statement_data

GET_BY_ID_URL = "/api/v1/statement/getById"

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


UEBER_DER_SCHWELLE = frozenset({uuid.UUID(int=7)})

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "person-1"}
BESUCHER = {"X-User": "anonymous"}
NICHT_ADMINS = [MITWIRKENDE, BESUCHER, {}]
NICHT_ADMIN_IDS = ["mitwirkende", "besucher", "ohne_kopf"]


@pytest.fixture(autouse=True)
def suchen_ohne_treffer():
    dienst = MagicMock()
    dienst.sichtbar_fuer_alle = AsyncMock(return_value=UEBER_DER_SCHWELLE)
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: dienst
    yield dienst
    app.dependency_overrides.clear()


@pytest.fixture
def statement_service(suchen_ohne_treffer):
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


def _aussage(statement_id, origin, antworten):
    return MagicMock(
        id=statement_id,
        text="Wer zahlt die Waermepumpe",
        origin=origin,
        replysuggestions_count=antworten,
    )


@pytest.mark.api
class TestGetByIdSchwelle:
    """Wie getAll (#436): unbeantwortete Suchanfragen erst ab der Schwelle."""

    @pytest.mark.parametrize("headers", NICHT_ADMINS, ids=NICHT_ADMIN_IDS)
    def test_suchanfrage_unter_der_schwelle_gibt_404(self, statement_service, headers):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.SEARCH_QUERY, 0)
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}, headers=headers
        )

        assert resp.status_code == 404
        assert "Waermepumpe" not in resp.text

    @pytest.mark.parametrize("headers", NICHT_ADMINS, ids=NICHT_ADMIN_IDS)
    def test_suchanfrage_ueber_der_schwelle_kommt(self, statement_service, headers):
        statement_id = next(iter(UEBER_DER_SCHWELLE))
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.SEARCH_QUERY, 0)
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}, headers=headers
        )

        assert resp.status_code == 200
        assert resp.json()["statement_text"] == "Wer zahlt die Waermepumpe"

    def test_beantwortete_suchanfrage_kommt_ohne_schwelle(
        self, statement_service, suchen_ohne_treffer
    ):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.SEARCH_QUERY, 1)
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL,
            params={"statement_id": str(statement_id)},
            headers=MITWIRKENDE,
        )

        assert resp.status_code == 200
        suchen_ohne_treffer.sichtbar_fuer_alle.assert_not_awaited()

    def test_kuratierte_aussage_kommt_ohne_schwelle(
        self, statement_service, suchen_ohne_treffer
    ):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.MANUALLY_CREATED, 0)
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}, headers=BESUCHER
        )

        assert resp.status_code == 200
        suchen_ohne_treffer.sichtbar_fuer_alle.assert_not_awaited()

    def test_admin_bekommt_suchanfrage_unter_der_schwelle(
        self, statement_service, suchen_ohne_treffer
    ):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.SEARCH_QUERY, 0)
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}, headers=ADMIN
        )

        assert resp.status_code == 200
        suchen_ohne_treffer.sichtbar_fuer_alle.assert_not_awaited()

    def test_fehler_bei_der_schwelle_gibt_500(
        self, statement_service, suchen_ohne_treffer
    ):
        statement_id = uuid.uuid4()
        statement_service.get = AsyncMock(
            return_value=_aussage(statement_id, ContentOrigin.SEARCH_QUERY, 0)
        )
        suchen_ohne_treffer.sichtbar_fuer_alle.side_effect = RuntimeError("weg")

        resp = TestClient(app, raise_server_exceptions=False).get(
            GET_BY_ID_URL,
            params={"statement_id": str(statement_id)},
            headers=MITWIRKENDE,
        )

        assert resp.status_code == 500
        assert "Waermepumpe" not in resp.text


@pytest.fixture
def echtes_repository(test_settings, test_embeddings_manager):
    """
    Das echte StatementRepository ueber dem Test-Embeddings-Manager, eingehaengt
    als get() des Dienstes: So laeuft der Datensatz durch dieselbe Validierung
    wie in Produktion.
    """
    from repositories.implementations.qdrant.statement_repository import (
        StatementRepository,
    )

    repository = StatementRepository(
        test_settings, embeddings_manager=test_embeddings_manager
    )
    service = MagicMock()
    service.get = repository.get
    app.dependency_overrides[get_statement_service] = lambda: service
    yield test_embeddings_manager
    app.dependency_overrides.clear()


@pytest.mark.api
class TestGetByIdGegenRepository:
    def test_get_by_id_liest_gespeicherten_datensatz(self, echtes_repository):
        statement_id = uuid.uuid4()
        echtes_repository.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    **create_statement_data(text="Waermepumpen sind zu teuer"),
                    "id": str(statement_id),
                    "content_type": "statement",
                }
            ],
        )

        resp = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}
        )

        assert resp.status_code == 200
        assert resp.json()["statement_text"] == "Waermepumpen sind zu teuer"

    def test_suchanfrage_unter_der_schwelle_aus_dem_speicher_gibt_404(
        self, echtes_repository
    ):
        """Herkunft und Antwortzahl so, wie das Repository sie liest."""
        statement_id = uuid.uuid4()
        echtes_repository.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    **create_statement_data(text="Wer zahlt die Waermepumpe"),
                    "origin": ContentOrigin.SEARCH_QUERY.value,
                    "id": str(statement_id),
                    "content_type": "statement",
                }
            ],
        )

        besucher = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}
        )
        admin = TestClient(app).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}, headers=ADMIN
        )

        assert besucher.status_code == 404
        assert admin.status_code == 200

    def test_get_by_id_nicht_vorhanden_gibt_404(self, echtes_repository, caplog):
        with caplog.at_level(logging.INFO):
            resp = TestClient(app).get(
                GET_BY_ID_URL, params={"statement_id": str(uuid.uuid4())}
            )

        assert resp.status_code == 404
        # Erwartbar, kein Fehler: warning ohne Traceback, kein error.
        warnungen = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("not found" in r.getMessage() for r in warnungen)
        assert all(r.exc_info is None for r in warnungen)
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    def test_get_by_id_kaputter_datensatz_gibt_500_statt_404(
        self, echtes_repository, caplog
    ):
        """Pflichtfelder fehlen: Die ValidationError ist ein ValueError, aber kein 'nicht gefunden'."""
        statement_id = uuid.uuid4()
        echtes_repository.add_test_data(
            "statement",
            [{"id": str(statement_id), "content_type": "statement", "text": None}],
        )

        resp = TestClient(app, raise_server_exceptions=False).get(
            GET_BY_ID_URL, params={"statement_id": str(statement_id)}
        )

        assert resp.status_code == 500
        assert "nicht lesbar" in caplog.text
        fehler = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert fehler and all(r.exc_info for r in fehler)
