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
    statement_service = MagicMock()
    statement_service.beitrag_als_antwort_verknuepfen = AsyncMock()

    app.dependency_overrides[get_commentary_service] = lambda: commentary_service
    app.dependency_overrides[get_reference_service] = lambda: MagicMock()
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

    def test_dublette_wird_gemeldet_und_nicht_verknuepft(self, dienste):
        commentary_id, statement_service = dienste
        vorhanden = uuid.uuid4()
        # add_commentary meldet: nichts angelegt, ein sehr aehnlicher existiert schon.
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
