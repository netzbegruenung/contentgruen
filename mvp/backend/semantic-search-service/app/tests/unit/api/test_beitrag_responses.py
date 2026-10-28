"""
Suche und lesende Beitragsrouten liefern keine Kennung anderer Personen (#333).

Die Kennung ist personenbezogen (GLOSSARY.md). Nicht-Admins bekommen statt
``original_author`` den Anzeigenamen und ``ist_eigener_beitrag``, beides nur
angemeldet; Admins sehen die Kennung weiter. Geprueft je Beitragstyp an jeder
lesenden Route: Die Kennung der Autorin darf nirgends in der Antwort stehen,
auch nicht in ``last_modified_by``, ``authors`` oder ``edit_history``.
"""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import router as commentary_router
from api.v1.content import router as content_router
from api.v1.generic_text import router as generic_text_router
from api.v1.image import router as image_router
from api.v1.post import router as post_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_reference_service,
    get_settings,
)
from domain.models.author_entry import AuthorEntry
from domain.models.base_content import BaseContentDbEntry
from domain.models.commentary import CommentaryDbEntry, CommentarySearchResult
from domain.models.content import ContentDbEntry, ContentSearchResult
from domain.models.content_type import ContentType
from domain.models.edit_entry import EditEntry
from domain.models.generic_text import GenericTextDbEntry, GenericTextSearchResult
from domain.models.image import ImageDbEntry
from domain.models.post import PostDbEntry, PostSearchResult
from dtos.beitrag import BeitragResponse, KommentarResponse
from services.beitrag_fuer_aufrufer import Aufrufer, als_responses
from services.content.base_content_service import BaseContentService
from tests.conftest import create_base_content_fields
from tests.unit.api.test_search_ranking import (  # noqa: F401 - Fixture
    SEARCH_URL,
    _reply,
    _statement_result,
    app as such_app,
    search_client,
)

AUTORIN = "kennung-der-autorin"
BEARBEITER = "kennung-des-bearbeiters"
LESERIN = "kennung-der-leserin"
NAME = "Anna B."

FREMD = {"X-User": LESERIN}
EIGEN = {"X-User": AUTORIN}
ADMIN = {"X-User": LESERIN, "X-Is-Admin": "true"}
ANONYM = {"X-User": "anonymous"}


def _personen():
    """Was am DbEntry eine Person bezeichnet, ueberall mit einer Kennung belegt."""
    return create_base_content_fields(
        original_author=AUTORIN,
        last_modified_by=BEARBEITER,
        authors=[AuthorEntry(name=AUTORIN, role="author")],
        edit_history=[
            EditEntry(
                editor=BEARBEITER,
                action="edit",
                timestamp=datetime.datetime(2026, 10, 27),
            )
        ],
    )


def _kommentar(cid=None, klasse=CommentaryDbEntry, **extra):
    return klasse(
        **_personen(),
        **extra,
        id=cid or uuid.uuid4(),
        content_type=ContentType.COMMENTARY,
        title="Wärmepumpe lohnt sich auch im Altbau",
        text="Kommentartext",
        short_text="kurz",
        long_text="lang",
        style="sachlich",
        references=[],
        references_count=0,
    )


def _hintergrundinfo(gid=None, klasse=GenericTextDbEntry, **extra):
    return klasse(
        **_personen(),
        **extra,
        id=gid or uuid.uuid4(),
        content_type=ContentType.GENERIC_TEXT,
        title="Wärmepumpen sparen im Schnitt die Hälfte der Heizkosten",
        text="Hintergrundinfotext",
        references=[],
        references_count=0,
    )


def _post(pid=None, klasse=PostDbEntry, **extra):
    return klasse(
        **_personen(),
        **extra,
        id=pid or uuid.uuid4(),
        content_type=ContentType.POST,
        title="Unser Solarpark ist am Netz",
        text="Posttext",
        platform="mastodon",
        author="@buergerenergie",
    )


