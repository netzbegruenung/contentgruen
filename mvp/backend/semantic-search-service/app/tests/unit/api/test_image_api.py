"""
Antwortformat der Bild-Endpunkte.

Jede Route in api/v1/image.py beschreibt ihre Antwort mit einem response_model.
getById und getAll liefern ein Bild als BildResponse: eine feste Feldauswahl mit
dem Anzeigenamen statt der Kennung und dem Zustand, ohne Bearbeitungshistorie und
Moderationsfelder (#311); die Felder teilt es mit den anderen Beitragstypen (#333). addImage gibt 201 mit der ID. Ein Bild ohne Unterschrift lehnt addImage ab
(422, test_add_image.py).
"""

import datetime
import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.v1.image import router as image_router
from dependencies import get_image_service
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import ContentStatus
from domain.models.edit_entry import EditEntry
from domain.models.image import ImageDbEntry
from services.anzeigename_service import (
    EHEMALIGE_PERSON_KENNUNG,
    EHEMALIGE_PERSON_NAME,
)
from services.content.base_content_service import BaseContentService
from tests.conftest import create_base_content_fields, create_image_data

BILD_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
TITEL = "Solardach auf der Schule"
BILD_URL = "https://example.org/solar.jpg"
UNTERSCHRIFT = "Ein Solardach auf einer Grundschule"
KENNUNG = "kennung-der-autorin"
ANDERE_KENNUNG = "kennung-des-bearbeiters"
ANZEIGENAME = "Anna B."
ZEITPUNKT = datetime.datetime(2026, 10, 1, 12, 0)

# Was ein Bild nach aussen zeigt. Alles andere am ImageDbEntry ist intern.
# original_author ist nur fuer Admins belegt, sonst null (#333).
BILD_FELDER = {
    "id",
    "content_type",
    "title",
    "image_url",
    "text",
    "created",
    "status",
    "usage_count",
    "autor_name",
    "ist_eigener_beitrag",
    "original_author",
}


@pytest.fixture
def image_service():
    service = Mock(spec=BaseContentService)
    service.add = AsyncMock(return_value=BILD_ID)
    service.get = AsyncMock()
    service.get_all = AsyncMock(return_value=[])
    service.count = AsyncMock(return_value=0)
    return service


@pytest.fixture
def client(image_service):
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")
    app.dependency_overrides[get_image_service] = lambda: image_service
    return TestClient(app)


def _bild(**overrides) -> ImageDbEntry:
    """Ein Bild, an dem jedes interne Feld etwas traegt, das nicht hinausgehen darf."""
    felder = {
        **create_base_content_fields(
            id=BILD_ID,
            original_author=KENNUNG,
            last_modified_by=ANDERE_KENNUNG,
            authors=[AuthorEntry(name=KENNUNG), AuthorEntry(name=ANDERE_KENNUNG)],
            edit_history=[
                EditEntry(
                    editor=ANDERE_KENNUNG,
                    timestamp=ZEITPUNKT,
                    action="edit",
                )
            ],
            report_count=2,
            report_flagged=True,
            most_similar_similarity_score=0.9,
            most_similar_content_id=uuid.uuid4(),
            rejection_reason="intern",
            block_reason="intern",
        ),
        **create_image_data(
            title=TITEL,
            image_url=BILD_URL,
            text=UNTERSCHRIFT,
            description_model="ein-modell",
        ),
    }
    felder.update(overrides)
    return ImageDbEntry(**felder)


def _get_by_id(client, x_user="leserin"):
    headers = {"X-User": x_user} if x_user else {}
    return client.get(
        "/api/v1/image/getById", params={"image_id": str(BILD_ID)}, headers=headers
    )


def test_image_router_jede_route_hat_response_model():
    routen = [r for r in image_router.routes if isinstance(r, APIRoute)]

    assert routen
    assert [r.path for r in routen if r.response_model is None] == []


def test_image_router_kein_testendpunkt_unter_dem_praefix(client):
    assert client.get("/api/v1/image/").status_code == 404


def test_add_image_mit_unterschrift_antwortet_201_mit_id(client):
    response = client.post(
        "/api/v1/image/addImage",
        json={"image": {"title": TITEL, "image_url": BILD_URL, "text": UNTERSCHRIFT}},
        headers={"X-User": "autorin"},
    )

    assert response.status_code == 201
    assert response.content == f'{{"id":"{BILD_ID}"}}'.encode()


