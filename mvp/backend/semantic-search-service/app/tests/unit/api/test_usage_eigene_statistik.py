"""
Die Nutzungsstatistik unter "Meine Beitraege" ohne Kennung im Pfad (#284).

Die Person kommt aus ``X-User``, den das BFF aus der Anmeldung setzt
(IdentityHeaderTransform.cs). Stuende die Kennung im Pfad, landete sie im
Zugriffslog jedes Webservers davor. Eine fremde Statistik laesst sich ueber
diese Route nicht abrufen, denn es gibt keinen Parameter, der eine Kennung nennt.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from dependencies import get_settings

URL = "/api/v1/usage/users/me/usage-stats"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.get_user_usage_stats = AsyncMock(
        side_effect=lambda user_id: {
            "user_id": user_id,
            "unique_contents_contributed": 2,
            "total_usage_count": 7,
            "top_content": [],
        }
    )
    return dienst


@pytest.fixture
def client(dienst):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")
    app.dependency_overrides[get_settings] = lambda: Mock()

    with patch.object(usage_module, "get_usage_service", return_value=dienst):
        yield TestClient(app)


class TestEigeneNutzungsstatistik:
    def test_person_kommt_aus_der_anmeldung(self, client, dienst):
        antwort = client.get(URL, headers={"X-User": "kim-1"})

        assert antwort.status_code == 200
        assert antwort.json()["total_usage_count"] == 7
        dienst.get_user_usage_stats.assert_awaited_once_with("kim-1")

    @pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
    def test_ohne_anmeldung_401(self, client, dienst, kopf):
        antwort = client.get(URL, headers=kopf)

        assert antwort.status_code == 401
        dienst.get_user_usage_stats.assert_not_awaited()

    def test_kennung_im_pfad_gibt_es_nicht_mehr(self, client, dienst):
        antwort = client.get(
            "/api/v1/usage/users/bo-2/usage-stats", headers={"X-User": "kim-1"}
        )

        assert antwort.status_code == 404
        dienst.get_user_usage_stats.assert_not_awaited()

    def test_fehler_ohne_kennung_im_log(self, client, dienst, caplog):
        dienst.get_user_usage_stats.side_effect = RuntimeError("kaputt")

        antwort = client.get(URL, headers={"X-User": "kim-1"})

        assert antwort.status_code == 500
        assert "kim-1" not in caplog.text