def _bild(bid=None):
    return ImageDbEntry(
        **_personen(),
        id=bid or uuid.uuid4(),
        content_type=ContentType.IMAGE,
        title="Solardach auf der Schule",
        image_url="https://example.org/solar.jpg",
        text="Ein Solardach auf einer Grundschule",
    )


def _inhalt(cid=None, klasse=ContentDbEntry, **extra):
    return klasse(
        **_personen(),
        **extra,
        id=cid or uuid.uuid4(),
        content_type=ContentType.COMMENTARY,
        text="Inhalt",
    )


# Was der DbEntry fuehrt, die allgemeine Auswahl aber nicht: Bearbeitung,
# Moderation, Dublettenpruefung. Aus dem Modell abgeleitet, damit ein neues Feld am
# DbEntry hier auffaellt, bis jemand es bewusst in dtos/beitrag.py aufnimmt.
NICHT_NACH_AUSSEN = set(BaseContentDbEntry.model_fields) - set(
    BeitragResponse.model_fields
)


def _ohne_kennung(antwort):
    assert AUTORIN not in antwort.text
    assert BEARBEITER not in antwort.text
    for eintrag in _eintraege(antwort.json()):
        assert not NICHT_NACH_AUSSEN & set(eintrag), eintrag.get("content_type")


TREFFERLISTEN = (
    "commentary_search_results",
    "generictext_search_results",
    "post_search_results",
    "image_search_results",
)


def _eintraege(body):
    """Jeder Beitrag einer Antwort, egal wie die Route ihn verpackt."""
    if "commentary_search_results" in body:
        return [
            treffer[feld.replace("_search_results", "_result")]
            for feld in TREFFERLISTEN
            for treffer in body[feld]
        ]
    if "results" in body:
        return body["results"]
    return [body]


# --------------------------------------------------------------------------- #
# Lesende Routen je Beitragstyp
# --------------------------------------------------------------------------- #

lese_app = FastAPI()
lese_app.include_router(commentary_router, prefix="/api/v1/commentary")
lese_app.include_router(generic_text_router, prefix="/api/v1/generic_text")
lese_app.include_router(post_router, prefix="/api/v1/post")
lese_app.include_router(image_router, prefix="/api/v1/image")
lese_app.include_router(content_router, prefix="/api/v1/content")

GET = "get"
POST = "post"
ID = str(uuid.uuid4())
SUCHE = {"query_text": "Wärmepumpe", "limit": 3}

# (Methode, URL) - jede lesende Route, die Beitraege ausliefert; POST schickt SUCHE.
ROUTEN = {
    "commentary/getById": (GET, f"/api/v1/commentary/getById?commentary_id={ID}"),
    "commentary/searchCommentaries": (POST, "/api/v1/commentary/searchCommentaries"),
    "generic_text/getById": (
        GET,
        f"/api/v1/generic_text/getById?generic_text_id={ID}",
    ),
    "generic_text/getAll": (GET, "/api/v1/generic_text/getAll"),
    "generic_text/searchGenericText": (POST, "/api/v1/generic_text/searchGenericText"),
    "post/getById": (GET, f"/api/v1/post/getById?post_id={ID}"),
    "post/getAll": (GET, "/api/v1/post/getAll"),
    "post/searchPost": (POST, "/api/v1/post/searchPost"),
    "image/getById": (GET, f"/api/v1/image/getById?image_id={ID}"),
    "image/getAll": (GET, "/api/v1/image/getAll"),
    "content/recent": (GET, "/api/v1/content/recent"),
    "content/getAll": (GET, "/api/v1/content/getAll"),
    "content/searchContent": (POST, "/api/v1/content/searchContent"),
}


