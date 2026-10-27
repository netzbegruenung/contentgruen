"""
Die Rueckmeldung beim Anmelden (#349): "Seit deinem letzten Besuch wurden deine
Beitraege N-mal genutzt".

Wie die Nutzungsstatistik ohne Kennung in der Adresse: Die Person kommt aus
``X-User`` (gesetzt vom BFF), ein Pfad mit Kennung stuende im Zugriffslog.
POST, weil der Aufruf den gezeigten Stand fortschreibt.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import usage as usage_module
from api.v1.usage import router as usage_router
from core.logging import log_pseudonym

URL = "/api/v1/usage/users/me/besuch"


@pytest.fixture
def dienst():
    dienst = Mock()
    dienst.nutzung_seit_letztem_besuch = AsyncMock(return_value=4)
    return dienst


@pytest.fixture
def client(dienst):
    app = FastAPI()
    app.include_router(usage_router, prefix="/api/v1/usage")

    with patch.object(usage_module, "get_usage_service", return_value=dienst):
        yield TestClient(app)


class TestSeitLetztemBesuch:
    def test_besuch_nennt_nutzung_seit_letztem_besuch(self, client, dienst):
        antwort = client.post(URL, headers={"X-User": "kim-1"})

        assert antwort.status_code == 200
        assert antwort.json() == {"nutzung_seit_letztem_besuch": 4}
        dienst.nutzung_seit_letztem_besuch.assert_awaited_once_with("kim-1")

    @pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
    def test_besuch_ohne_anmeldung_401(self, client, dienst, kopf):
        antwort = client.post(URL, headers=kopf)

        assert antwort.status_code == 401
        dienst.nutzung_seit_letztem_besuch.assert_not_awaited()

    def test_besuch_ohne_kennung_in_der_adresse(self, client, dienst):
        antwort = client.post(
            "/api/v1/usage/users/bo-2/besuch", headers={"X-User": "kim-1"}
        )

        assert antwort.status_code in (404, 405)
        dienst.nutzung_seit_letztem_besuch.assert_not_awaited()

    def test_besuch_fehler_ohne_kennung_im_log(self, client, dienst, caplog):
        dienst.nutzung_seit_letztem_besuch.side_effect = RuntimeError("kaputt")

        antwort = client.post(URL, headers={"X-User": "kim-1"})

        assert antwort.status_code == 500
        assert log_pseudonym("kim-1") in caplog.text
        assert "kim-1" not in caplog.text