def test_add_image_dokumentiert_nur_201():
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")

    antworten = app.openapi()["paths"]["/api/v1/image/addImage"]["post"]["responses"]

    assert "202" not in antworten
    schema = antworten["201"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/AddImageResponse"}


def test_get_by_id_liefert_das_bild(client, image_service):
    image_service.get.return_value = _bild()

    response = _get_by_id(client)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(BILD_ID)
    assert body["content_type"] == "image"
    assert body["title"] == TITEL
    assert body["image_url"] == BILD_URL
    assert body["text"] == UNTERSCHRIFT
    assert body["status"] == "visible"


# Haelt den Ist-Stand fest: getById filtert nicht nach Zustand. Laut Glossar ist ein
# gesperrtes Bild fuer Nicht-Admins nicht abrufbar; das baut #300, dann aendert sich
# dieser Test.
def test_get_by_id_gesperrtes_bild_bleibt_erkennbar(client, image_service):
    image_service.get.return_value = _bild(status=ContentStatus.BLOCKED)

    response = _get_by_id(client)

    assert response.json()["status"] == "blocked"


def test_get_by_id_liefert_nur_die_bildfelder(client, image_service):
    image_service.get.return_value = _bild()

    response = _get_by_id(client)

    assert set(response.json()) == BILD_FELDER


def test_get_by_id_enthaelt_keine_kennung(client, image_service):
    image_service.get.return_value = _bild()

    response = _get_by_id(client)

    assert KENNUNG.encode() not in response.content
    assert ANDERE_KENNUNG.encode() not in response.content


def test_get_by_id_angemeldet_mit_anzeigename(
    client, image_service, anzeigenamen_ohne_datenbank
):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {KENNUNG: ANZEIGENAME}
    image_service.get.return_value = _bild()

    response = _get_by_id(client)

    assert response.json()["autor_name"] == ANZEIGENAME


def test_get_by_id_ohne_gespeicherten_namen_ist_autor_name_leer(client, image_service):
    image_service.get.return_value = _bild()

    response = _get_by_id(client)

    assert response.json()["autor_name"] is None


@pytest.mark.parametrize("x_user", [None, "anonymous"])
def test_get_by_id_anonym_ohne_anzeigename(
    client, image_service, anzeigenamen_ohne_datenbank, x_user
):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {KENNUNG: ANZEIGENAME}
    image_service.get.return_value = _bild()

    response = _get_by_id(client, x_user=x_user)

    assert response.status_code == 200
    assert response.json()["autor_name"] is None
    anzeigenamen_ohne_datenbank.anzeigenamen.assert_not_called()


def test_get_by_id_geloeschte_person_heisst_ehemalige_person(client, image_service):
    image_service.get.return_value = _bild(original_author=EHEMALIGE_PERSON_KENNUNG)

    response = _get_by_id(client)

    assert response.json()["autor_name"] == EHEMALIGE_PERSON_NAME


def test_get_all_liefert_nur_die_bildfelder_ohne_kennung(
    client, image_service, anzeigenamen_ohne_datenbank
):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {KENNUNG: ANZEIGENAME}
    zweite_id = uuid.uuid4()
    image_service.get_all.return_value = [_bild(), _bild(id=zweite_id)]
    image_service.count.return_value = 2

    response = client.get("/api/v1/image/getAll", headers={"X-User": "leserin"})

    assert response.status_code == 200
    body = response.json()
    assert body["results_count"] == 2
    assert body["total_records_count"] == 2
    assert [bild["id"] for bild in body["results"]] == [str(BILD_ID), str(zweite_id)]
    assert all(set(bild) == BILD_FELDER for bild in body["results"])
    assert all(bild["autor_name"] == ANZEIGENAME for bild in body["results"])
    assert KENNUNG.encode() not in response.content
    assert ANDERE_KENNUNG.encode() not in response.content
    # Eine Abfrage fuer die ganze Seite, nicht eine je Bild.
    anzeigenamen_ohne_datenbank.anzeigenamen.assert_called_once()


def test_get_all_anonym_ohne_anzeigename(
    client, image_service, anzeigenamen_ohne_datenbank
):
    anzeigenamen_ohne_datenbank.anzeigenamen.return_value = {KENNUNG: ANZEIGENAME}
    image_service.get_all.return_value = [_bild()]
    image_service.count.return_value = 1

    response = client.get("/api/v1/image/getAll")

    assert response.json()["results"][0]["autor_name"] is None
    anzeigenamen_ohne_datenbank.anzeigenamen.assert_not_called()


def test_lesende_routen_dokumentieren_kein_internes_feld():
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")
    schemas = app.openapi()["components"]["schemas"]

    assert "ImageDbEntry" not in schemas
    assert set(schemas["BildResponse"]["properties"]) == BILD_FELDER


def test_get_by_id_unbekannte_id_ist_404(client, image_service):
    image_service.get.side_effect = ValueError("not found")

    response = client.get("/api/v1/image/getById", params={"image_id": str(BILD_ID)})

    assert response.status_code == 404