def _dienst(einzeln, treffer_klasse):
    dienst = MagicMock(spec=BaseContentService)
    dienst.get = AsyncMock(side_effect=lambda i: einzeln(i))
    dienst.get_all = AsyncMock(side_effect=lambda **_: [einzeln(), einzeln()])
    dienst.count = AsyncMock(return_value=2)
    dienst.search = AsyncMock(
        side_effect=lambda *_: [einzeln(klasse=treffer_klasse, score=0.9)]
    )
    return dienst


@pytest.fixture
def lese_client(anzeigenamen_ohne_datenbank):
    anzeigenamen_ohne_datenbank.anzeigenamen.side_effect = lambda ids: {
        k: NAME for k in ids if k == AUTORIN
    }
    lese_app.dependency_overrides.update(
        {
            get_commentary_service: lambda: _dienst(_kommentar, CommentarySearchResult),
            get_generic_text_service: lambda: _dienst(
                _hintergrundinfo, GenericTextSearchResult
            ),
            get_post_service: lambda: _dienst(_post, PostSearchResult),
            get_image_service: lambda: _dienst(
                lambda i=None, **_: _bild(i), ImageDbEntry
            ),
            get_settings: lambda: MagicMock(),
            get_reference_service: lambda: MagicMock(),
        }
    )
    factory = MagicMock()
    factory.create_commentary_repository.return_value = MagicMock(
        get_recent=AsyncMock(return_value=[_kommentar()])
    )
    factory.create_generic_text_repository.return_value = MagicMock(
        get_recent=AsyncMock(return_value=[_hintergrundinfo()])
    )
    factory.create_content_repository.return_value = MagicMock(
        getAll=AsyncMock(return_value=[_inhalt()]),
        count=AsyncMock(return_value=1),
        search=AsyncMock(return_value=[_inhalt(klasse=ContentSearchResult, score=1)]),
    )
    nutzung = MagicMock()
    nutzung.enrich_content_with_usage.side_effect = lambda eintraege: eintraege
    with patch("api.v1.content.QdrantRepositoryFactory", return_value=factory), patch(
        "api.v1.content.get_usage_service", return_value=nutzung
    ):
        client = TestClient(lese_app)

        def abrufen(route, headers):
            methode, url = ROUTEN[route]
            if methode == GET:
                antwort = client.get(url, headers=headers)
            else:
                antwort = client.post(url, json=SUCHE, headers=headers)
            assert antwort.status_code == 200, antwort.text
            return antwort

        yield abrufen
    lese_app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.parametrize("route", ROUTEN)
class TestLesendeRouten:
    def test_angemeldet_ohne_kennung_mit_namen(self, lese_client, route):
        antwort = lese_client(route, FREMD)

        _ohne_kennung(antwort)
        for eintrag in _eintraege(antwort.json()):
            assert eintrag["autor_name"] == NAME
            assert eintrag["ist_eigener_beitrag"] is False

    def test_eigener_beitrag_erkannt(self, lese_client, route):
        antwort = lese_client(route, EIGEN)

        for eintrag in _eintraege(antwort.json()):
            assert eintrag["ist_eigener_beitrag"] is True

    def test_anonym_ohne_kennung_ohne_namen(self, lese_client, route):
        antwort = lese_client(route, ANONYM)

        _ohne_kennung(antwort)
        for eintrag in _eintraege(antwort.json()):
            assert eintrag.get("autor_name") is None
            assert eintrag.get("ist_eigener_beitrag") is None

    def test_admin_sieht_kennung(self, lese_client, route):
        antwort = lese_client(route, ADMIN)

        # Nur die Kennung des Autors, keine Bearbeitungshistorie.
        assert BEARBEITER not in antwort.text
        for eintrag in _eintraege(antwort.json()):
            assert eintrag["original_author"] == AUTORIN
            assert eintrag["ist_eigener_beitrag"] is False


@pytest.mark.unit
def test_admin_kopf_ohne_anmeldung_zaehlt_nicht(lese_client):
    """Den Kopf setzt nur das BFF; ohne Kennung ist niemand Admin."""
    antwort = lese_client("commentary/getById", {"X-Is-Admin": "true"})

    _ohne_kennung(antwort)


