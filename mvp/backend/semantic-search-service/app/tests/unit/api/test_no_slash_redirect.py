"""
Kein 307 auf Pfaden, die sich nur im abschliessenden Slash unterscheiden.

Starlette beantwortete solche Pfade mit einer Umleitung, bevor irgendeine
Auth-Dependency lief, und setzte dabei einen absoluten Location-Header mit dem
internen Dienstnamen samt Port. GET /api/v1/moderation/reports/ verriet so einem
unauthentifizierten Aufrufer die interne Topologie.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

# Ohne follow_redirects: eine Umleitung soll als solche sichtbar werden.
client = TestClient(app, follow_redirects=False)

# Geschuetzte Routen, deren Slash-Variante frueher 307 ergab.
SLASH_VARIANTS = [
    "/api/v1/moderation/reports/",
    "/api/v1/usage/trending/",
    "/api/v1/metrics/getMetrics/",
    "/api/v1/health/",
]


@pytest.mark.parametrize("path", SLASH_VARIANTS)
def test_trailing_slash_does_not_redirect(path):
    response = client.get(path)

    assert response.status_code != 307
    assert "location" not in {h.lower() for h in response.headers}


@pytest.mark.parametrize("path", SLASH_VARIANTS)
def test_trailing_slash_leaks_no_internal_host(path):
    response = client.get(path)

    assert "localhost:8000" not in response.text
    assert "contentgruen-semantic-search" not in response.text


def test_health_without_slash_still_works():
    """Die Form, die Healthchecks und Backup-Skripte verwenden."""
    assert client.get("/api/v1/health").status_code == 200


def test_moderation_reports_without_slash_still_requires_admin():
    """Der eigentliche Endpunkt bleibt erreichbar -- und geschuetzt."""
    assert client.get("/api/v1/moderation/reports").status_code == 401
