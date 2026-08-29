# test_main.py
import os
import pytest
from fastapi.testclient import TestClient
from main import app

# Set the environment variable for the test
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 404  # Assuming the root endpoint is not defined


# Die Index-Stubs der Content-Router sind als @router.get("/") registriert und
# heissen mit dem Prefix also "/api/v1/content/" -- mit Slash. Frueher fuehrte
# die Form ohne Slash ueber einen 307 dorthin; seit redirect_slashes=False
# (der 307 verriet den internen Dienstnamen im Location-Header) gibt es diese
# Umleitung nicht mehr, und der Test spricht die Route direkt an.
def test_content_router():
    response = client.get("/api/v1/content/")
    assert (
        response.status_code == 200
    )  # Assuming the content router is defined and returns 200


def test_statement_router():
    response = client.get("/api/v1/statement/")
    assert (
        response.status_code == 200
    )  # Assuming the statement router is defined and returns 200


@pytest.mark.parametrize("path", ["/api/v1/content", "/api/v1/statement"])
def test_index_routes_do_not_redirect_without_slash(path):
    """
    Die Gegenprobe: ohne Slash gibt es keine Umleitung mehr, sondern 404.

    Festgehalten, damit die Aenderung als bewusste Entscheidung erkennbar
    bleibt und nicht als Regression zurueckgedreht wird.
    """
    response = TestClient(app, follow_redirects=False).get(path)

    assert response.status_code == 404
    assert "location" not in {h.lower() for h in response.headers}
