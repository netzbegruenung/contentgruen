"""
GET /api/v1/linkvorschau/...: das Stueck HTML, das nginx fuer geteilte Links in
index.html einsetzt (#360). 200 mit og-Angaben fuer einen sichtbaren Beitrag, 204
fuer alles andere; nginx setzt dann die allgemeinen Angaben ein.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.linkvorschau import router as linkvorschau_router
from core.config import Settings
from dependencies import (
    get_beitrag_laden,
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_settings,
)
from domain.models.content import ContentDbEntry
from domain.models.content_type import ContentType
from services.beitrag_laden import BeitragUnlesbar
from services.content.base_content_service import BaseContentService
from tests.conftest import create_base_content_fields
from tests.unit.api.test_beitrag_responses import (
    AUTORIN,
    BEARBEITER,
    _bild,
    _hintergrundinfo,
    _kommentar,
    _post,
)

BEITRAG_ID = uuid.uuid4()
URL = f"/api/v1/linkvorschau/beitrag/{BEITRAG_ID}"


def _allgemein(content_type: ContentType) -> ContentDbEntry:
    return ContentDbEntry(
        **create_base_content_fields(),
        id=BEITRAG_ID,
        content_type=content_type,
        text="Inhalt",
    )


def _dienst(beitrag=None):
    dienst = MagicMock(spec=BaseContentService)
    dienst.get = AsyncMock(return_value=beitrag)
    return dienst


@pytest.fixture
def dienste():
    return {
        ContentType.COMMENTARY: _dienst(_kommentar(BEITRAG_ID)),
        ContentType.GENERIC_TEXT: _dienst(_hintergrundinfo(BEITRAG_ID)),
        ContentType.POST: _dienst(_post(BEITRAG_ID)),
        ContentType.IMAGE: _dienst(_bild(BEITRAG_ID)),
    }


@pytest.fixture
def laden():
    return AsyncMock(return_value=_allgemein(ContentType.COMMENTARY))


@pytest.fixture
def client(dienste, laden):
    app = FastAPI()
    app.include_router(linkvorschau_router, prefix="/api/v1/linkvorschau")
    app.dependency_overrides.update(
        {
            get_beitrag_laden: lambda: laden,
            get_commentary_service: lambda: dienste[ContentType.COMMENTARY],
            get_generic_text_service: lambda: dienste[ContentType.GENERIC_TEXT],
            get_post_service: lambda: dienste[ContentType.POST],
            get_image_service: lambda: dienste[ContentType.IMAGE],
            get_settings: lambda: Settings(app_url="https://gutgesagt.example/"),
        }
    )
    return TestClient(app)


def test_sichtbarer_kommentar(client):
    antwort = client.get(URL)
    assert antwort.status_code == 200
    assert antwort.headers["content-type"] == "text/html; charset=utf-8"
    assert antwort.text == (
        '<meta property="og:title" content="Wärmepumpe lohnt sich auch im Altbau">\n'
        '<meta property="og:description" content="Kommentartext">\n'
        '<meta name="twitter:description" content="Kommentartext">\n'
        f'<meta property="og:url" content="https://gutgesagt.example/beitrag/{BEITRAG_ID}">\n'
    )


@pytest.mark.parametrize(
    ("typ", "titel"),
    [
        (ContentType.GENERIC_TEXT, "Wärmepumpen sparen im Schnitt die Hälfte"),
        (ContentType.POST, "Unser Solarpark ist am Netz"),
        (ContentType.IMAGE, "Solardach auf der Schule"),
    ],
)
def test_jeder_beitragstyp(client, laden, typ, titel):
    laden.return_value = _allgemein(typ)
    antwort = client.get(URL)
    assert antwort.status_code == 200
    assert titel in antwort.text


def test_keine_angaben_zur_person(client, laden, dienste):
    for typ in dienste:
        laden.return_value = _allgemein(typ)
        text = client.get(URL).text
        for person in (AUTORIN, BEARBEITER, "@buergerenergie"):
            assert person not in text, (typ, person)


def test_gesperrt_geloescht_oder_unbekannt_204(client, laden):
    # Das Repository liefert fuer alle drei "nicht da" (beitrag_laden: None).
    laden.return_value = None
    antwort = client.get(URL)
    assert antwort.status_code == 204
    assert antwort.content == b""


def test_zwischen_den_lesungen_gesperrt_204(client, dienste):
    dienste[ContentType.COMMENTARY].get.side_effect = ValueError("gesperrt")
    assert client.get(URL).status_code == 204


def test_aussage_hat_keine_vorschau(client, laden):
    laden.return_value = _allgemein(ContentType.STATEMENT)
    assert client.get(URL).status_code == 204


@pytest.mark.parametrize(
    "fehler", [BeitragUnlesbar("x"), RuntimeError("Qdrant weg"), TimeoutError()]
)
def test_fehler_beim_laden_204(client, laden, fehler):
    laden.side_effect = fehler
    assert client.get(URL).status_code == 204


def test_bildindex_nicht_bereit_204(client, laden, dienste):
    laden.return_value = _allgemein(ContentType.IMAGE)
    client.app.dependency_overrides[get_image_service] = lambda: None
    assert client.get(URL).status_code == 204


def test_titel_maskiert(client, dienste):
    dienste[ContentType.COMMENTARY].get.return_value = _kommentar(
        BEITRAG_ID
    ).model_copy(update={"title": '"><script>alert(1)</script>'})
    text = client.get(URL).text
    assert "<script>" not in text
    assert 'content="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"' in text


def test_ergebnis_aus_header(client):
    antwort = client.get(
        "/api/v1/linkvorschau/ergebnis",
        headers={"X-Suchtext": "W%C3%A4rmepumpe%20%22im%22%20Altbau"},
    )
    assert antwort.status_code == 200
    assert (
        '<meta property="og:title" content="Antworten auf: Wärmepumpe &quot;im&quot; Altbau">'
        in antwort.text
    )
    assert "og:url" not in antwort.text


def test_ergebnis_ohne_suchtext_204(client):
    assert client.get("/api/v1/linkvorschau/ergebnis").status_code == 204
    assert (
        client.get(
            "/api/v1/linkvorschau/ergebnis", headers={"X-Suchtext": ""}
        ).status_code
        == 204
    )
