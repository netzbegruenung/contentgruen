"""
Nutzung je Fassung (#355): Die Karte meldet beim Kopieren, welche Fassung eines
Kommentars kopiert wurde. Gezaehlt wird die Fassung nur am Kommentar; andere
Beitragstypen haben keine Fassungen.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_settings
from domain.models.content_type import ContentType

KOMMENTAR_ID = "11111111-1111-4111-8111-111111111111"
BILD_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.track_content_usage.return_value = True
    dienst.get_content_usage.return_value = 1
    return dienst


@pytest.fixture
def client(dienst):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Mock()
    typen = {KOMMENTAR_ID: ContentType.COMMENTARY, BILD_ID: ContentType.IMAGE}

    async def beitrag_laden(content_id, settings):
        return SimpleNamespace(
            id=content_id, original_author="kim-1", content_type=typen[str(content_id)]
        )

    with patch.object(
        usage_module, "get_usage_service", return_value=dienst
    ), patch.object(usage_module, "beitrag_laden", beitrag_laden):
        yield TestClient(app)


def kopieren(client, beitrag, **body):
    return client.post(
        f"/api/v1/usage/content/{beitrag}/usage", json=body, headers={"X-User": "bo-2"}
    )


def gezaehlte_fassung(dienst):
    return dienst.track_content_usage.call_args.kwargs["fassung"]


@pytest.mark.parametrize("fassung", ["kurz", "mittel", "lang"])
def test_track_content_usage_kommentar_zaehlt_die_fassung(client, dienst, fassung):
    assert kopieren(client, KOMMENTAR_ID, fassung=fassung).status_code == 200

    assert gezaehlte_fassung(dienst) == fassung


def test_track_content_usage_kommentar_ohne_fassung_zaehlt_ohne(client, dienst):
    assert kopieren(client, KOMMENTAR_ID).status_code == 200

    assert gezaehlte_fassung(dienst) is None


def test_track_content_usage_bild_hat_keine_fassung(client, dienst):
    assert kopieren(client, BILD_ID, fassung="kurz").status_code == 200

    dienst.track_content_usage.assert_called_once()
    assert gezaehlte_fassung(dienst) is None


def test_track_content_usage_unbekannte_fassung_422(client, dienst):
    assert kopieren(client, KOMMENTAR_ID, fassung="extralang").status_code == 422

    dienst.track_content_usage.assert_not_called()
