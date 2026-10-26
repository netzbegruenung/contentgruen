"""
/generic_text/addGenericText mit Aussage: Hintergrundinfo speichern und im selben
Aufruf als Antwort verknuepfen - dieselbe Service-Logik wie beim Kommentar. Ist sie
eine Dublette, entscheidet die Person wie beim Kommentar (#301).
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.generic_text import HINTERGRUNDINFO_RELEVANZ, router as generic_text_router
from dependencies import (
    get_generic_text_service,
    get_reference_service,
    get_statement_service,
)
from domain.models.content_type import ContentType
from services.content.base_content_service import Dublettenpruefung
from utils.text_normalisierung import SperreJeText

ADD_URL = "/api/v1/generic_text/addGenericText"
HEADERS = {"X-User": "person-1"}
VORHANDEN_TITEL = "Waermepumpen erreichen im Altbau gute Jahresarbeitszahlen"

app = FastAPI()
app.include_router(generic_text_router, prefix="/api/v1/generic_text")


def _anfrage(**extra) -> dict:
    return {
        "generictext": {
            "title": "Waermepumpen sparen im Altbau 40 Prozent Heizkosten",
            "text": "Laut Feldtest des Fraunhofer ISE erreichen Waermepumpen im Altbau gute Jahresarbeitszahlen.",
            "content_type": "generic_text",
            "references": [],
        },
        "references": [],
        **extra,
    }


@pytest.fixture
def dienste():
    commentary_id = uuid.uuid4()
    generic_text_service = MagicMock()
    generic_text_service.add_generic_text = AsyncMock(
        return_value=(True, commentary_id, "text")
    )
    generic_text_service.pruefe_dublette = AsyncMock(
        return_value=Dublettenpruefung(vorhanden=None, aehnlichster=None)
    )
    generic_text_service.sperre = lambda text: SperreJeText().halten(text)
    statement_service = MagicMock()
    statement_service.beitrag_als_antwort_verknuepfen = AsyncMock()
    reference_service = MagicMock()
    reference_service.find_exact_match = AsyncMock(return_value=None)
    reference_service.add_reference = AsyncMock(
        return_value=(uuid.uuid4(), True, "neu")
    )

    app.dependency_overrides[get_generic_text_service] = lambda: generic_text_service
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_statement_service] = lambda: statement_service
    yield commentary_id, statement_service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestAddGenericTextAntwort:
    def test_ohne_aussage_wird_nichts_verknuepft(self, dienste):
        commentary_id, statement_service = dienste

        resp = TestClient(app).post(ADD_URL, json=_anfrage(), headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(commentary_id),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": True,
            "dublette": False,
            "vorhanden_titel": None,
            "vorhanden_eigen": False,
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_aussagetext_unter_10_zeichen_wird_abgelehnt(self, dienste):
        _, statement_service = dienste

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_text="zu kurz"), headers=HEADERS
        )

        assert resp.status_code == 422
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_leerer_aussagetext_zaehlt_als_ohne_aussage(self, dienste):
        _, statement_service = dienste

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_text="   "), headers=HEADERS
        )

        assert resp.status_code == 200
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_mit_aussage_id_wird_verknuepft(self, dienste):
        commentary_id, statement_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Waermepumpen sind zu teuer",
        )

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_id=str(statement_id)), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json()["statement_id"] == str(statement_id)
        assert resp.json()["statement_text"] == "Waermepumpen sind zu teuer"
        assert resp.json()["verknuepft"] is True
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once_with(
            beitrag_id=commentary_id,
            content_type=ContentType.GENERIC_TEXT,
            relevance=HINTERGRUNDINFO_RELEVANZ,
            author="person-1",
            statement_id=statement_id,
            statement_text=None,
        )

    def test_mit_aussagetext_wird_gesucht_oder_angelegt(self, dienste):
        _, statement_service = dienste
        statement_id = uuid.uuid4()
        # Die tatsaechlich verknuepfte Aussage kann eine vorhandene, aehnliche sein.
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Waermepumpen sind viel zu teuer!",
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text="Waermepumpen sind zu teuer"),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["statement_id"] == str(statement_id)
        assert resp.json()["statement_text"] == "Waermepumpen sind viel zu teuer!"
        aufruf = statement_service.beitrag_als_antwort_verknuepfen.call_args.kwargs
        assert aufruf["statement_text"] == "Waermepumpen sind zu teuer"
        assert aufruf["statement_id"] is None

    def test_verschwundene_aussage_ist_warning_ohne_traceback(self, dienste, caplog):
        import logging
        from services.content.statement_service import AussageNichtGefunden

        _, statement_service = dienste
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = (
            AussageNichtGefunden("weg")
        )

        with caplog.at_level(logging.WARNING):
            resp = TestClient(app).post(
                ADD_URL, json=_anfrage(statement_id=str(uuid.uuid4())), headers=HEADERS
            )

        assert resp.status_code == 200
        assert resp.json()["verknuepft"] is False
        eintraege = [r for r in caplog.records if "statement" in r.getMessage()]
        assert eintraege and all(r.levelno == logging.WARNING for r in eintraege)
        assert all(r.exc_info is None for r in eintraege)

    def test_anderer_fehler_beim_verknuepfen_ist_error_mit_traceback(
        self, dienste, caplog
    ):
        import logging

        _, statement_service = dienste
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = RuntimeError(
            "Qdrant weg"
        )

        with caplog.at_level(logging.WARNING):
            TestClient(app).post(
                ADD_URL, json=_anfrage(statement_id=str(uuid.uuid4())), headers=HEADERS
            )

        fehler = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert fehler and fehler[0].exc_info is not None

    def test_gescheiterte_verknuepfung_behaelt_den_kommentar(self, dienste):
        commentary_id, statement_service = dienste
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = ValueError(
            "Statement not found"
        )

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_id=str(uuid.uuid4())), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(commentary_id),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": False,
            "dublette": False,
            "vorhanden_titel": None,
            "vorhanden_eigen": False,
        }

    def test_text_ueber_2000_zeichen_wird_abgelehnt(self, dienste):
        anfrage = _anfrage()
        anfrage["generictext"]["text"] = "x" * 2001

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 422

    def test_text_mit_2000_zeichen_geht_durch(self, dienste):
        anfrage = _anfrage()
        anfrage["generictext"]["text"] = "x" * 2000

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200

    @staticmethod
    def _dublette(vorhanden, autor="person-1"):
        generic_text_service = app.dependency_overrides[get_generic_text_service]()
        generic_text_service.pruefe_dublette.return_value = Dublettenpruefung(
            vorhanden=MagicMock(
                id=vorhanden, original_author=autor, title=VORHANDEN_TITEL
            ),
            aehnlichster=None,
        )
        return generic_text_service

    def test_dublette_legt_weder_hintergrundinfo_noch_herkunft_an(self, dienste):
        """Die Pruefung laeuft vor den Referenzen - sonst blieben sie verwaist."""
        vorhanden = uuid.uuid4()
        generic_text_service = self._dublette(vorhanden)
        reference_service = app.dependency_overrides[get_reference_service]()
        anfrage = _anfrage()
        anfrage["references"] = [
            {"reference_string": "https://example.org/studie", "description": "Studie"}
        ]

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(vorhanden),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": False,
            "dublette": True,
            "vorhanden_titel": VORHANDEN_TITEL,
            "vorhanden_eigen": True,
        }
        generic_text_service.pruefe_dublette.assert_awaited_once_with(
            anfrage["generictext"]["text"]
        )
        reference_service.find_exact_match.assert_not_awaited()
        reference_service.add_reference.assert_not_awaited()
        generic_text_service.add_generic_text.assert_not_awaited()

    def test_ohne_text_prueft_der_titel(self, dienste):
        """Ohne Text speichert der Dienst den Titel als Text - geprueft wird dasselbe."""
        generic_text_service = app.dependency_overrides[get_generic_text_service]()
        anfrage = _anfrage()
        anfrage["generictext"]["text"] = ""

        TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        generic_text_service.pruefe_dublette.assert_awaited_once_with(
            anfrage["generictext"]["title"]
        )

    def test_ohne_dublette_werden_herkunftsangaben_angelegt(self, dienste):
        generic_text_service = app.dependency_overrides[get_generic_text_service]()
        reference_service = app.dependency_overrides[get_reference_service]()
        anfrage = _anfrage()
        anfrage["references"] = [
            {"reference_string": "https://example.org/studie", "description": "Studie"}
        ]

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["dublette"] is False
        reference_service.add_reference.assert_awaited_once()
        # Das Pruefergebnis geht mit - add_generic_text bettet nicht noch einmal ein.
        pruefung = generic_text_service.pruefe_dublette.return_value
        assert (
            generic_text_service.add_generic_text.call_args.kwargs["dublettenpruefung"]
            is pruefung
        )

    def test_eigene_dublette_mit_aussage_verknuepft_noch_nichts(self, dienste):
        """Erst die Entscheidung der Person verknuepft."""
        _, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        self._dublette(vorhanden)

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_id=str(statement_id)), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(vorhanden)
        assert resp.json()["dublette"] is True
        assert resp.json()["vorhanden_eigen"] is True
        assert resp.json()["statement_id"] is None
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_fremde_dublette_wird_nicht_verknuepft(self, dienste):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        self._dublette(vorhanden, autor="person-2")

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text="Waermepumpen sind zu teuer"),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(vorhanden),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": False,
            "dublette": True,
            "vorhanden_titel": VORHANDEN_TITEL,
            "vorhanden_eigen": False,
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_vorhanden_nehmen_verknuepft_die_eigene_mit_der_aussage(self, dienste):
        _, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        generic_text_service = self._dublette(vorhanden)
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Waermepumpen sind zu teuer",
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_id=str(statement_id), vorhanden_nehmen=str(vorhanden)
            ),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(vorhanden),
            "statement_id": str(statement_id),
            "statement_text": "Waermepumpen sind zu teuer",
            "verknuepft": True,
            "dublette": True,
            "vorhanden_titel": VORHANDEN_TITEL,
            "vorhanden_eigen": True,
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once_with(
            beitrag_id=vorhanden,
            content_type=ContentType.GENERIC_TEXT,
            relevance=HINTERGRUNDINFO_RELEVANZ,
            author="person-1",
            statement_id=statement_id,
            statement_text=None,
        )
        generic_text_service.add_generic_text.assert_not_awaited()

    def test_vorhanden_nehmen_verknuepft_keine_fremde(self, dienste):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        generic_text_service = self._dublette(vorhanden, autor="person-2")

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(vorhanden),
            ),
            headers=HEADERS,
        )

        assert resp.json()["dublette"] is True
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()
        generic_text_service.add_generic_text.assert_not_awaited()

    def test_vorhanden_nehmen_gilt_nur_fuer_die_gezeigte(self, dienste):
        """Ist inzwischen eine andere vorhanden, sieht die Person erst sie."""
        _, statement_service = dienste
        andere = uuid.uuid4()
        self._dublette(andere)

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(uuid.uuid4()),
            ),
            headers=HEADERS,
        )

        assert resp.json()["id"] == str(andere)
        assert resp.json()["dublette"] is True
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_vorhanden_nehmen_legt_nie_eine_neue_an(self, dienste):
        """Ist die gewaehlte nicht mehr da, entsteht keine Hintergrundinfo, die niemand wollte."""
        _, statement_service = dienste
        generic_text_service = app.dependency_overrides[get_generic_text_service]()

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(uuid.uuid4()),
            ),
            headers=HEADERS,
        )

        assert resp.status_code == 409
        generic_text_service.add_generic_text.assert_not_awaited()
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_nehmen_und_trotzdem_speichern_schliessen_einander_aus(self, dienste):
        vorhanden = str(uuid.uuid4())

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(trotz_dublette_von=vorhanden, vorhanden_nehmen=vorhanden),
            headers=HEADERS,
        )

        assert resp.status_code == 422

    def test_vorhanden_nehmen_ohne_aussage_verknuepft_nichts(self, dienste):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        generic_text_service = self._dublette(vorhanden)

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(vorhanden_nehmen=str(vorhanden)), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(vorhanden)
        assert resp.json()["dublette"] is True
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()
        generic_text_service.add_generic_text.assert_not_awaited()

    def test_vorhanden_nehmen_mit_gescheiterter_verknuepfung(self, dienste):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        self._dublette(vorhanden)
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = RuntimeError(
            "Qdrant weg"
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(vorhanden),
            ),
            headers=HEADERS,
        )

        assert resp.json()["dublette"] is True
        assert resp.json()["verknuepft"] is False
        assert resp.json()["id"] == str(vorhanden)

    def test_trotz_dublette_von_legt_die_hintergrundinfo_an(self, dienste):
        """Die Person hat die vorhandene gesehen und speichert trotzdem."""
        neu_id, _ = dienste
        aehnlichster = MagicMock(id=uuid.uuid4(), original_author="person-2")
        generic_text_service = app.dependency_overrides[get_generic_text_service]()
        generic_text_service.pruefe_dublette.return_value = Dublettenpruefung(
            vorhanden=aehnlichster, aehnlichster=aehnlichster
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(trotz_dublette_von=str(aehnlichster.id)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(neu_id)
        assert resp.json()["dublette"] is False
        # Angelegt wird ohne "vorhanden"; die aehnlichste bleibt fuer most_similar_*.
        pruefung = generic_text_service.add_generic_text.call_args.kwargs[
            "dublettenpruefung"
        ]
        assert pruefung == Dublettenpruefung(vorhanden=None, aehnlichster=aehnlichster)

    def test_trotz_eigener_dublette_haengt_nur_die_neue_an_der_aussage(self, dienste):
        neu_id, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        self._dublette(vorhanden)
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Waermepumpen sind zu teuer",
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_id=str(statement_id), trotz_dublette_von=str(vorhanden)
            ),
            headers=HEADERS,
        )

        assert resp.json()["id"] == str(neu_id)
        assert resp.json()["dublette"] is False
        assert resp.json()["statement_id"] == str(statement_id)
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once()
        assert (
            statement_service.beitrag_als_antwort_verknuepfen.call_args.kwargs[
                "beitrag_id"
            ]
            == neu_id
        )

    def test_trotz_dublette_von_gilt_nur_fuer_die_gezeigte(self, dienste):
        andere = uuid.uuid4()
        generic_text_service = self._dublette(andere, autor="person-2")

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(trotz_dublette_von=str(uuid.uuid4())),
            headers=HEADERS,
        )

        assert resp.json()["id"] == str(andere)
        assert resp.json()["dublette"] is True
        generic_text_service.add_generic_text.assert_not_awaited()
