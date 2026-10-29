"""
"Hier fehlt eine Antwort": die Liste der unbeantworteten Aussagen und das Anlegen
einer Aussage vorab. Beides nur fuer Angemeldete; die Liste traegt ID und Text der
Aussage und die Zahl der Personen, die ohne Treffer danach gesucht haben, aber nicht
die Zahl der Suchen.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_statement_service, get_unbeantwortete_aussagen_service
from services.unbeantwortete_aussagen_service import UnbeantworteteAussage

LISTE_URL = "/api/v1/statement/unbeantwortet"
VORAB_URL = "/api/v1/statement/vorab"
ANGEMELDET = {"X-User": "person-1"}

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def liste_service():
    service = MagicMock()
    app.dependency_overrides[get_unbeantwortete_aussagen_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def statement_service():
    service = MagicMock()
    app.dependency_overrides[get_statement_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestUnbeantwortet:
    def test_liefert_id_text_und_personen_ohne_treffer(self, liste_service):
        a, b = uuid.uuid4(), uuid.uuid4()
        liste_service.liste = AsyncMock(
            return_value=[
                UnbeantworteteAussage(a, "Wärmepumpen sind zu teuer", 3),
                UnbeantworteteAussage(b, "Windräder sind hässlich", 0),
            ]
        )

        resp = TestClient(app).get(LISTE_URL, headers=ANGEMELDET)

        assert resp.status_code == 200
        assert resp.json() == {
            "aussagen": [
                {
                    "statement_id": str(a),
                    "statement_text": "Wärmepumpen sind zu teuer",
                    "personen_ohne_treffer": 3,
                },
                {
                    "statement_id": str(b),
                    "statement_text": "Windräder sind hässlich",
                    "personen_ohne_treffer": 0,
                },
            ]
        }

    @pytest.mark.parametrize("headers", [{}, {"X-User": "anonymous"}])
    def test_nur_fuer_angemeldete(self, liste_service, headers):
        liste_service.liste = AsyncMock(return_value=[])

        resp = TestClient(app).get(LISTE_URL, headers=headers)

        assert resp.status_code == 401
        liste_service.liste.assert_not_called()

    def test_fehler_gibt_500_ohne_details(self, liste_service):
        liste_service.liste = AsyncMock(side_effect=RuntimeError("qdrant weg"))

        resp = TestClient(app).get(LISTE_URL, headers=ANGEMELDET)

        assert resp.status_code == 500
        assert "qdrant" not in resp.text


@pytest.mark.api
class TestVorab:
    def test_legt_aussage_mit_person_als_autor_an(self, statement_service):
        neu = uuid.uuid4()
        statement_service.vorab_anlegen = AsyncMock(
            return_value=(True, neu, "Das Heizungsgesetz enteignet uns")
        )

        resp = TestClient(app).post(
            VORAB_URL,
            json={"text": "  Das Heizungsgesetz enteignet uns  "},
            headers=ANGEMELDET,
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "statement_was_new": True,
            "statement_id": str(neu),
            "statement_text": "Das Heizungsgesetz enteignet uns",
        }
        statement_service.vorab_anlegen.assert_awaited_once_with(
            "Das Heizungsgesetz enteignet uns", "person-1"
        )

    def test_vorhandene_aehnliche_aussage_wird_gemeldet(self, statement_service):
        vorhanden = uuid.uuid4()
        statement_service.vorab_anlegen = AsyncMock(
            return_value=(False, vorhanden, "Heizungsgesetz = Enteignung")
        )

        resp = TestClient(app).post(
            VORAB_URL,
            json={"text": "Das Heizungsgesetz enteignet uns"},
            headers=ANGEMELDET,
        )

        assert resp.status_code == 200
        assert resp.json()["statement_was_new"] is False
        assert resp.json()["statement_text"] == "Heizungsgesetz = Enteignung"

    @pytest.mark.parametrize("text", ["", "  ", "ab", "x" * 1001])
    def test_text_muss_passen(self, statement_service, text):
        statement_service.vorab_anlegen = AsyncMock()

        resp = TestClient(app).post(VORAB_URL, json={"text": text}, headers=ANGEMELDET)

        assert resp.status_code == 422
        statement_service.vorab_anlegen.assert_not_called()

    @pytest.mark.parametrize("headers", [{}, {"X-User": "anonymous"}])
    def test_nur_fuer_angemeldete(self, statement_service, headers):
        statement_service.vorab_anlegen = AsyncMock()

        resp = TestClient(app).post(
            VORAB_URL,
            json={"text": "Das Heizungsgesetz enteignet uns"},
            headers=headers,
        )

        assert resp.status_code == 401
        statement_service.vorab_anlegen.assert_not_called()
