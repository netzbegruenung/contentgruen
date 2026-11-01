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


# Ohne Slash leitete FastAPI frueher per 307 auf die Form mit Slash um; seit
# redirect_slashes=False (der 307 verriet den internen Dienstnamen im
# Location-Header) gibt es diese Umleitung nicht mehr. Die Index-Stubs unter
# "/api/v1/<router>/" sind seit #272 ausgebaut (tests/unit/api/test_ungenutzte_endpunkte_api.py).
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