# --------------------------------------------------------------------------- #
# Suche
# --------------------------------------------------------------------------- #


@pytest.fixture
def such_antwort(search_client, anzeigenamen_ohne_datenbank):
    """Ein Treffer je Beitragstyp, alle von AUTORIN."""
    anzeigenamen_ohne_datenbank.anzeigenamen.side_effect = lambda ids: {
        k: NAME for k in ids if k == AUTORIN
    }
    ids = {typ: uuid.uuid4() for typ in ContentType}
    client = search_client(
        statement_results=[
            _statement_result(
                0.95,
                [
                    _reply(typ, 0.95, ids[typ])
                    for typ in (
                        ContentType.COMMENTARY,
                        ContentType.GENERIC_TEXT,
                        ContentType.POST,
                        ContentType.IMAGE,
                    )
                ],
            )
        ]
    )
    dienste = {
        get_commentary_service: _kommentar,
        get_generic_text_service: _hintergrundinfo,
        get_post_service: _post,
        get_image_service: _bild,
    }
    for abhaengigkeit, einzeln in dienste.items():
        dienst = MagicMock(
            spec=BaseContentService,
            get=AsyncMock(side_effect=lambda i, e=einzeln: e(i)),
            search=AsyncMock(return_value=[]),
        )
        such_app.dependency_overrides[abhaengigkeit] = lambda d=dienst: d

    def suchen(headers):
        antwort = client.post(
            SEARCH_URL, json={"query_text": "frage", "limit": 10}, headers=headers
        )
        assert antwort.status_code == 200, antwort.text
        body = antwort.json()
        for feld in TREFFERLISTEN:
            assert len(body[feld]) == 1, feld
        return antwort

    return suchen


@pytest.mark.unit
class TestSuche:
    def test_angemeldet_ohne_kennung_mit_namen(self, such_antwort):
        antwort = such_antwort(FREMD)

        _ohne_kennung(antwort)
        for eintrag in _eintraege(antwort.json()):
            assert eintrag["autor_name"] == NAME
            assert eintrag["ist_eigener_beitrag"] is False

    def test_namen_aus_einer_abfrage(self, such_antwort, anzeigenamen_ohne_datenbank):
        such_antwort(FREMD)

        assert anzeigenamen_ohne_datenbank.anzeigenamen.call_count == 1

    def test_eigener_beitrag_erkannt(self, such_antwort):
        antwort = such_antwort(EIGEN)

        for eintrag in _eintraege(antwort.json()):
            assert eintrag["ist_eigener_beitrag"] is True

    def test_anonym_ohne_kennung_ohne_namen(
        self, such_antwort, anzeigenamen_ohne_datenbank
    ):
        antwort = such_antwort({})

        _ohne_kennung(antwort)
        for eintrag in _eintraege(antwort.json()):
            assert eintrag["autor_name"] is None
            assert eintrag["ist_eigener_beitrag"] is None
        anzeigenamen_ohne_datenbank.anzeigenamen.assert_not_called()

    def test_admin_sieht_kennung(self, such_antwort):
        antwort = such_antwort(ADMIN)

        assert BEARBEITER not in antwort.text
        for eintrag in _eintraege(antwort.json()):
            assert eintrag["original_author"] == AUTORIN


# --------------------------------------------------------------------------- #
# Umwandlung
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_als_responses_laesst_den_db_entry_unveraendert():
    """Der DbEntry kann aus einem Cache stammen; geleert wird nur die Kopie."""
    eintrag = _kommentar()

    (kommentar,) = als_responses(KommentarResponse, [eintrag], Aufrufer(LESERIN))

    assert kommentar.original_author is None
    assert eintrag.original_author == AUTORIN
    assert eintrag.edit_history[0].editor == BEARBEITER
