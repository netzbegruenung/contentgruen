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
    get_commentary_service,
    get_reference_service,
    get_statement_service,
)
from domain.models.content_type import ContentType

ADD_URL = "/api/v1/commentary/addCommentary"
HEADERS = {"X-User": "person-1"}

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
def dienste():
    commentary_id = uuid.uuid4()
    commentary_service = MagicMock()
    commentary_service.add_commentary = AsyncMock(
        return_value=(True, commentary_id, "text")
    )
    commentary_service.finde_dublette = AsyncMock(return_value=None)
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
            "duplikat": False,
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
            "duplikat": False,
        }

    def test_dublette_legt_keine_herkunftsangaben_an(self, dienste):
        """Die Pruefung laeuft vor den Referenzen - sonst blieben sie verwaist."""
        _, statement_service = dienste
        vorhanden = uuid.uuid4()
        commentary_service = app.dependency_overrides[get_commentary_service]()
        reference_service = app.dependency_overrides[get_reference_service]()
        commentary_service.finde_dublette.return_value = MagicMock(id=vorhanden)
        anfrage = _anfrage(statement_id=str(uuid.uuid4()))
        anfrage["references"] = [
            {"reference_string": "https://example.org/studie", "description": "Studie"}
        ]

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["id"] == str(vorhanden)
        assert resp.json()["duplikat"] is True
        commentary_service.finde_dublette.assert_awaited_once_with(
            anfrage["commentary"]["text"]
        )
        reference_service.find_exact_match.assert_not_awaited()
        reference_service.add_reference.assert_not_awaited()
        commentary_service.add_commentary.assert_not_awaited()
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_ohne_dublette_werden_herkunftsangaben_angelegt(self, dienste):
        reference_service = app.dependency_overrides[get_reference_service]()
        anfrage = _anfrage()
        anfrage["references"] = [
            {"reference_string": "https://example.org/studie", "description": "Studie"}
        ]

        resp = TestClient(app).post(ADD_URL, json=anfrage, headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["duplikat"] is False
        reference_service.add_reference.assert_awaited_once()

    def test_parallel_gespeicherte_dublette_wird_gemeldet_und_nicht_verknuepft(
        self, dienste
    ):
        commentary_id, statement_service = dienste
        vorhanden = uuid.uuid4()
        # Die Vorpruefung fand nichts, add_commentary meldet unter dem Anlegen doch
        # eine Dublette (derselbe Kommentar wurde gleichzeitig gespeichert).
        app.dependency_overrides[
            get_commentary_service
        ]().add_commentary.return_value = (
            False,
            vorhanden,
            "text",
        )

        resp = TestClient(app).post(
            ADD_URL,
            json=_anfrage(statement_id=str(uuid.uuid4())),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(vorhanden),
            "statement_id": None,
            "statement_text": None,
            "verknuepft": True,
            "duplikat": True,
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

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
