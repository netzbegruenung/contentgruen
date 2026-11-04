"""
PUT /api/v1/content/{id}: Der Autor aendert seinen Beitrag (#299).

Was Aendern am Beitrag bewirkt, pruefen die Service-Tests
(tests/unit/services/test_beitrag_aendern_service.py); hier nur, wie der Endpunkt
Anfrage, Aufrufer und Ergebnis auf HTTP abbildet.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.content import router as content_router
from dependencies import get_beitrag_aendern_service
from services.content.beitrag_aendern_service import (
    AenderErgebnis,
    Aenderung,
    HerkunftAngabe,
    TextZuLang,
)
from services.content.reference_service import HerkunftsadresseUngueltig

BEITRAG_ID = str(uuid.uuid4())

ANFRAGE = {
    "title": "Wärmepumpe spart auch im Altbau Geld",
    "text": "Mit Flächenheizung rechnet sie sich nach wenigen Jahren.",
    "references": [
        {"reference_string": "https://example.org/studie", "description": "Feldtest"}
    ],
}


@pytest.fixture
def service():
    mock = Mock()
    mock.aendern = AsyncMock(return_value=AenderErgebnis.GEAENDERT)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(content_router, prefix="/api/v1/content")
    app.dependency_overrides[get_beitrag_aendern_service] = lambda: service
    return TestClient(app)


def _aendern(client, anfrage=ANFRAGE, user="autor-1"):
    kopf = {"X-User": user} if user else {}
    return client.put(f"/api/v1/content/{BEITRAG_ID}", json=anfrage, headers=kopf)


@pytest.mark.unit
class TestBeitragAendernApi:
    def test_aendern_autor_ist_204(self, client, service):
        antwort = _aendern(client)

        assert antwort.status_code == 204
        service.aendern.assert_awaited_once_with(
            uuid.UUID(BEITRAG_ID),
            "autor-1",
            Aenderung(
                titel=ANFRAGE["title"],
                text=ANFRAGE["text"],
                herkuenfte=[HerkunftAngabe("https://example.org/studie", "Feldtest")],
            ),
        )

    def test_aendern_ohne_herkunft_ist_erlaubt(self, client, service):
        antwort = _aendern(client, {**ANFRAGE, "references": []})

        assert antwort.status_code == 204
        assert service.aendern.await_args.args[2].herkuenfte == []

    def test_aendern_titel_und_text_ohne_leerraum_am_rand(self, client, service):
        _aendern(
            client,
            {**ANFRAGE, "title": "  Ein Titel mit Haltung ", "text": " Text mit Rand "},
        )

        aenderung = service.aendern.await_args.args[2]
        assert aenderung.titel == "Ein Titel mit Haltung"
        assert aenderung.text == "Text mit Rand"

    def test_aendern_andere_person_ist_403(self, client, service):
        service.aendern.return_value = AenderErgebnis.NICHT_AUTOR

        assert _aendern(client, user="andere").status_code == 403

    def test_aendern_nicht_da_ist_404(self, client, service):
        service.aendern.return_value = AenderErgebnis.NICHT_DA

        assert _aendern(client).status_code == 404

    def test_aendern_mit_offener_meldung_ist_409_mit_text(self, client, service):
        service.aendern.return_value = AenderErgebnis.MELDUNG_OFFEN

        antwort = _aendern(client)

        assert antwort.status_code == 409
        assert antwort.json()["detail"] == "Der Beitrag lässt sich gerade nicht ändern."

    def test_aendern_post_oder_bild_ist_400(self, client, service):
        service.aendern.return_value = AenderErgebnis.NICHT_AENDERBAR

        assert _aendern(client).status_code == 400

    @pytest.mark.parametrize(
        "fehler",
        [
            TextZuLang("Der Text darf höchstens 500 Zeichen lang sein"),
            HerkunftsadresseUngueltig("Ungültige Adresse"),
        ],
    )
    def test_aendern_validierungsfehler_ist_400_mit_text(self, client, service, fehler):
        service.aendern.side_effect = fehler

        antwort = _aendern(client)

        assert antwort.status_code == 400
        assert antwort.json()["detail"] == str(fehler)

    @pytest.mark.parametrize(
        "anfrage",
        [
            {**ANFRAGE, "title": "ab"},
            {**ANFRAGE, "title": "x" * 121},
            {**ANFRAGE, "text": "   "},
            {**ANFRAGE, "text": "Zu kurz"},
            {**ANFRAGE, "cc0_wortlaut": "unbekannt"},
            {**ANFRAGE, "references": [{"reference_string": "  "}]},
            {**ANFRAGE, "references": [{"reference_string": "a"}] * 11},
        ],
    )
    def test_aendern_ungueltige_anfrage_ist_422(self, client, service, anfrage):
        assert _aendern(client, anfrage).status_code == 422
        service.aendern.assert_not_awaited()

    @pytest.mark.parametrize("user", [None, "anonymous"])
    def test_aendern_besucher_ist_401(self, client, service, user):
        assert _aendern(client, user=user).status_code == 401
        service.aendern.assert_not_awaited()
