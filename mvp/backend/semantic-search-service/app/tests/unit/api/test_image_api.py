"""
Antwortformat der Bild-Endpunkte.

Jede Route in api/v1/image.py beschreibt ihre Antwort mit einem response_model
und baut sie ueber DTOs. Die Antworten selbst bleiben, wie das Frontend sie
kennt: addImage gibt 201 mit der ID, ohne Unterschrift 202 mit ID und Status.
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
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.image import ImageDbEntry

BILD_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
TITEL = "Solardach auf der Schule"
BILD_URL = "https://example.org/solar.jpg"
UNTERSCHRIFT = "Ein Solardach auf einer Grundschule"


@pytest.fixture
def image_service():
    service = Mock()
    service.add = AsyncMock(return_value=BILD_ID)
    service.get = AsyncMock()
    return service


@pytest.fixture
def client(image_service):
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")
    app.dependency_overrides[get_image_service] = lambda: image_service
    return TestClient(app)


def _bild_eintrag() -> ImageDbEntry:
    jetzt = datetime.datetime(2026, 10, 1, tzinfo=datetime.timezone.utc)
    return ImageDbEntry(
        id=BILD_ID,
        title=TITEL,
        image_url=BILD_URL,
        text=UNTERSCHRIFT,
        created=jetzt,
        last_modified=jetzt,
        original_author="autorin",
        last_modified_by="autorin",
        authors=[AuthorEntry(name="autorin")],
        status=NEW_CONTENT_STATUS,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


def test_image_router_jede_route_hat_response_model():
    routen = [r for r in image_router.routes if isinstance(r, APIRoute)]

    assert routen
    assert [r.path for r in routen if r.response_model is None] == []


def test_image_router_kein_testendpunkt_unter_dem_praefix(client):
    assert client.get("/api/v1/image/").status_code == 404


def test_add_image_mit_bildunterschrift_antwortet_201_mit_id(client):
    response = client.post(
        "/api/v1/image/addImage",
        json={"image": {"title": TITEL, "image_url": BILD_URL, "text": UNTERSCHRIFT}},
        headers={"X-User": "autorin"},
    )

    assert response.status_code == 201
    assert response.json() == {"id": str(BILD_ID)}


def test_add_image_ohne_bildunterschrift_antwortet_202_mit_status(client):
    response = client.post(
        "/api/v1/image/addImage",
        json={"image": {"title": TITEL, "image_url": BILD_URL}},
        headers={"X-User": "autorin"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "id": str(BILD_ID),
        "status": "pending_description",
    }


def test_add_image_dokumentiert_beide_antworten():
    app = FastAPI()
    app.include_router(image_router, prefix="/api/v1/image")

    antworten = app.openapi()["paths"]["/api/v1/image/addImage"]["post"]["responses"]

    for code in ("201", "202"):
        schema = antworten[code]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/AddImageResponse"}


def test_get_by_id_liefert_den_eintrag(client, image_service):
    image_service.get.return_value = _bild_eintrag()

    response = client.get("/api/v1/image/getById", params={"image_id": str(BILD_ID)})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(BILD_ID)
    assert body["title"] == TITEL
    assert body["image_url"] == BILD_URL
    assert body["text"] == UNTERSCHRIFT


def test_get_by_id_unbekannte_id_ist_404(client, image_service):
    image_service.get.side_effect = ValueError("not found")

    response = client.get("/api/v1/image/getById", params={"image_id": str(BILD_ID)})

    assert response.status_code == 404
