"""
Der Zaehl-Endpunkt ist gedrosselt (#352): Sonst liesse sich der Zaehler auf der
Karte mit einer Schleife beliebig hochtreiben. Angemeldete zaehlen je Kennung,
Besucher je Adresse; Anzahl und Fenster stehen in der Konfiguration.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from core.config import Settings
from dependencies import get_nutzung_rate_limiter, get_settings
from utils.rate_limiter import RateLimiter

URL = "/api/v1/usage/content/11111111-1111-4111-8111-111111111111/usage"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.track_content_usage.return_value = True
    dienst.get_content_usage.return_value = 4
    return dienst


@pytest.fixture
def client(dienst):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Settings()
    limiter = RateLimiter(max_requests=2, window_minutes=10)
    app.dependency_overrides[get_nutzung_rate_limiter] = lambda: limiter

    async def beitrag_laden(content_id, settings):
        return SimpleNamespace(id=content_id, original_author="kim-1")

    with patch.object(
        usage_module, "get_usage_service", return_value=dienst
    ), patch.object(usage_module, "beitrag_laden", beitrag_laden):
        yield TestClient(app)


def test_zaehlen_ueber_dem_limit_ist_429(client, dienst):
    kopf = {"X-User": "bo-2"}

    antworten = [client.post(URL, json={}, headers=kopf).status_code for _ in range(3)]

    assert antworten == [200, 200, 429]
    assert dienst.track_content_usage.call_count == 2


def test_limit_gilt_je_person(client, dienst):
    for _ in range(2):
        client.post(URL, json={}, headers={"X-User": "bo-2"})

    assert client.post(URL, json={}, headers={"X-User": "lea-3"}).status_code == 200


def test_besucher_teilen_das_limit_ihrer_adresse(client):
    antworten = [client.post(URL, json={}).status_code for _ in range(3)]

    assert antworten == [200, 200, 429]


def test_limit_kommt_aus_der_konfiguration():
    import dependencies

    dependencies._nutzung_rate_limiter = None
    with patch.object(
        dependencies,
        "settings",
        Settings(nutzung_rate_limit_anfragen=7, nutzung_rate_limit_minuten=3),
    ):
        limiter = get_nutzung_rate_limiter()
    dependencies._nutzung_rate_limiter = None

    assert limiter.max_requests == 7
    assert limiter.window.total_seconds() == 180
