"""
PUT /api/v1/moderation/content/{id}/sperren und .../entsperren.

Admin-only; ein unbekannter Beitrag ist 404, eine ungueltige ID 422. Was Sperren am Beitrag und an den
Meldungen aendert, pruefen die Service-Tests (tests/unit/services/
test_moderation_service.py).
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings

CONTENT_ID = str(uuid.uuid4())
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "user-1", "X-Is-Admin": "false"}
GRUND = {"sperrgrund": "unterstellung", "begruendung": "Unterstellt Bosheit."}


def _koerper(aktion: str):
    """Sperren verlangt Sperrgrund und Begruendung (#448), Entsperren nichts."""
    return GRUND if aktion == "sperren" else None


@pytest.fixture
def service():
    mock = Mock()
    mock.sperren = AsyncMock(return_value=True)
    mock.entsperren = AsyncMock(return_value=True)
    mock.gesperrte_beitraege = AsyncMock(return_value=[])
    mock.sperre_bestaetigen = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    with patch.object(moderation_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


@pytest.mark.unit
@pytest.mark.parametrize("aktion", ["sperren", "entsperren"])
class TestSperrenApi:
    def test_admin_darf(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}",
            headers=ADMIN,
            json=_koerper(aktion),
        )

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        getattr(service, aktion).assert_awaited_once()
        assert getattr(service, aktion).call_args.args[0] == CONTENT_ID

    def test_mitwirkende_duerfen_nicht(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}",
            headers=MITWIRKENDE,
            json=_koerper(aktion),
        )

        assert antwort.status_code == 403
        getattr(service, aktion).assert_not_called()

    def test_besucher_duerfen_nicht(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}", json=_koerper(aktion)
        )

        assert antwort.status_code == 401

    def test_unbekannter_beitrag_ist_404(self, client, service, aktion):
        getattr(service, aktion).return_value = False

        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}",
            headers=ADMIN,
            json=_koerper(aktion),
        )

        assert antwort.status_code == 404

    def test_ungueltige_id_ist_422(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/kein-uuid/{aktion}",
            headers=ADMIN,
            json=_koerper(aktion),
        )

        assert antwort.status_code == 422
        getattr(service, aktion).assert_not_called()


@pytest.mark.unit
def test_sperren_gibt_admin_grund_und_begruendung_weiter(client, service):
    client.put(
        f"/api/v1/moderation/content/{CONTENT_ID}/sperren", headers=ADMIN, json=GRUND
    )

    kwargs = service.sperren.call_args.kwargs
    assert kwargs["gesperrt_von"] == "admin-1"
    assert kwargs["sperrgrund"] == "unterstellung"
    assert kwargs["begruendung"] == "Unterstellt Bosheit."


@pytest.mark.unit
def test_entsperren_gibt_admin_weiter(client, service):
    client.put(f"/api/v1/moderation/content/{CONTENT_ID}/entsperren", headers=ADMIN)

    assert service.entsperren.call_args.kwargs["entsperrt_von"] == "admin-1"


@pytest.mark.unit
@pytest.mark.parametrize(
    "koerper",
    [
        None,
        {"begruendung": "Unterstellt Bosheit."},
        {"sperrgrund": "fake_news", "begruendung": "x"},
        {"sperrgrund": "unterstellung"},
        {"sperrgrund": "unterstellung", "begruendung": ""},
        {"sperrgrund": "unterstellung", "begruendung": "x" * 2001},
    ],
)
def test_sperren_ohne_grund_ist_422(client, service, koerper):
    antwort = client.put(
        f"/api/v1/moderation/content/{CONTENT_ID}/sperren", headers=ADMIN, json=koerper
    )

    assert antwort.status_code == 422
    service.sperren.assert_not_called()


@pytest.mark.unit
def test_schon_gesperrt_ist_409(client, service):
    from services.moderation_service import SchonGesperrt

    service.sperren.side_effect = SchonGesperrt()

    antwort = client.put(
        f"/api/v1/moderation/content/{CONTENT_ID}/sperren", headers=ADMIN, json=GRUND
    )

    assert antwort.status_code == 409


@pytest.mark.unit
def test_sperren_nur_leerraum_als_begruendung_ist_422(client, service):
    from services.moderation_service import SperreUngueltig

    service.sperren.side_effect = SperreUngueltig("Begruendung fehlt")

    antwort = client.put(
        f"/api/v1/moderation/content/{CONTENT_ID}/sperren",
        headers=ADMIN,
        json={"sperrgrund": "unterstellung", "begruendung": "   "},
    )

    assert antwort.status_code == 422


@pytest.mark.unit
class TestSperreBestaetigenApi:
    PFAD = f"/api/v1/moderation/sperren/{uuid.uuid4()}/bestaetigen"
    KOERPER = {"begruendung": "Bleibt eine Unterstellung."}

    def test_admin_darf(self, client, service):
        antwort = client.put(self.PFAD, headers=ADMIN, json=self.KOERPER)

        assert antwort.status_code == 200
        args = service.sperre_bestaetigen.call_args.args
        assert args[1:] == ("admin-1", "Bleibt eine Unterstellung.")

    def test_ohne_offenen_widerspruch_ist_404(self, client, service):
        service.sperre_bestaetigen.return_value = False

        antwort = client.put(self.PFAD, headers=ADMIN, json=self.KOERPER)

        assert antwort.status_code == 404

    def test_ohne_begruendung_ist_422(self, client, service):
        antwort = client.put(self.PFAD, headers=ADMIN, json={"begruendung": ""})

        assert antwort.status_code == 422
        service.sperre_bestaetigen.assert_not_called()

    def test_mitwirkende_duerfen_nicht(self, client, service):
        antwort = client.put(self.PFAD, headers=MITWIRKENDE, json=self.KOERPER)

        assert antwort.status_code == 403
        service.sperre_bestaetigen.assert_not_called()


@pytest.mark.unit
class TestGesperrteApi:
    def test_admin_bekommt_gesperrte(self, client, service):
        service.gesperrte_beitraege.return_value = [
            {"id": CONTENT_ID, "content_type": "commentary", "status": "blocked"}
        ]

        antwort = client.get("/api/v1/moderation/gesperrt", headers=ADMIN)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "total": 1,
            "beitraege": [
                {"id": CONTENT_ID, "content_type": "commentary", "status": "blocked"}
            ],
        }

    def test_mitwirkende_duerfen_nicht(self, client, service):
        antwort = client.get("/api/v1/moderation/gesperrt", headers=MITWIRKENDE)

        assert antwort.status_code == 403
        service.gesperrte_beitraege.assert_not_called()

    def test_besucher_duerfen_nicht(self, client, service):
        antwort = client.get("/api/v1/moderation/gesperrt")

        assert antwort.status_code == 401
