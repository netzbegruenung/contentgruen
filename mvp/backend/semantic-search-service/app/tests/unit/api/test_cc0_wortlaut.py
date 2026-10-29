"""
Die Kennung des CC0-Hinweises (#431): Jeder Speicherweg fuer Beitrag, Satz und
Einwurf nimmt sie an und reicht sie bis zum gespeicherten Eintrag durch. Ohne
Kennung (aeltere App) wird ohne gespeichert, eine unbekannte abgewiesen.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from api.v1.commentary import router as commentary_router
from api.v1.generic_text import router as generic_text_router
from api.v1.image import router as image_router
from api.v1.post import router as post_router
from api.v1.raw_input import router as raw_input_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_reference_service,
    get_statement_service,
)
from domain.models.raw_input import RawInputSource, RawInputStatus
from repositories.raw_input_repository import get_raw_input_repository
from services.content.base_content_service import Dublettenpruefung
from utils.text_normalisierung import SperreJeText

FORMULAR = "2026-10-29-formular"
SATZ = "2026-10-29-satz"
HEADERS = {"X-User": "person-1"}
EINWURF_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")

app = FastAPI()
app.include_router(commentary_router, prefix="/api/v1/commentary")
app.include_router(generic_text_router, prefix="/api/v1/generictext")
app.include_router(image_router, prefix="/api/v1/image")
app.include_router(post_router, prefix="/api/v1/post")
app.include_router(raw_input_router, prefix="/api/v1/rawinput")


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _ohne_dublette(service, methode: str):
    setattr(service, methode, AsyncMock(return_value=(True, uuid.uuid4(), "text")))
    service.pruefe_dublette = AsyncMock(
        return_value=Dublettenpruefung(vorhanden=None, aehnlichster=None)
    )
    service.sperre = lambda text: SperreJeText().halten(text)
    return service


def _herkunft_und_aussage():
    reference_service = MagicMock()
    reference_service.find_exact_match = AsyncMock(return_value=None)
    reference_service.add_reference = AsyncMock(
        return_value=(uuid.uuid4(), True, "neu")
    )
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_statement_service] = lambda: MagicMock()


@pytest.fixture
def kommentar_dienst():
    service = _ohne_dublette(MagicMock(), "add_commentary")
    app.dependency_overrides[get_commentary_service] = lambda: service
    _herkunft_und_aussage()
    return service


@pytest.fixture
def hintergrundinfo_dienst():
    service = _ohne_dublette(MagicMock(), "add_generic_text")
    app.dependency_overrides[get_generic_text_service] = lambda: service
    _herkunft_und_aussage()
    return service


@pytest.fixture
def typ_dienst():
    """Bild und Post laufen ueber den generischen Dienst: add(entry)."""
    service = MagicMock()
    service.add = AsyncMock(side_effect=lambda entry: entry.id)
    app.dependency_overrides[get_image_service] = lambda: service
    app.dependency_overrides[get_post_service] = lambda: service
    return service


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.create.return_value = {
        "id": str(uuid.uuid4()),
        "content": "ein Satz",
        "url": None,
        "image_url": None,
        "submitted_by": "person-1",
        "source_channel": RawInputSource.WEB.value,
        "status": RawInputStatus.OPEN.value,
        "created_at": datetime(2026, 10, 29, tzinfo=timezone.utc),
    }
    repo.save_draft.side_effect = lambda id, person, satz, **_: {
        "raw_input_id": str(id),
        "sentence": satz,
        "updated_at": None,
    }
    app.dependency_overrides[get_raw_input_repository] = lambda: repo
    return repo


def _kommentar(**extra) -> dict:
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


def _hintergrundinfo(**extra) -> dict:
    return {
        "generictext": {
            "title": "Waermepumpen sparen im Altbau Heizkosten",
            "text": "Laut Feldtest liegt die Jahresarbeitszahl im Altbau bei 3,4.",
            "content_type": "generic_text",
            "references": [],
        },
        "references": [],
        **extra,
    }


def _bild(**extra) -> dict:
    return {
        "image": {
            "title": "Klimademo Berlin",
            "image_url": "https://example.com/demo.jpg",
            "text": "Tausende Menschen demonstrieren in Berlin fuer Klimaschutz",
        },
        **extra,
    }


def _post(**extra) -> dict:
    return {
        "post": {
            "title": "Verkehrswende jetzt",
            "text": "Busse und Bahnen ausbauen, statt Strassen zu verbreitern.",
            "content_type": "post",
            "platform": "mastodon",
            "author": "@gruen",
        },
        **extra,
    }


@pytest.mark.api
class TestBeitraege:
    def test_kommentar_reicht_die_kennung_durch(self, client, kommentar_dienst):
        resp = client.post(
            "/api/v1/commentary/addCommentary",
            json=_kommentar(cc0_wortlaut=FORMULAR),
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        kwargs = kommentar_dienst.add_commentary.await_args.kwargs
        assert kwargs["cc0_wortlaut"] == FORMULAR

    def test_hintergrundinfo_reicht_die_kennung_durch(
        self, client, hintergrundinfo_dienst
    ):
        resp = client.post(
            "/api/v1/generictext/addGenericText",
            json=_hintergrundinfo(cc0_wortlaut=FORMULAR),
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        kwargs = hintergrundinfo_dienst.add_generic_text.await_args.kwargs
        assert kwargs["cc0_wortlaut"] == FORMULAR

    def test_bild_speichert_die_kennung_am_eintrag(self, client, typ_dienst):
        resp = client.post(
            "/api/v1/image/addImage", json=_bild(cc0_wortlaut=FORMULAR), headers=HEADERS
        )

        assert resp.status_code == 201, resp.text
        assert typ_dienst.add.await_args.args[0].cc0_wortlaut == FORMULAR

    def test_post_speichert_die_kennung_am_eintrag(self, client, typ_dienst):
        resp = client.post(
            "/api/v1/post/addPost", json=_post(cc0_wortlaut=FORMULAR), headers=HEADERS
        )

        assert resp.status_code == 200, resp.text
        assert typ_dienst.add.await_args.args[0].cc0_wortlaut == FORMULAR

    def test_ohne_kennung_wird_ohne_gespeichert(self, client, typ_dienst):
        resp = client.post("/api/v1/post/addPost", json=_post(), headers=HEADERS)

        assert resp.status_code == 200, resp.text
        assert typ_dienst.add.await_args.args[0].cc0_wortlaut is None

    @pytest.mark.parametrize(
        "url, anfrage",
        [
            ("/api/v1/commentary/addCommentary", _kommentar),
            ("/api/v1/generictext/addGenericText", _hintergrundinfo),
            ("/api/v1/image/addImage", _bild),
            ("/api/v1/post/addPost", _post),
        ],
    )
    def test_unbekannte_kennung_wird_abgewiesen(
        self,
        client,
        kommentar_dienst,
        hintergrundinfo_dienst,
        typ_dienst,
        url,
        anfrage,
    ):
        resp = client.post(url, json=anfrage(cc0_wortlaut="erfunden"), headers=HEADERS)

        assert resp.status_code == 422
        kommentar_dienst.add_commentary.assert_not_awaited()
        hintergrundinfo_dienst.add_generic_text.assert_not_awaited()
        typ_dienst.add.assert_not_awaited()


@pytest.mark.api
class TestEinwurfUndSatz:
    def test_einwurf_reicht_die_kennung_durch(self, client, repository):
        resp = client.post(
            "/api/v1/rawinput/addRawInput",
            json={"content": "ein Satz", "cc0_wortlaut": FORMULAR},
            headers=HEADERS,
        )

        assert resp.status_code == 201, resp.text
        assert repository.create.call_args.kwargs["cc0_wortlaut"] == FORMULAR

    def test_einwurf_ohne_kennung(self, client, repository):
        resp = client.post(
            "/api/v1/rawinput/addRawInput",
            json={"content": "ein Satz"},
            headers=HEADERS,
        )

        assert resp.status_code == 201, resp.text
        assert repository.create.call_args.kwargs["cc0_wortlaut"] is None

    def test_satz_reicht_die_kennung_durch(self, client, repository):
        resp = client.put(
            f"/api/v1/rawinput/{EINWURF_ID}/draft",
            json={
                "sentence": "Waermepumpe lohnt sich auch im Altbau",
                "cc0_wortlaut": SATZ,
            },
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        assert repository.save_draft.call_args.kwargs["cc0_wortlaut"] == SATZ

    @pytest.mark.parametrize(
        "methode, url, body",
        [
            ("post", "/api/v1/rawinput/addRawInput", {"content": "ein Satz"}),
            ("put", f"/api/v1/rawinput/{EINWURF_ID}/draft", {"sentence": "Ein Satz"}),
        ],
    )
    def test_unbekannte_kennung_wird_abgewiesen(
        self, client, repository, methode, url, body
    ):
        resp = getattr(client, methode)(
            url, json={**body, "cc0_wortlaut": "erfunden"}, headers=HEADERS
        )

        assert resp.status_code == 422
        repository.create.assert_not_called()
        repository.save_draft.assert_not_called()
