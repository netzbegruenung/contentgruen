"""
Themen an Aussagen (#363): die Liste lesen, einer Aussage von Hand zuordnen und die
Zuordnungen als Testset abholen. Zuordnen nur fuer Angemeldete, das Testset und
die Liste aller Aussagen zum Zuordnen nur fuer Admins.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.statement import router as statement_router
from dependencies import get_aussage_themen_service
from domain.themen import THEMEN, ThemaUngueltig
from services.aussage_themen_service import VON_HAND, ThemenZuordnung
from services.content.statement_service import AussageNichtGefunden

LISTE_URL = "/api/v1/statement/themen"
ZUORDNEN_URL = "/api/v1/statement/themen/zuordnen"
TESTSET_URL = "/api/v1/statement/themen/testset"
AUSSAGEN_URL = "/api/v1/statement/themen/aussagen"
ANGEMELDET = {"X-User": "person-1"}
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def themen_service():
    service = MagicMock()
    app.dependency_overrides[get_aussage_themen_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestListe:
    def test_liefert_die_ganze_liste_mit_schluessel_und_name(self):
        resp = TestClient(app).get(LISTE_URL, headers=ANGEMELDET)

        assert resp.status_code == 200
        themen = resp.json()["themen"]
        assert len(themen) == len(THEMEN)
        assert themen[0] == {"schluessel": THEMEN[0].schluessel, "name": THEMEN[0].name}


@pytest.mark.api
class TestZuordnen:
    def test_setzt_die_themen_und_liefert_sie_mit_namen(self, themen_service):
        aussage = uuid.uuid4()
        themen_service.zuordnen = AsyncMock(return_value=["klima", "verkehr"])

        resp = TestClient(app).put(
            ZUORDNEN_URL,
            json={"statement_id": str(aussage), "themen": ["klima", "verkehr"]},
            headers=ANGEMELDET,
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "statement_id": str(aussage),
            "themen": [
                {"schluessel": "klima", "name": "Klima"},
                {"schluessel": "verkehr", "name": "Verkehr"},
            ],
        }
        themen_service.zuordnen.assert_awaited_once_with(aussage, ["klima", "verkehr"])

    def test_ungueltige_themen_geben_422(self, themen_service):
        themen_service.zuordnen = AsyncMock(side_effect=ThemaUngueltig("x"))

        resp = TestClient(app).put(
            ZUORDNEN_URL,
            json={"statement_id": str(uuid.uuid4()), "themen": ["windkraft"]},
            headers=ANGEMELDET,
        )

        assert resp.status_code == 422

    def test_unbekannte_aussage_gibt_404(self, themen_service):
        themen_service.zuordnen = AsyncMock(side_effect=AussageNichtGefunden("x"))

        resp = TestClient(app).put(
            ZUORDNEN_URL,
            json={"statement_id": str(uuid.uuid4()), "themen": ["klima"]},
            headers=ANGEMELDET,
        )

        assert resp.status_code == 404

    @pytest.mark.parametrize("headers", [{}, {"X-User": "anonymous"}])
    def test_nur_fuer_angemeldete(self, themen_service, headers):
        themen_service.zuordnen = AsyncMock()

        resp = TestClient(app).put(
            ZUORDNEN_URL,
            json={"statement_id": str(uuid.uuid4()), "themen": ["klima"]},
            headers=headers,
        )

        assert resp.status_code == 401
        themen_service.zuordnen.assert_not_called()


@pytest.mark.api
class TestTestset:
    def test_liefert_zuordnungen_von_hand_ohne_person(self, themen_service):
        aussage = uuid.uuid4()
        themen_service.testset = AsyncMock(
            return_value=[
                ThemenZuordnung(
                    aussage, "Windräder töten Vögel", ["natur-umwelt"], VON_HAND
                )
            ]
        )

        resp = TestClient(app).get(TESTSET_URL, headers=ADMIN)

        assert resp.status_code == 200
        assert resp.json() == {
            "zuordnungen": [
                {
                    "statement_id": str(aussage),
                    "text": "Windräder töten Vögel",
                    "themen": ["natur-umwelt"],
                    "quelle": "von_hand",
                }
            ]
        }

    def test_nur_fuer_admins(self, themen_service):
        themen_service.testset = AsyncMock(return_value=[])

        resp = TestClient(app).get(TESTSET_URL, headers=ANGEMELDET)

        assert resp.status_code == 403
        themen_service.testset.assert_not_called()


@pytest.mark.api
class TestAussagenZumZuordnen:
    def test_liefert_aussagen_mit_ihren_themen(self, themen_service):
        a, b = uuid.uuid4(), uuid.uuid4()
        themen_service.aussagen_zum_zuordnen = AsyncMock(
            return_value=[
                SimpleNamespace(
                    statement_id=a, text="Tempolimit bringt nichts", themen=("verkehr",)
                ),
                SimpleNamespace(
                    statement_id=b, text="Windräder töten Vögel", themen=()
                ),
            ]
        )

        resp = TestClient(app).get(AUSSAGEN_URL, headers=ADMIN)

        assert resp.status_code == 200
        assert resp.json() == {
            "aussagen": [
                {
                    "statement_id": str(a),
                    "statement_text": "Tempolimit bringt nichts",
                    "themen": [{"schluessel": "verkehr", "name": "Verkehr"}],
                },
                {
                    "statement_id": str(b),
                    "statement_text": "Windräder töten Vögel",
                    "themen": [],
                },
            ]
        }

    def test_nur_fuer_admins(self, themen_service):
        themen_service.aussagen_zum_zuordnen = AsyncMock(return_value=[])

        resp = TestClient(app).get(AUSSAGEN_URL, headers=ANGEMELDET)

        assert resp.status_code == 403
