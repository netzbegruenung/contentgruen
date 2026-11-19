"""
/post/addPost und /image/addImage mit Aussage (#619): Post oder Bild speichern und im
selben Aufruf als Antwort verknuepfen, wie Kommentar und Hintergrundinfo. Scheitert
die Verknuepfung, bleibt der Beitrag gespeichert und die Antwort sagt es
(verknuepft=false).
"""

import logging
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.image import BILD_RELEVANZ, router as image_router
from api.v1.post import POST_RELEVANZ, router as post_router
from dependencies import (
    get_aussage_themen_service,
    get_image_service,
    get_post_service,
    get_statement_service,
)
from domain.models.content_type import ContentType
from services.content.statement_service import AussageNichtGefunden

HEADERS = {"X-User": "person-1"}

app = FastAPI()
app.include_router(image_router, prefix="/api/v1/image")
app.include_router(post_router, prefix="/api/v1/post")


def _bild(**extra) -> dict:
    return {
        "image": {
            "title": "Solardach auf der Grundschule",
            "image_url": "https://example.com/dach.jpg",
            "text": "Die Stadt hat alle Schuldaecher mit Solarmodulen belegt.",
        },
        **extra,
    }


def _post(**extra) -> dict:
    return {
        "post": {
            "title": "So erklaert man das Heizungsgesetz",
            "text": "Ein kurzer Post, der die Foerderung in drei Saetzen erklaert.",
            "platform": "Instagram",
            "author": "@gruene",
            "url": "https://www.instagram.com/p/abc",
        },
        **extra,
    }


# (URL, Anfrage, erwarteter Status, Typ, Relevanz)
ARTEN = [
    pytest.param(
        "/api/v1/image/addImage",
        _bild,
        201,
        ContentType.IMAGE,
        BILD_RELEVANZ,
        id="bild",
    ),
    pytest.param(
        "/api/v1/post/addPost", _post, 200, ContentType.POST, POST_RELEVANZ, id="post"
    ),
]


@pytest.fixture
def dienste():
    typ_dienst = MagicMock()
    typ_dienst.add = AsyncMock(side_effect=lambda entry: entry.id)
    statement_service = MagicMock()
    statement_service.beitrag_als_antwort_verknuepfen = AsyncMock()
    themen_service = MagicMock()
    themen_service.ergaenzen = AsyncMock(
        side_effect=lambda statement_id, themen: themen
    )
    app.dependency_overrides[get_image_service] = lambda: typ_dienst
    app.dependency_overrides[get_post_service] = lambda: typ_dienst
    app.dependency_overrides[get_statement_service] = lambda: statement_service
    app.dependency_overrides[get_aussage_themen_service] = lambda: themen_service
    yield typ_dienst, statement_service, themen_service
    app.dependency_overrides.clear()


def _gespeichert_id(typ_dienst) -> uuid.UUID:
    return typ_dienst.add.await_args.args[0].id


