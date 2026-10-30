"""
GET /api/v1/metrics/bilanz (#467): die Kennzahlen der Bilanz je Woche, ohne Zielwerte.

Der BilanzService ist ersetzt; seine Rechnung pruefen tests/unit/services/test_bilanz_service.py
und die Integrationstests. Hier: Zeitraum, Felder und dass Unbekanntes leer bleibt.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.metrics import router as metrics_router
from dependencies import get_bilanz_service
from services.bilanz_service import BilanzWoche

pytestmark = pytest.mark.unit

ADMIN = {"X-User": "admin", "X-Is-Admin": "true"}
WOCHE = BilanzWoche(
    woche_ab=date(2026, 10, 26),
    tage=4,
    suchen=10,
    personen_pro_tag=2.5,
    nutzungen=3,
    anteil_ohne_treffer=30.0,
    nutzungen_je_suche=0.3,
)
LEERE_WOCHE = BilanzWoche(
    woche_ab=date(2026, 10, 19),
    tage=7,
    suchen=0,
    personen_pro_tag=0.0,
    nutzungen=None,
    anteil_ohne_treffer=None,
    nutzungen_je_suche=None,
)


@pytest.fixture
def service():
    service = Mock()
    service.wochen.return_value = [WOCHE, LEERE_WOCHE]
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(metrics_router, prefix="/api/v1/metrics")
    app.dependency_overrides[get_bilanz_service] = lambda: service
    return TestClient(app)


def test_bilanz_liefert_kennzahlen_je_woche(client, service):
    response = client.get("/api/v1/metrics/bilanz", headers=ADMIN)

    assert response.status_code == 200
    body = response.json()
    assert body["wochen"] == 8
    assert body["woechentlich"] == [
        {
            "woche_ab": "2026-10-26",
            "tage": 4,
            "suchen": 10,
            "personen_pro_tag": 2.5,
            "nutzungen": 3,
            "anteil_ohne_treffer": 30.0,
            "nutzungen_je_suche": 0.3,
        },
        {
            "woche_ab": "2026-10-19",
            "tage": 7,
            "suchen": 0,
            "personen_pro_tag": 0.0,
            "nutzungen": None,
            "anteil_ohne_treffer": None,
            "nutzungen_je_suche": None,
        },
    ]
    service.wochen.assert_called_once_with(8)


def test_bilanz_ohne_zielwerte(client):
    body = client.get("/api/v1/metrics/bilanz", headers=ADMIN).json()

    felder = set(body) | {f for w in body["woechentlich"] for f in w}
    assert not [f for f in felder if f.endswith(("_goal", "_met", "ziel"))]


def test_bilanz_zeitraum_waehlbar(client, service):
    assert (
        client.get("/api/v1/metrics/bilanz?wochen=26", headers=ADMIN).status_code == 200
    )
    service.wochen.assert_called_once_with(26)


@pytest.mark.parametrize("wochen", [0, 53])
def test_bilanz_zeitraum_begrenzt(client, wochen):
    response = client.get(f"/api/v1/metrics/bilanz?wochen={wochen}", headers=ADMIN)

    assert response.status_code == 422


def test_bilanz_datenbankfehler_ist_500(client, service):
    service.wochen.side_effect = RuntimeError("weg")

    response = client.get("/api/v1/metrics/bilanz", headers=ADMIN)

    assert response.status_code == 500
    assert "weg" not in response.text
