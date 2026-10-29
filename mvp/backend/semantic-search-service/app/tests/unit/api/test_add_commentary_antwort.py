"""
/commentary/addCommentary mit Aussage: Kommentar speichern und im selben Aufruf
als Antwort verknuepfen. Scheitert die Verknuepfung, bleibt der Kommentar
gespeichert und die Antwort sagt es (verknuepft=false).
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import KOMMENTAR_RELEVANZ, router as commentary_router
from dependencies import (
    get_aussage_themen_service,
    get_commentary_service,
    get_reference_service,
    get_statement_service,
)
from domain.models.commentary import Stil, Zweck
from domain.models.content_type import ContentType
from services.content.base_content_service import Dublettenpruefung
from utils.text_normalisierung import SperreJeText

ADD_URL = "/api/v1/commentary/addCommentary"
HEADERS = {"X-User": "person-1"}
VORHANDEN_TITEL = "Waermepumpen rechnen sich auch im Altbau"

app = FastAPI()
app.include_router(commentary_router, prefix="/api/v1/commentary")


def _anfrage(**extra) -> dict:
    return {
        "commentary": {
            "title": "Waermepumpen lohnen sich auch im Altbau",
            "text": "Mit Foerderung rechnet sich die Pumpe schon nach wenigen Jahren.",
            "content_type": "commentary",
            "references": [],
        },
        "references": [],
        **extra,
    }


@pytest.fixture
def themen_service():
    # Die Aussage hat noch keine Themen; zuordnen gibt die gesetzten zurueck.
    service = MagicMock()
    # Wie AussageThemenService.ergaenzen: eine Aussage mit Themen (bestand) behaelt ihre.
    service.bestand = {}
    service.ergaenzen = AsyncMock(
        side_effect=lambda statement_id, themen: service.bestand.get(
            statement_id, themen
        )
    )
    return service


@pytest.fixture
def dienste(themen_service):
    commentary_id = uuid.uuid4()
    commentary_service = MagicMock()
    commentary_service.add_commentary = AsyncMock(
        return_value=(True, commentary_id, "text")
    )
    commentary_service.pruefe_dublette = AsyncMock(
        return_value=Dublettenpruefung(vorhanden=None, aehnlichster=None)
    )
    commentary_service.sperre = lambda text: SperreJeText().halten(text)
    statement_service = MagicMock()
    statement_service.beitrag_als_antwort_verknuepfen = AsyncMock()
    reference_service = MagicMock()
    reference_service.find_exact_match = AsyncMock(return_value=None)
    reference_service.add_reference = AsyncMock(
        return_value=(uuid.uuid4(), True, "neu")
    )

    app.dependency_overrides[get_commentary_service] = lambda: commentary_service
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_statement_service] = lambda: statement_service
    app.dependency_overrides[get_aussage_themen_service] = lambda: themen_service
    yield commentary_id, statement_service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestAddCommentaryAntwort:
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
            "themen": [],
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
            content_type=ContentType.COMMENTARY,
            relevance=KOMMENTAR_RELEVANZ,
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
            "themen": [],
        }

    @staticmethod
    def _dublette(vorhanden, autor="person-1"):
        commentary_service = app.dependency_overrides[get_commentary_service]()
        commentary_service.pruefe_dublette.return_value = Dublettenpruefung(
            vorhanden=MagicMock(
                id=vorhanden, original_author=autor, title=VORHANDEN_TITEL
            ),
            aehnlichster=None,
        )
        return commentary_service

    def test_dublette_legt_keine_herkunftsangaben_an(self, dienste):
        """Die Pruefung laeuft vor den Referenzen - sonst blieben sie verwaist."""
        vorhanden = uuid.uuid4()
        commentary_service = self._dublette(vorhanden)
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
            "themen": [],
        }
        commentary_service.pruefe_dublette.assert_awaited_once_with(
            anfrage["commentary"]["text"]
        )
        reference_service.find_exact_match.assert_not_awaited()
        reference_service.add_reference.assert_not_awaited()
        commentary_service.add_commentary.assert_not_awaited()

    def test_dublette_ohne_aussage_verknuepft_nichts(self, dienste):
        _, statement_service = dienste
        self._dublette(uuid.uuid4())

        TestClient(app).post(ADD_URL, json=_anfrage(), headers=HEADERS)

        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_eigene_dublette_mit_aussage_verknuepft_noch_nichts(self, dienste):
        """Erst die Entscheidung der Person verknuepft (#242) - bis dahin sagt die
        Antwort nicht verknuepft (#238)."""
        _, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        self._dublette(vorhanden)

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_id=str(statement_id)), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(vorhanden),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": False,
            "dublette": True,
            "vorhanden_titel": VORHANDEN_TITEL,
            "vorhanden_eigen": True,
            "themen": [],
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_vorhanden_nehmen_verknuepft_den_eigenen_mit_der_aussage(self, dienste):
        _, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        commentary_service = self._dublette(vorhanden)
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
            "themen": [],
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once_with(
            beitrag_id=vorhanden,
            content_type=ContentType.COMMENTARY,
            relevance=KOMMENTAR_RELEVANZ,
            author="person-1",
            statement_id=statement_id,
            statement_text=None,
        )
        # Kein neuer Kommentar.
        commentary_service.add_commentary.assert_not_awaited()

    def test_vorhanden_nehmen_verknuepft_keinen_fremden(self, dienste):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        commentary_service = self._dublette(vorhanden, autor="person-2")

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(vorhanden),
            ),
            headers=HEADERS,
        )

        assert resp.json()["dublette"] is True
        assert resp.json()["statement_id"] is None
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()
        commentary_service.add_commentary.assert_not_awaited()

    def test_vorhanden_nehmen_gilt_nur_fuer_den_gezeigten(self, dienste):
        """Ist inzwischen ein anderer vorhanden, sieht die Person erst ihn."""
        _, statement_service = dienste
        anderer = uuid.uuid4()
        self._dublette(anderer)

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(uuid.uuid4()),
            ),
            headers=HEADERS,
        )

        assert resp.json()["id"] == str(anderer)
        assert resp.json()["dublette"] is True
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_vorhanden_nehmen_legt_nie_einen_neuen_an(self, dienste):
        """Ist der gewaehlte nicht mehr da, entsteht kein Kommentar, den niemand wollte."""
        _, statement_service = dienste
        commentary_service = app.dependency_overrides[get_commentary_service]()

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text="Waermepumpen sind zu teuer",
                vorhanden_nehmen=str(uuid.uuid4()),
            ),
            headers=HEADERS,
        )

        assert resp.status_code == 409
        commentary_service.add_commentary.assert_not_awaited()
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
        """Ohne Aussage gibt es nichts zu verknuepfen - und der vorhandene ist noch da."""
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        commentary_service = self._dublette(vorhanden)

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(vorhanden_nehmen=str(vorhanden)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(vorhanden)
        assert resp.json()["dublette"] is True
        assert resp.json()["statement_id"] is None
        assert resp.json()["verknuepft"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()
        commentary_service.add_commentary.assert_not_awaited()

    def test_trotz_eigener_dublette_haengt_nur_der_neue_an_der_aussage(self, dienste):
        commentary_id, statement_service = dienste
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

        assert resp.json()["id"] == str(commentary_id)
        assert resp.json()["dublette"] is False
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once()
        assert (
            statement_service.beitrag_als_antwort_verknuepfen.call_args.kwargs[
                "beitrag_id"
            ]
            == commentary_id
        )

    def test_fremde_dublette_wird_nicht_verknuepft(self, dienste):
        """Ein fremder Kommentar darf nicht an eine selbst gewaehlte Aussage."""
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
            "themen": [],
        }
        # Auch keine Aussage angelegt - das passiert erst beim Verknuepfen.
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

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

    def test_ohne_dublette_werden_herkunftsangaben_angelegt(self, dienste):
        commentary_service = app.dependency_overrides[get_commentary_service]()
        reference_service = app.dependency_overrides[get_reference_service]()
        anfrage = _anfrage()
        anfrage["references"] = [
            {"reference_string": "https://example.org/studie", "description": "Studie"}
        ]

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["dublette"] is False
        reference_service.add_reference.assert_awaited_once()
        # Das Pruefergebnis geht mit - add_commentary bettet nicht noch einmal ein.
        pruefung = commentary_service.pruefe_dublette.return_value
        assert (
            commentary_service.add_commentary.call_args.kwargs["dublettenpruefung"]
            is pruefung
        )

    def test_text_ueber_500_zeichen_wird_abgelehnt(self, dienste):
        anfrage = _anfrage()
        anfrage["commentary"]["text"] = "x" * 501

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 422

    def test_text_mit_500_zeichen_geht_durch(self, dienste):
        anfrage = _anfrage()
        anfrage["commentary"]["text"] = "x" * 500

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200

    def test_kurz_und_lang_werden_gespeichert(self, dienste):
        """Die Fassungen Kurz und Lang sind optional (#355)."""
        anfrage = _anfrage()
        anfrage["commentary"]["short_text"] = "Die Pumpe rechnet sich."
        anfrage["commentary"]["long_text"] = "Mit Förderung und Strompreis gerechnet."

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        commentary_service = app.dependency_overrides[get_commentary_service]()
        gespeichert = commentary_service.add_commentary.call_args.args[0]
        assert (gespeichert.short_text, gespeichert.long_text) == (
            "Die Pumpe rechnet sich.",
            "Mit Förderung und Strompreis gerechnet.",
        )

    def test_zweck_und_stil_werden_gespeichert(self, dienste):
        """Zweck und Stil sind optional (#357); bissig nur fuer die eigenen Leute."""
        anfrage = _anfrage()
        anfrage["commentary"]["zweck"] = "eigene_leute"
        anfrage["commentary"]["style"] = "bissig"

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        commentary_service = app.dependency_overrides[get_commentary_service]()
        gespeichert = commentary_service.add_commentary.call_args.args[0]
        assert (gespeichert.zweck, gespeichert.style) == (
            Zweck.EIGENE_LEUTE,
            Stil.BISSIG,
        )

    def test_ohne_zweck_wird_kommentarspalte_gespeichert(self, dienste):
        resp = TestClient(app).post(ADD_URL, json=_anfrage(), headers=HEADERS)

        assert resp.status_code == 200
        commentary_service = app.dependency_overrides[get_commentary_service]()
        gespeichert = commentary_service.add_commentary.call_args.args[0]
        assert (gespeichert.zweck, gespeichert.style) == (Zweck.KOMMENTARSPALTE, None)

    def test_bissig_in_der_kommentarspalte_wird_abgelehnt(self, dienste):
        anfrage = _anfrage()
        anfrage["commentary"]["style"] = "bissig"

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 422
        commentary_service = app.dependency_overrides[get_commentary_service]()
        commentary_service.add_commentary.assert_not_called()

    def test_leere_fassungen_gelten_als_nicht_vorhanden(self, dienste):
        """Sonst zeigte die Karte einen Reiter ohne Text."""
        anfrage = _anfrage()
        anfrage["commentary"]["short_text"] = "   "
        anfrage["commentary"]["long_text"] = ""

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        commentary_service = app.dependency_overrides[get_commentary_service]()
        gespeichert = commentary_service.add_commentary.call_args.args[0]
        assert (gespeichert.short_text, gespeichert.long_text) == (None, None)

    @pytest.mark.parametrize(
        "feld, zeichen, status",
        [
            ("short_text", 280, 200),
            ("short_text", 281, 422),
            ("long_text", 2000, 200),
            ("long_text", 2001, 422),
        ],
    )
    def test_fassungen_haben_eine_hoechstlaenge(self, dienste, feld, zeichen, status):
        anfrage = _anfrage()
        anfrage["commentary"][feld] = "x" * zeichen

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == status

    def test_trotz_dublette_von_legt_den_kommentar_an(self, dienste):
        """Die Person hat den vorhandenen gesehen und speichert trotzdem."""
        commentary_id, _ = dienste
        aehnlichster = MagicMock(id=uuid.uuid4(), original_author="person-2")
        commentary_service = app.dependency_overrides[get_commentary_service]()
        commentary_service.pruefe_dublette.return_value = Dublettenpruefung(
            vorhanden=aehnlichster, aehnlichster=aehnlichster
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(trotz_dublette_von=str(aehnlichster.id)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(commentary_id)
        assert resp.json()["dublette"] is False
        assert resp.json()["vorhanden_titel"] is None
        assert resp.json()["vorhanden_eigen"] is False
        # Angelegt wird ohne "vorhanden"; der aehnlichste bleibt fuer most_similar_*.
        pruefung = commentary_service.add_commentary.call_args.kwargs[
            "dublettenpruefung"
        ]
        assert pruefung == Dublettenpruefung(vorhanden=None, aehnlichster=aehnlichster)

    def test_trotz_dublette_von_verknuepft_den_neuen_mit_der_aussage(self, dienste):
        commentary_id, statement_service = dienste
        statement_id = uuid.uuid4()
        vorhanden = uuid.uuid4()
        self._dublette(vorhanden, autor="person-2")
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Waermepumpen sind zu teuer",
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                trotz_dublette_von=str(vorhanden), statement_id=str(statement_id)
            ),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(commentary_id)
        assert resp.json()["statement_id"] == str(statement_id)
        assert (
            statement_service.beitrag_als_antwort_verknuepfen.call_args.kwargs[
                "beitrag_id"
            ]
            == commentary_id
        )

    def test_ohne_trotz_dublette_von_bleibt_es_bei_der_dublette(self, dienste):
        commentary_service = self._dublette(uuid.uuid4(), autor="person-2")

        resp = TestClient(app).post(ADD_URL, json=_anfrage(), headers=HEADERS)

        assert resp.json()["dublette"] is True
        assert resp.json()["vorhanden_titel"] == VORHANDEN_TITEL
        assert resp.json()["vorhanden_eigen"] is False
        assert resp.json()["verknuepft"] is False
        commentary_service.add_commentary.assert_not_awaited()

    def test_trotz_dublette_von_gilt_nur_fuer_den_gezeigten(self, dienste):
        """Ist inzwischen ein anderer vorhanden, sieht die Person erst ihn."""
        anderer = uuid.uuid4()
        commentary_service = self._dublette(anderer, autor="person-2")

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(trotz_dublette_von=str(uuid.uuid4())),
            headers=HEADERS,
        )

        assert resp.json()["id"] == str(anderer)
        assert resp.json()["dublette"] is True
        commentary_service.add_commentary.assert_not_awaited()

    def test_eigene_dublette_ohne_aussage_nennt_sich_eigen(self, dienste):
        self._dublette(uuid.uuid4())

        resp = TestClient(app).post(ADD_URL, json=_anfrage(), headers=HEADERS)

        assert resp.json()["dublette"] is True
        assert resp.json()["vorhanden_eigen"] is True


@pytest.mark.api
class TestThemenDerAussage:
    """
    Wer beim Speichern eine Aussage per Text anlegt, waehlt ihre Themen gleich mit
    (#455), nach derselben Regel wie beim Vorab-Anlegen: Eine vorhandene Aussage mit
    Themen behaelt ihre.
    """

    AUSSAGE = "Waermepumpen sind zu teuer"

    def test_neue_aussage_bekommt_die_gewaehlten_themen(self, dienste, themen_service):
        _, statement_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            self.AUSSAGE,
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text=self.AUSSAGE, themen=["energie-heizen"]),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["themen"] == [
            {"schluessel": "energie-heizen", "name": "Energie und Heizen"}
        ]
        assert resp.json()["verknuepft"] is True
        themen_service.ergaenzen.assert_awaited_once_with(
            statement_id, ["energie-heizen"]
        )

    def test_vorhandene_aussage_mit_themen_behaelt_ihre(self, dienste, themen_service):
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            vorhanden,
            "Waermepumpen sind viel zu teuer!",
        )
        themen_service.bestand[vorhanden] = ["klima"]

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text=self.AUSSAGE, themen=["soziales"]),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        # Die Antwort nennt ihre, damit das Formular sagen kann, dass die Wahl nicht galt.
        assert resp.json()["themen"] == [{"schluessel": "klima", "name": "Klima"}]
        themen_service.ergaenzen.assert_awaited_once_with(vorhanden, ["soziales"])

    def test_gewaehlte_aussage_bekommt_keine_themen(self, dienste, themen_service):
        _, statement_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            self.AUSSAGE,
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_id=str(statement_id), themen=["soziales"]),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["themen"] == []
        themen_service.ergaenzen.assert_not_called()

    def test_ohne_themen_wird_nichts_zugeordnet(self, dienste, themen_service):
        _, statement_service = dienste
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            uuid.uuid4(),
            self.AUSSAGE,
        )

        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(statement_text=self.AUSSAGE), headers=HEADERS
        )

        assert resp.status_code == 200
        assert resp.json()["themen"] == []
        themen_service.ergaenzen.assert_not_called()

    def test_gescheitertes_zuordnen_behaelt_kommentar_und_verknuepfung(
        self, dienste, themen_service
    ):
        commentary_id, statement_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            self.AUSSAGE,
        )
        themen_service.ergaenzen = AsyncMock(side_effect=RuntimeError("PostgreSQL weg"))

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text=self.AUSSAGE, themen=["soziales"]),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["themen"] == []
        assert resp.json()["id"] == str(commentary_id)
        assert resp.json()["statement_id"] == str(statement_id)
        assert resp.json()["verknuepft"] is True

    def test_fremde_dublette_bekommt_keine_themen(self, dienste, themen_service):
        commentary_service = app.dependency_overrides[get_commentary_service]()
        vorhanden = MagicMock(
            id=uuid.uuid4(), original_author="person-2", title=VORHANDEN_TITEL
        )
        commentary_service.pruefe_dublette = AsyncMock(
            return_value=Dublettenpruefung(vorhanden=vorhanden, aehnlichster=vorhanden)
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text=self.AUSSAGE, themen=["soziales"]),
            headers=HEADERS,
        )

        assert resp.json()["dublette"] is True
        themen_service.ergaenzen.assert_not_called()

    def test_vorhanden_nehmen_gibt_der_neuen_aussage_die_themen(
        self, dienste, themen_service
    ):
        _, statement_service = dienste
        vorhanden, statement_id = uuid.uuid4(), uuid.uuid4()
        TestAddCommentaryAntwort._dublette(vorhanden)
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            self.AUSSAGE,
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(
                statement_text=self.AUSSAGE,
                themen=["klima"],
                vorhanden_nehmen=str(vorhanden),
            ),
            headers=HEADERS,
        )

        assert resp.json()["verknuepft"] is True
        themen_service.ergaenzen.assert_awaited_once_with(statement_id, ["klima"])

    @pytest.mark.parametrize(
        "themen", [["heizungsgesetz"], ["klima", "verkehr", "europa"]]
    )
    def test_ungueltige_themen_werden_vor_dem_speichern_abgewiesen(
        self, dienste, themen
    ):
        commentary_service = app.dependency_overrides[get_commentary_service]()

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_text=self.AUSSAGE, themen=themen),
            headers=HEADERS,
        )

        assert resp.status_code == 422
        commentary_service.add_commentary.assert_not_awaited()
