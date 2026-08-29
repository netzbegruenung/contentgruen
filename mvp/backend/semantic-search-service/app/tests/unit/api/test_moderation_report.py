"""
Missbrauchsschutz auf POST /api/v1/moderation/report.

Die Route bleibt bewusst ohne Anmeldung erreichbar (DSA Art. 16). Genau deshalb
muss die Begrenzung an etwas haengen, das der Aufrufer nicht frei waehlen kann:
das Rate-Limit lag auf X-Session-Id, einem Wert, den die SPA selbst erzeugt und
in localStorage haelt. Zwoelf Meldungen mit zwoelf verschiedenen Session-Werten
gingen alle durch.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings
from utils import client_identity
from utils.rate_limiter import RateLimiter

REPORT_URL = "/api/v1/moderation/report"
CONTENT_ID = "11111111-2222-3333-4444-555555555555"


def _payload(**overrides):
    body = {
        "content_id": CONTENT_ID,
        "content_type": "commentary",
        "reason": "spam",
    }
    body.update(overrides)
    return body


@pytest.fixture
def service():
    """ModerationService-Mock: Inhalt existiert, Meldung gelingt."""
    mock = Mock()
    mock.content_exists = AsyncMock(return_value=True)
    mock.report_content = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()

    # Frischer Limiter je Test, sonst tragen die Fenster ineinander.
    limiter = RateLimiter(max_requests=5, window_minutes=15)
    with patch.object(
        moderation_module, "get_moderation_service", lambda: service
    ), patch.object(moderation_module, "report_rate_limiter", limiter):
        yield TestClient(app)


class TestRateLimitIsNotKeyedOnSessionHeader:
    """Der Kern des Befunds: ein wechselnder Session-Header darf nichts bringen."""

    def test_rotating_session_header_does_not_bypass_limit(self, client):
        codes = [
            client.post(
                REPORT_URL, json=_payload(), headers={"X-Session-Id": f"sess-{i}"}
            ).status_code
            for i in range(12)
        ]

        # Fuenf gehen durch, der Rest wird abgewiesen -- vorher waren es 12x 200.
        assert codes[:5] == [200] * 5
        assert set(codes[5:]) == {429}

    def test_absent_session_header_is_still_limited(self, client):
        codes = [client.post(REPORT_URL, json=_payload()).status_code for _ in range(7)]

        assert codes[:5] == [200] * 5
        assert codes[5:] == [429, 429]

    def test_limit_applies_per_client_address(self, client):
        """Zwei verschiedene Adressen teilen sich das Kontingent nicht."""
        for _ in range(5):
            response = client.post(
                REPORT_URL, json=_payload(), headers={"X-Real-IP": "198.51.100.1"}
            )
            assert response.status_code == 200

        assert (
            client.post(
                REPORT_URL, json=_payload(), headers={"X-Real-IP": "198.51.100.1"}
            ).status_code
            == 429
        )
        assert (
            client.post(
                REPORT_URL, json=_payload(), headers={"X-Real-IP": "198.51.100.2"}
            ).status_code
            == 200
        )


class TestAuthenticatedReportersAreLimitedByUser:
    """Angemeldete Melder zusaetzlich auf X-User begrenzen."""

    def test_user_limit_survives_changing_address(self, client):
        headers = {"X-User": "u1", "X-Real-IP": "198.51.100.10"}
        for _ in range(5):
            assert (
                client.post(REPORT_URL, json=_payload(), headers=headers).status_code
                == 200
            )

        # Neue Adresse, gleiche Kennung: das Nutzerlimit greift weiterhin.
        assert (
            client.post(
                REPORT_URL,
                json=_payload(),
                headers={"X-User": "u1", "X-Real-IP": "203.0.113.77"},
            ).status_code
            == 429
        )

    def test_anonymous_marker_is_not_treated_as_user(self, client, service):
        client.post(REPORT_URL, json=_payload(), headers={"X-User": "anonymous"})

        # "anonymous" ist keine Kennung: es darf nicht als Melder gespeichert werden.
        assert service.report_content.await_args.kwargs["user_id"] is None


class TestContentMustExist:
    """Eine nie existierende UUID darf keinen Eintrag im Posteingang erzeugen."""

    def test_unknown_content_id_returns_404(self, client, service):
        service.content_exists = AsyncMock(return_value=False)

        response = client.post(
            REPORT_URL, json=_payload(content_id="00000000-0000-0000-0000-000000000000")
        )

        assert response.status_code == 404
        service.report_content.assert_not_awaited()

    def test_existing_content_is_reported(self, client, service):
        assert client.post(REPORT_URL, json=_payload()).status_code == 200
        service.report_content.assert_awaited_once()


class TestRequestValidation:
    """Laenge und Wertebereich auf Schema-Ebene."""

    def test_description_over_1000_chars_is_rejected(self, client):
        response = client.post(REPORT_URL, json=_payload(description="X" * 1001))

        assert response.status_code == 422

    def test_description_at_limit_is_accepted(self, client):
        response = client.post(REPORT_URL, json=_payload(description="X" * 1000))

        assert response.status_code == 200

    def test_unknown_reason_is_rejected(self, client):
        response = client.post(REPORT_URL, json=_payload(reason="weil-ich-kann"))

        assert response.status_code == 422

    @pytest.mark.parametrize("reason", ["spam", "inappropriate", "duplicate", "other"])
    def test_documented_reasons_are_accepted(self, client, reason):
        assert client.post(REPORT_URL, json=_payload(reason=reason)).status_code == 200


class TestClientKeyDerivation:
    """Der Schluessel darf die Adresse nicht preisgeben."""

    def test_key_is_not_the_raw_address(self):
        request = Mock()
        request.headers = {"X-Real-IP": "198.51.100.5"}
        request.client = Mock(host="10.0.0.1")

        key = client_identity.derive_client_key(request)

        assert "198.51.100.5" not in key
        assert key.startswith("ip:")

    def test_same_address_yields_same_key_within_process(self):
        request = Mock()
        request.headers = {"X-Real-IP": "198.51.100.5"}
        request.client = Mock(host="10.0.0.1")

        assert client_identity.derive_client_key(
            request
        ) == client_identity.derive_client_key(request)

    def test_different_addresses_yield_different_keys(self):
        first = Mock(
            headers={"X-Real-IP": "198.51.100.5"}, client=Mock(host="10.0.0.1")
        )
        second = Mock(
            headers={"X-Real-IP": "198.51.100.6"}, client=Mock(host="10.0.0.1")
        )

        assert client_identity.derive_client_key(
            first
        ) != client_identity.derive_client_key(second)

    def test_real_ip_header_wins_over_socket_peer(self):
        """Hinter nginx ist der Socket-Peer der Proxy, nicht der Aufrufer."""
        with_header = Mock(
            headers={"X-Real-IP": "198.51.100.5"}, client=Mock(host="10.0.0.1")
        )
        without_header = Mock(headers={}, client=Mock(host="10.0.0.1"))

        assert client_identity.derive_client_key(
            with_header
        ) != client_identity.derive_client_key(without_header)

    def test_missing_address_falls_back_to_shared_key(self):
        request = Mock(headers={}, client=None)

        assert client_identity.derive_client_key(request) == "ip:unknown"
