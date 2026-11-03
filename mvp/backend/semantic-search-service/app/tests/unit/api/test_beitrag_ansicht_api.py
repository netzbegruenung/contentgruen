"""
GET /api/v1/content/beitrag/{id}: ein Beitrag unter seiner eigenen Adresse (#300).

Die Seite /beitrag/:id kennt nur die ID. Der Endpunkt sucht den Typ selbst und
liefert den Beitrag in der Antwort seines Typs, wie getById des Typs. Gesperrt,
geloescht oder nie vorhanden ist fuer jeden Leser 404 (GLOSSARY.md: Gesperrtes
finden Admins ueber die Moderation, nicht ueber die Ansicht). Aussage und Herkunft
sind keine Beitraege und haben hier keine Adresse.

Was Nicht-Admins zur Person sehen, prueft test_beitrag_responses.py mit allen
lesenden Routen.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.content import router as content_router
from dependencies import (
    get_beitrag_laden,
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_reference_service,
)
from domain.models.content import ContentDbEntry
from domain.models.content_type import ContentType
from services.beitrag_laden import BeitragUnlesbar
from services.content.base_content_service import BaseContentService
from tests.conftest import create_base_content_fields
from tests.unit.api.test_beitrag_responses import (
    _bild,
    _hintergrundinfo,
    _kommentar,
    _post,
)

BEITRAG_ID = uuid.uuid4()
URL = f"/api/v1/content/beitrag/{BEITRAG_ID}"


def _allgemein(content_type: ContentType) -> ContentDbEntry:
    """Was das aggregierte Repository liefert: nur die allgemeinen Felder samt Typ."""
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
def client(dienste, laden, herkunft, nutzung):
    app = FastAPI()
    app.include_router(content_router, prefix="/api/v1/content")
    app.dependency_overrides.update(
        {
            get_beitrag_laden: lambda: laden,
            get_commentary_service: lambda: dienste[ContentType.COMMENTARY],
            get_generic_text_service: lambda: dienste[ContentType.GENERIC_TEXT],
            get_post_service: lambda: dienste[ContentType.POST],
            get_image_service: lambda: dienste[ContentType.IMAGE],
            get_reference_service: lambda: herkunft,
        }
    )
    with patch("api.v1.content.get_usage_service", return_value=nutzung):
        yield TestClient(app)


@pytest.fixture
def herkunft():
    dienst = MagicMock()
    dienst.herkunft_ergaenzen = AsyncMock()
    return dienst


@pytest.fixture
def nutzung():
    dienst = MagicMock()
    dienst.enrich_content_with_usage.side_effect = lambda eintraege: [
        {**e, "usage_count": 7} for e in eintraege
    ]
    return dienst


@pytest.mark.unit
class TestBeitragAnsicht:
    @pytest.mark.parametrize(
        "typ, typfeld",
        [
            (ContentType.COMMENTARY, "long_text"),
            (ContentType.GENERIC_TEXT, "title"),
            (ContentType.POST, "platform"),
            (ContentType.IMAGE, "image_url"),
        ],
    )
    def test_jeder_beitragstyp_mit_seinen_feldern(
        self, client, dienste, laden, typ, typfeld
    ):
        laden.return_value = _allgemein(typ)

        antwort = client.get(URL)

        assert antwort.status_code == 200, antwort.text
        body = antwort.json()
        assert body["id"] == str(BEITRAG_ID)
        assert body["content_type"] == typ.value
        assert body[typfeld]
        dienste[typ].get.assert_awaited_once_with(BEITRAG_ID)

    def test_mit_herkunft_und_nutzung_wie_in_der_suche(self, client, herkunft):
        body = client.get(URL).json()

        assert body["usage_count"] == 7
        herkunft.herkunft_ergaenzen.assert_awaited_once()

    def test_nicht_da_ist_404(self, client, laden):
        # beitrag_laden: gesperrt, geloescht und nie vorhanden heissen None.
        laden.return_value = None

        assert client.get(URL).status_code == 404

    def test_gesperrt_auch_fuer_admins_404(self, client, laden):
        laden.return_value = None

        antwort = client.get(URL, headers={"X-User": "admin-1", "X-Is-Admin": "true"})

        assert antwort.status_code == 404

    @pytest.mark.parametrize("typ", [ContentType.STATEMENT, ContentType.REFERENCE])
    def test_aussage_und_herkunft_sind_keine_beitraege(
        self, client, dienste, laden, typ
    ):
        laden.return_value = _allgemein(typ)

        assert client.get(URL).status_code == 404
        for dienst in dienste.values():
            dienst.get.assert_not_awaited()

    def test_zwischen_den_lesungen_ausgeblendet_ist_404(self, client, dienste, laden):
        # Das Typ-Repository meldet "nicht da" als ValueError (base_repository.get).
        dienste[ContentType.COMMENTARY].get.side_effect = ValueError("ausgeblendet")

        assert client.get(URL).status_code == 404

    def test_unlesbarer_datensatz_ist_500(self, client, laden):
        laden.side_effect = BeitragUnlesbar(str(BEITRAG_ID))

        assert client.get(URL).status_code == 500

    def test_kaputter_datensatz_im_typ_repository_ist_500(self, client, dienste):
        # Pydantics ValidationError ist ein ValueError, aber kein "nicht da".
        try:
            ContentDbEntry.model_validate({})
        except ValueError as fehler:
            dienste[ContentType.COMMENTARY].get.side_effect = fehler

        assert client.get(URL).status_code == 500

    def test_keine_uuid_ist_422(self, client):
        assert client.get("/api/v1/content/beitrag/kein-beitrag").status_code == 422
