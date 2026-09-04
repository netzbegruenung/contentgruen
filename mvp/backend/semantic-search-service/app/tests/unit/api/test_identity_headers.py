"""
Unit tests fuer die Identitaets-Dependencies aus dependencies.py.

Hintergrund: get_current_user_optional hat den Header-Alias nicht gesetzt und
damit X-User-Id statt X-User gelesen. Das BFF setzt X-User; X-User-Id wurde von
YARP ungeprueft vom Client durchgereicht. Ergebnis waren zwei Fehler auf einmal:
der eingeloggte Nutzer bekam auf seine eigenen /usage-stats ein 403, und ein
anonymer Aufrufer konnte sich per Header eine fremde Identitaet geben.

Die Tests halten beide Eigenschaften fest -- gelesen wird X-User, und X-User-Id
hat keine Wirkung mehr.
"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from dependencies import get_current_user_optional, require_admin


def _client_for(dependency):
    """Minimal-App, die nur die uebergebene Dependency aufloest und zurueckgibt."""
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user=Depends(dependency)):
        return {"user": user}

    return TestClient(app)


class TestGetCurrentUserOptional:
    """get_current_user_optional muss X-User lesen, nicht X-User-Id."""

    def test_reads_x_user_header(self):
        response = _client_for(get_current_user_optional).get(
            "/whoami", headers={"X-User": "test-user-id-1"}
        )

        assert response.status_code == 200
        assert response.json()["user"] == "test-user-id-1"

    def test_ignores_x_user_id_header(self):
        """X-User-Id ist clientkontrolliert und darf keine Identitaet mehr stiften."""
        response = _client_for(get_current_user_optional).get(
            "/whoami", headers={"X-User-Id": "victim"}
        )

        assert response.status_code == 200
        assert response.json()["user"] is None

    def test_returns_none_without_identity_header(self):
        response = _client_for(get_current_user_optional).get("/whoami")

        assert response.status_code == 200
        assert response.json()["user"] is None

    def test_x_user_wins_over_x_user_id(self):
        """Beide gesetzt: die vom BFF gesetzte Identitaet gewinnt."""
        response = _client_for(get_current_user_optional).get(
            "/whoami", headers={"X-User": "echt", "X-User-Id": "gefaelscht"}
        )

        assert response.status_code == 200
        assert response.json()["user"] == "echt"


class TestRequireAdmin:
    """require_admin liest denselben Header und verlangt zusaetzlich X-Is-Admin."""

    def test_admin_passes(self):
        response = _client_for(require_admin).get(
            "/whoami", headers={"X-User": "admin-1", "X-Is-Admin": "true"}
        )

        assert response.status_code == 200
        assert response.json()["user"] == "admin-1"

    def test_admin_flag_is_case_insensitive(self):
        response = _client_for(require_admin).get(
            "/whoami", headers={"X-User": "admin-1", "X-Is-Admin": "True"}
        )

        assert response.status_code == 200

    def test_missing_user_is_unauthorized(self):
        response = _client_for(require_admin).get(
            "/whoami", headers={"X-Is-Admin": "true"}
        )

        assert response.status_code == 401

    def test_anonymous_user_is_unauthorized(self):
        response = _client_for(require_admin).get(
            "/whoami", headers={"X-User": "anonymous", "X-Is-Admin": "true"}
        )

        assert response.status_code == 401

    def test_non_admin_is_forbidden(self):
        response = _client_for(require_admin).get(
            "/whoami", headers={"X-User": "normalo"}
        )

        assert response.status_code == 403
