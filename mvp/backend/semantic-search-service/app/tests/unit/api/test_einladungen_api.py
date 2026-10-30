"""
Einladungen (#429): Verwalten im Admin-Dashboard (GET/POST /api/v1/einladungen,
PATCH /api/v1/einladungen/{id}) und Einloesen ohne Anmeldung
(POST /api/v1/einladungen/pruefen, POST /api/v1/einladungen/einloesen).
"""

import uuid
from datetime import date, timedelta
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.einladungen import router as einladungen_router
from dependencies import get_einladung_service
from services.einladung_service import (
    Einladung,
    EinladungUngueltig,
    KontoAnlegenFehlgeschlagen,
    EinloesenNichtEingerichtet,
)
from utils.rate_limiter import einladung_rate_limiter
from utils.utc_tag import heute_utc

pytestmark = [pytest.mark.unit, pytest.mark.api]

BASIS = "/api/v1/einladungen"
IN_ZWEI_WOCHEN = heute_utc() + timedelta(days=14)
ADMIN = {"X-User": "admin", "X-Is-Admin": "true"}
MITWIRKEND = {"X-User": "user-001", "X-Is-Admin": "false"}
EINLADUNG = Einladung(
    id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
    code="Ab3dEf6hIj9kLm2nOp4qRs",
    notiz="Kreisverband, Herbsttreffen",
    erlaubte_einloesungen=50,
    einloesungen=3,
    gueltig_bis=date(2099, 11, 27),
    abgeschaltet=False,
    angelegt_am=date(2026, 10, 30),
)


@pytest.fixture
def service():
    service = Mock()
    service.alle.return_value = [EINLADUNG]
    service.anlegen.return_value = EINLADUNG
    service.schalten.return_value = EINLADUNG
    service.ist_einloesbar.return_value = True
    service.einloesen_eingerichtet = True
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(einladungen_router, prefix=BASIS)
    app.dependency_overrides[get_einladung_service] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def frisches_limit():
    einladung_rate_limiter._requests.clear()
    yield
    einladung_rate_limiter._requests.clear()


class TestVerwalten:
    def test_admin_sieht_alle_einladungen_mit_zaehler_und_zustand(self, client):
        response = client.get(BASIS, headers=ADMIN)

        assert response.status_code == 200
        body = response.json()
        assert body["einloesen_eingerichtet"] is True
        [e] = body["einladungen"]
        assert e["code"] == EINLADUNG.code
        assert e["einloesungen"] == 3
        assert e["erlaubte_einloesungen"] == 50
        assert e["zustand"] == "aktiv"

    @pytest.mark.parametrize("kopf", [{}, MITWIRKEND])
    def test_nur_admins_verwalten(self, client, service, kopf):
        assert client.get(BASIS, headers=kopf).status_code in (401, 403)
        antwort = client.post(
            BASIS,
            headers=kopf,
            json={
                "notiz": "x",
                "erlaubte_einloesungen": 1,
                "gueltig_bis": "2099-01-01",
            },
        )
        assert antwort.status_code in (401, 403)
        antwort = client.patch(
            f"{BASIS}/{EINLADUNG.id}", headers=kopf, json={"abgeschaltet": True}
        )
        assert antwort.status_code in (401, 403)
        service.anlegen.assert_not_called()
        service.schalten.assert_not_called()

    def test_anlegen(self, client, service):
        response = client.post(
            BASIS,
            headers=ADMIN,
            json={
                "notiz": " Persönlicher Link ",
                "erlaubte_einloesungen": 1,
                "gueltig_bis": IN_ZWEI_WOCHEN.isoformat(),
            },
        )

        assert response.status_code == 201
        service.anlegen.assert_called_once_with("Persönlicher Link", 1, IN_ZWEI_WOCHEN)

    @pytest.mark.parametrize(
        "werte",
        [
            {"notiz": "  ", "erlaubte_einloesungen": 1},
            {"notiz": "x", "erlaubte_einloesungen": 0},
            {"notiz": "x", "erlaubte_einloesungen": 1001},
            {"notiz": "x" * 201, "erlaubte_einloesungen": 1},
        ],
    )
    def test_anlegen_weist_ungueltige_werte_ab(self, client, service, werte):
        response = client.post(
            BASIS,
            headers=ADMIN,
            json={**werte, "gueltig_bis": IN_ZWEI_WOCHEN.isoformat()},
        )

        assert response.status_code == 422
        service.anlegen.assert_not_called()

    def test_letzter_tag_in_der_vergangenheit_wird_abgewiesen(self, client, service):
        response = client.post(
            BASIS,
            headers=ADMIN,
            json={
                "notiz": "x",
                "erlaubte_einloesungen": 1,
                "gueltig_bis": "2020-01-01",
            },
        )

        assert response.status_code == 422
        service.anlegen.assert_not_called()

    def test_letzter_tag_mehr_als_ein_jahr_voraus_wird_abgewiesen(
        self, client, service
    ):
        response = client.post(
            BASIS,
            headers=ADMIN,
            json={
                "notiz": "x",
                "erlaubte_einloesungen": 1,
                "gueltig_bis": "2199-01-01",
            },
        )

        assert response.status_code == 422
        service.anlegen.assert_not_called()

    def test_abschalten(self, client, service):
        response = client.patch(
            f"{BASIS}/{EINLADUNG.id}", headers=ADMIN, json={"abgeschaltet": True}
        )

        assert response.status_code == 200
        service.schalten.assert_called_once_with(EINLADUNG.id, True)

    def test_abschalten_unbekannt(self, client, service):
        service.schalten.return_value = None

        response = client.patch(
            f"{BASIS}/{uuid.uuid4()}", headers=ADMIN, json={"abgeschaltet": True}
        )

        assert response.status_code == 404


