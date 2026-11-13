"""
Vormoderation (Entscheidung des Maintainers vom 13.11.2026): die Liste der zu
pruefenden Suchanfragen und Freigeben/Ablehnen, nur fuer Admins.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.vormoderation import router
from dependencies import get_suchen_ohne_treffer_service
from services.content.statement_service import AussageNichtGefunden
from services.suchen_ohne_treffer_service import (
    KeineUnbeantworteteSuchanfrage,
    SucheOhneTreffer,
)

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "person-1"}
AUSSAGE = uuid.UUID(int=7)
LISTE = "/api/v1/moderation/suchanfragen"

app = FastAPI()
app.include_router(router, prefix="/api/v1/moderation")


@pytest.fixture
def service():
    dienst = MagicMock()
    dienst.zu_pruefen = AsyncMock(
        return_value=[
            SucheOhneTreffer(AUSSAGE, "Waermepumpen", 9, 3, True),
        ]
    )
    dienst.entscheiden = AsyncMock()
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: dienst
    yield dienst
    app.dependency_overrides.clear()


@pytest.mark.api
class TestVormoderation:
    def test_liste_mit_personen_ohne_zahl_der_suchen(self, service):
        resp = TestClient(app).get(LISTE, headers=ADMIN)

        assert resp.status_code == 200
        assert resp.json() == {
            "suchanfragen": [
                {
                    "statement_id": str(AUSSAGE),
                    "statement_text": "Waermepumpen",
                    "personen_ohne_treffer": 3,
                }
            ]
        }

    @pytest.mark.parametrize(
        "methode, pfad",
        [
            ("get", LISTE),
            ("put", f"{LISTE}/{AUSSAGE}/freigeben"),
            ("put", f"{LISTE}/{AUSSAGE}/ablehnen"),
        ],
    )
    def test_nur_admins(self, service, methode, pfad):
        resp = getattr(TestClient(app), methode)(pfad, headers=MITWIRKENDE)

        assert resp.status_code == 403
        service.zu_pruefen.assert_not_awaited()
        service.entscheiden.assert_not_awaited()

    @pytest.mark.parametrize(
        "aktion, freigegeben", [("freigeben", True), ("ablehnen", False)]
    )
    def test_entscheiden(self, service, aktion, freigegeben):
        resp = TestClient(app).put(f"{LISTE}/{AUSSAGE}/{aktion}", headers=ADMIN)

        assert resp.status_code == 200
        assert resp.json() == {"statement_id": str(AUSSAGE), "freigegeben": freigegeben}
        service.entscheiden.assert_awaited_once_with(AUSSAGE, freigegeben)

    @pytest.mark.parametrize(
        "fehler, status",
        [
            (AussageNichtGefunden("x"), 404),
            (KeineUnbeantworteteSuchanfrage("x"), 409),
            (RuntimeError("weg"), 500),
        ],
    )
    def test_entscheiden_fehler(self, service, fehler, status):
        service.entscheiden.side_effect = fehler

        resp = TestClient(app).put(f"{LISTE}/{AUSSAGE}/freigeben", headers=ADMIN)

        assert resp.status_code == status
