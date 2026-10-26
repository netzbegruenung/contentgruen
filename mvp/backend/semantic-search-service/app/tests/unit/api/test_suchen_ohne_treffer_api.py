"""
Admin-Endpunkt /api/v1/metrics/suchen-ohne-treffer.

Nur Admins sehen die Liste; sie enthaelt je Aussage den Text und die Anzahl,
aber nichts ueber die Suchenden und keine ID.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.metrics import router as metrics_router
from dependencies import get_suchen_ohne_treffer_service
from services.suchen_ohne_treffer_service import SucheOhneTreffer

pytestmark = [pytest.mark.unit, pytest.mark.api]

PFAD = "/api/v1/metrics/suchen-ohne-treffer"
ADMIN = {"X-User": "admin", "X-Is-Admin": "true"}
AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def service():
    service = Mock()
    service.haeufigste = AsyncMock(
        return_value=[SucheOhneTreffer(AUSSAGE, "Windräder töten Vögel", 5)]
    )
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1/metrics")
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: service
    return TestClient(app)


def test_anonym_ist_nicht_angemeldet(client):
    assert client.get(PFAD).status_code == 401


def test_angemeldet_ohne_admin_ist_verboten(client):
    assert client.get(PFAD, headers={"X-User": "normalo"}).status_code == 403


def test_admin_sieht_suchanfragen_mit_anzahl_ohne_personenbezug(client):
    response = client.get(PFAD, headers=ADMIN)

    assert response.status_code == 200
    body = response.json()
    assert body["wochen"] == 4
    assert body["mindestanzahl"] == 2
    # Ohne ID der Aussage: ueber deren created-Zeitpunkt liesse sich die Zeile
    # mit search_events verbinden.
    assert body["suchanfragen"] == [{"text": "Windräder töten Vögel", "anzahl": 5}]


def test_admin_waehlt_zeitraum_in_wochen(client, service):
    client.get(PFAD, params={"wochen": 8}, headers=ADMIN)

    assert service.haeufigste.call_args.kwargs["wochen"] == 8


@pytest.mark.parametrize("wochen", [0, 9])
def test_zeitraum_ausserhalb_der_aufbewahrung_ist_ungueltig(client, wochen):
    response = client.get(PFAD, params={"wochen": wochen}, headers=ADMIN)

    assert response.status_code == 422
