"""
content/getAll liest den ganzen Inhaltsbestand ueber alle Typen (ContentRepository
mit content_type=None) und blendet dabei nur Gesperrtes und Geloeschtes aus, nicht
die unbeantworteten Suchanfragen unter der Schwelle (#436). Frontend und BFF rufen
den Endpunkt nicht auf; er ist deshalb nur fuer Admins offen (juristische
Vorpruefung vom 12.11.2026, P6). Gelesen wird gegen das echte Repository ueber dem
Test-Embeddings-Manager.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.content import router as content_router
from dependencies import get_settings
from domain.models.content_origin import ContentOrigin
from tests.conftest import create_base_content_fields, create_statement_data

URL = "/api/v1/content/getAll"
SUCHTEXT = "Wer zahlt die Waermepumpe von Frau Beispiel"

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "person-1"}
BESUCHER = {"X-User": "anonymous"}
NICHT_ADMINS = [MITWIRKENDE, BESUCHER, {}]
NICHT_ADMIN_IDS = ["mitwirkende", "besucher", "ohne_kopf"]

app = FastAPI()
app.include_router(content_router, prefix="/api/v1/content")


@pytest.fixture
def client(test_settings, test_embeddings_manager, anzeigenamen_ohne_datenbank):
    from repositories.aggregated.content_repository import ContentRepository

    test_embeddings_manager.add_test_data(
        "statement",
        [
            {
                **create_base_content_fields(),
                **create_statement_data(text=SUCHTEXT),
                "origin": ContentOrigin.SEARCH_QUERY.value,
                "id": str(uuid.uuid4()),
                "content_type": "statement",
            }
        ],
    )
    factory = MagicMock()
    factory.create_content_repository.return_value = ContentRepository(
        test_settings, test_embeddings_manager
    )
    nutzung = MagicMock()
    nutzung.enrich_content_with_usage.side_effect = lambda eintraege: eintraege
    app.dependency_overrides[get_settings] = lambda: test_settings
    with patch("api.v1.content.QdrantRepositoryFactory", return_value=factory), patch(
        "api.v1.content.get_usage_service", return_value=nutzung
    ):
        yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.api
class TestContentGetAll:
    @pytest.mark.parametrize("headers", NICHT_ADMINS, ids=NICHT_ADMIN_IDS)
    def test_nicht_admins_bekommen_keine_suchanfrage(self, client, headers):
        antwort = client.get(URL, headers=headers)

        assert SUCHTEXT not in antwort.text
        assert antwort.status_code in (401, 403)

    def test_admin_sieht_den_bestand(self, client):
        antwort = client.get(URL, headers=ADMIN)

        assert antwort.status_code == 200
        assert SUCHTEXT in antwort.text