@pytest.mark.api
@pytest.mark.parametrize("url, anfrage, status, typ, relevanz", ARTEN)
class TestAntwortAuf:
    def test_ohne_aussage_wird_nichts_verknuepft(
        self, dienste, url, anfrage, status, typ, relevanz
    ):
        typ_dienst, statement_service, _ = dienste

        resp = TestClient(app).post(url, json=anfrage(), headers=HEADERS)

        assert resp.status_code == status, resp.text
        assert resp.json() == {
            "id": str(_gespeichert_id(typ_dienst)),
            "statement_id": None,
            "statement_text": None,
            "themen": [],
            "verknuepft": True,
        }
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_mit_aussage_id_wird_verknuepft(
        self, dienste, url, anfrage, status, typ, relevanz
    ):
        typ_dienst, statement_service, themen_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Solar lohnt sich nicht",
            False,
        )

        resp = TestClient(app).post(
            url,
            json=anfrage(statement_id=str(statement_id), themen=["energie-heizen"]),
            headers=HEADERS,
        )

        assert resp.status_code == status, resp.text
        assert resp.json()["statement_id"] == str(statement_id)
        assert resp.json()["statement_text"] == "Solar lohnt sich nicht"
        assert resp.json()["verknuepft"] is True
        statement_service.beitrag_als_antwort_verknuepfen.assert_awaited_once_with(
            beitrag_id=_gespeichert_id(typ_dienst),
            content_type=typ,
            relevance=relevanz,
            author="person-1",
            statement_id=statement_id,
            statement_text=None,
        )
        # Themen gelten nur fuer eine Aussage per Text.
        themen_service.ergaenzen.assert_not_awaited()
        assert resp.json()["themen"] == []

    def test_mit_aussagetext_wird_gesucht_oder_angelegt_samt_themen(
        self, dienste, url, anfrage, status, typ, relevanz
    ):
        _, statement_service, themen_service = dienste
        statement_id = uuid.uuid4()
        statement_service.beitrag_als_antwort_verknuepfen.return_value = (
            statement_id,
            "Solar lohnt sich doch nicht!",
            False,
        )

        resp = TestClient(app).post(
            url,
            json=anfrage(
                statement_text="Solar lohnt sich nicht", themen=["energie-heizen"]
            ),
            headers=HEADERS,
        )

        assert resp.status_code == status, resp.text
        assert resp.json()["statement_text"] == "Solar lohnt sich doch nicht!"
        aufruf = statement_service.beitrag_als_antwort_verknuepfen.call_args.kwargs
        assert aufruf["statement_text"] == "Solar lohnt sich nicht"
        assert aufruf["statement_id"] is None
        themen_service.ergaenzen.assert_awaited_once_with(
            statement_id, ["energie-heizen"]
        )
        assert [t["schluessel"] for t in resp.json()["themen"]] == ["energie-heizen"]

    def test_aussagetext_unter_10_zeichen_wird_abgelehnt(
        self, dienste, url, anfrage, status, typ, relevanz
    ):
        typ_dienst, _, _ = dienste

        resp = TestClient(app).post(
            url, json=anfrage(statement_text="zu kurz"), headers=HEADERS
        )

        assert resp.status_code == 422
        typ_dienst.add.assert_not_awaited()

    def test_leerer_aussagetext_zaehlt_als_ohne_aussage(
        self, dienste, url, anfrage, status, typ, relevanz
    ):
        _, statement_service, _ = dienste

        resp = TestClient(app).post(
            url, json=anfrage(statement_text="   "), headers=HEADERS
        )

        assert resp.status_code == status, resp.text
        statement_service.beitrag_als_antwort_verknuepfen.assert_not_awaited()

    def test_verschwundene_aussage_ist_warning_ohne_traceback(
        self, dienste, caplog, url, anfrage, status, typ, relevanz
    ):
        typ_dienst, statement_service, _ = dienste
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = (
            AussageNichtGefunden("weg")
        )

        with caplog.at_level(logging.WARNING):
            resp = TestClient(app).post(
                url, json=anfrage(statement_id=str(uuid.uuid4())), headers=HEADERS
            )

        assert resp.status_code == status, resp.text
        assert resp.json()["id"] == str(_gespeichert_id(typ_dienst))
        assert resp.json()["verknuepft"] is False
        eintraege = [r for r in caplog.records if "statement" in r.getMessage()]
        assert eintraege and all(r.levelno == logging.WARNING for r in eintraege)
        assert all(r.exc_info is None for r in eintraege)

    def test_anderer_fehler_behaelt_den_beitrag_und_loggt_mit_traceback(
        self, dienste, caplog, url, anfrage, status, typ, relevanz
    ):
        typ_dienst, statement_service, _ = dienste
        statement_service.beitrag_als_antwort_verknuepfen.side_effect = RuntimeError(
            "Qdrant weg"
        )

        with caplog.at_level(logging.WARNING):
            resp = TestClient(app).post(
                url, json=anfrage(statement_id=str(uuid.uuid4())), headers=HEADERS
            )

        assert resp.status_code == status, resp.text
        assert resp.json() == {
            "id": str(_gespeichert_id(typ_dienst)),
            "statement_id": None,
            "statement_text": None,
            "themen": [],
            "verknuepft": False,
        }
        fehler = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert fehler and fehler[0].exc_info is not None
