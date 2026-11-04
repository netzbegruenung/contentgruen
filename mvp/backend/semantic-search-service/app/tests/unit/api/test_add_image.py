"""
/image/addImage: Ein Bild wird nur mit Unterschrift gespeichert, und dann sofort
sichtbar (ADR 0003). Die Unterschrift schreibt die Person; den KI-Vorschlag ueber
OpenAI gibt es nicht mehr (#393). Ein Bild ohne Unterschrift, das ein
Hintergrunddienst nachbeschreibt, gibt es auch nicht.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.image import router as image_router
from dependencies import get_image_service
from domain.models.content_status import ContentStatus

ADD_URL = "/api/v1/image/addImage"
HEADERS = {"X-User": "person-1"}
UNTERSCHRIFT = "Tausende Menschen demonstrieren in Berlin fuer Klimaschutz"

app = FastAPI()
app.include_router(image_router, prefix="/api/v1/image")


def _anfrage(**bild) -> dict:
    return {
        "image": {
            "title": "Klimademo Berlin",
            "image_url": "https://example.com/demo.jpg",
            **bild,
        }
    }


@pytest.fixture
def image_service():
    service = MagicMock()
    service.add = AsyncMock(side_effect=lambda entry: entry.id)
    app.dependency_overrides[get_image_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_image_service, None)


@pytest.mark.api
class TestAddImage:
    def test_add_image_mit_unterschrift_ist_sofort_sichtbar(self, image_service):
        resp = TestClient(app).post(
            ADD_URL, json=_anfrage(text=UNTERSCHRIFT), headers=HEADERS
        )

        assert resp.status_code == 201
        gespeichert = image_service.add.await_args.args[0]
        assert resp.json() == {"id": str(gespeichert.id)}
        assert gespeichert.status == ContentStatus.VISIBLE
        assert gespeichert.text == UNTERSCHRIFT
        assert gespeichert.original_author == "person-1"

    @pytest.mark.parametrize("bild", [{}, {"text": None}, {"text": ""}, {"text": "  "}])
    def test_add_image_ohne_unterschrift_wird_abgelehnt(self, image_service, bild):
        resp = TestClient(app).post(ADD_URL, json=_anfrage(**bild), headers=HEADERS)

        assert resp.status_code == 422
        image_service.add.assert_not_awaited()