class TestEinloesen:
    def test_pruefen_ohne_anmeldung(self, client, service):
        response = client.post(f"{BASIS}/pruefen", json={"code": EINLADUNG.code})

        assert response.status_code == 200
        assert response.json() == {"einloesbar": True}

    def test_pruefen_verraet_keine_details(self, client, service):
        service.ist_einloesbar.return_value = False

        response = client.post(f"{BASIS}/pruefen", json={"code": "unbekannt"})

        assert response.json() == {"einloesbar": False}

    def test_einloesen_legt_konto_an(self, client, service):
        response = client.post(
            f"{BASIS}/einloesen",
            json={"code": EINLADUNG.code, "email": " Neu@Example.org "},
        )

        assert response.status_code == 202
        service.einloesen.assert_called_once_with(EINLADUNG.code, "neu@example.org")

    def test_ungueltige_einladung(self, client, service):
        service.einloesen.side_effect = EinladungUngueltig()

        response = client.post(
            f"{BASIS}/einloesen", json={"code": "x", "email": "neu@example.org"}
        )

        assert response.status_code == 410

    @pytest.mark.parametrize("email", ["", "keine-adresse", "a@b", "a b@example.org"])
    def test_ungueltige_mail_adresse(self, client, service, email):
        response = client.post(
            f"{BASIS}/einloesen", json={"code": EINLADUNG.code, "email": email}
        )

        assert response.status_code == 422
        service.einloesen.assert_not_called()

    def test_keycloak_fehler(self, client, service):
        service.einloesen.side_effect = KontoAnlegenFehlgeschlagen()

        response = client.post(
            f"{BASIS}/einloesen",
            json={"code": EINLADUNG.code, "email": "neu@example.org"},
        )

        assert response.status_code == 502

    def test_nicht_eingerichtet(self, client, service):
        service.einloesen.side_effect = EinloesenNichtEingerichtet()

        response = client.post(
            f"{BASIS}/einloesen",
            json={"code": EINLADUNG.code, "email": "neu@example.org"},
        )

        assert response.status_code == 503

    def test_gruppenlink_hinter_einer_adresse_bekommt_mehr_als_fuenf(self):
        # Gruppenlink in einem Raum hinter NAT (#429, Review 472 Befund 6).
        assert einladung_rate_limiter.max_requests >= 20

    def test_rate_limit(self, client, service):
        erlaubt = einladung_rate_limiter.max_requests
        for _ in range(erlaubt):
            client.post(
                f"{BASIS}/einloesen",
                json={"code": EINLADUNG.code, "email": "neu@example.org"},
            )

        response = client.post(
            f"{BASIS}/einloesen",
            json={"code": EINLADUNG.code, "email": "neu@example.org"},
        )

        assert response.status_code == 429
        assert service.einloesen.call_count == erlaubt
