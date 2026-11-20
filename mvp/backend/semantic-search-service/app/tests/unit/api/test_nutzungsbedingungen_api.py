"""
Zustimmung zu den Nutzungsbedingungen in der App: Stand lesen, zustimmen
(GET/POST /api/v1/nutzungsbedingungen), der Stand im GET der Art.-9-Einwilligung und
die serverseitige Sperre in ``require_art9_einwilligung``.

Die Datenbank ersetzt ``nutzungsbedingungen_ohne_datenbank`` (tests/conftest.py).
"""

import datetime
import re

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.v1.art9_einwilligung import router as art9_router
from api.v1.nutzungsbedingungen import router as nb_router
from dependencies import (
    ART9_EINWILLIGUNG_FEHLT,
    NUTZUNGSBEDINGUNGEN_FEHLEN,
    require_art9_einwilligung,
)
from domain.nutzungsbedingungen import (
    AKTUELLER_STAND,
    GELTENDE_STAENDE,
    STAENDE,
    STAND_KENNUNG_MAX,
)
from repositories.nutzungsbedingungen_repository import NbZustimmung

pytestmark = [pytest.mark.unit, pytest.mark.api]

BASIS = "/api/v1/nutzungsbedingungen"
PERSON = {"X-User": "user-001"}
AM = datetime.datetime(2026, 11, 20, 9, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(nb_router, prefix=BASIS)
    app.include_router(art9_router, prefix="/api/v1/art9-einwilligung")

    @app.post("/speichern", dependencies=[Depends(require_art9_einwilligung)])
    def speichern():
        return {"ok": True}

    return TestClient(app)


@pytest.fixture
def repository(nutzungsbedingungen_ohne_datenbank):
    return nutzungsbedingungen_ohne_datenbank


class TestStand:
    def test_ohne_anmeldung_401(self, client):
        assert client.get(BASIS).status_code == 401

    def test_nie_zugestimmt(self, client, repository):
        repository.lesen.return_value = None

        antwort = client.get(BASIS, headers=PERSON)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "zugestimmt": False,
            "stand": None,
            "zugestimmt_am": None,
            "aktueller_stand": {
                "kennung": AKTUELLER_STAND,
                "stand": STAENDE[AKTUELLER_STAND],
            },
        }
        repository.lesen.assert_called_once_with("user-001")

    def test_zugestimmt_mit_zeitpunkt_und_stand(self, client, repository):
        repository.lesen.return_value = NbZustimmung(AKTUELLER_STAND, AM)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["zugestimmt"] is True
        assert stand["stand"] == AKTUELLER_STAND
        assert stand["zugestimmt_am"].startswith("2026-11-20T09:30")

    def test_zustimmung_zu_einem_stand_der_nicht_mehr_zaehlt_fragt_neu(
        self, client, repository, monkeypatch
    ):
        import repositories.nutzungsbedingungen_repository as modul

        monkeypatch.setattr(modul, "geltender_stand", lambda k: k == "2099-01-01")
        repository.lesen.return_value = NbZustimmung(AKTUELLER_STAND, AM)

        assert client.get(BASIS, headers=PERSON).json()["zugestimmt"] is False

    def test_im_stand_der_art9_einwilligung(self, client, repository):
        repository.lesen.return_value = None

        stand = client.get("/api/v1/art9-einwilligung", headers=PERSON).json()

        assert stand["nutzungsbedingungen"]["zugestimmt"] is False
        assert stand["nutzungsbedingungen"]["aktueller_stand"]["kennung"] == (
            AKTUELLER_STAND
        )

    def test_lesefehler_500(self, client, repository):
        repository.lesen.side_effect = RuntimeError("weg")

        assert client.get(BASIS, headers=PERSON).status_code == 500
        assert client.get("/api/v1/art9-einwilligung", headers=PERSON).status_code == (
            500
        )


class TestZustimmen:
    def test_speichert_den_stand(self, client, repository):
        antwort = client.post(BASIS, headers=PERSON, json={"stand": AKTUELLER_STAND})

        assert antwort.status_code == 204
        repository.zustimmen.assert_called_once_with("user-001", AKTUELLER_STAND)

    def test_unbekannter_stand_422(self, client, repository):
        antwort = client.post(BASIS, headers=PERSON, json={"stand": "1999-01-01"})

        assert antwort.status_code == 422
        repository.zustimmen.assert_not_called()

    def test_stand_der_nicht_mehr_gilt_400(self, client, repository, monkeypatch):
        import services.nutzungsbedingungen_service as modul

        monkeypatch.setattr(modul, "geltender_stand", lambda k: False)

        antwort = client.post(BASIS, headers=PERSON, json={"stand": AKTUELLER_STAND})

        assert antwort.status_code == 400
        repository.zustimmen.assert_not_called()

    def test_ohne_anmeldung_401(self, client, repository):
        assert client.post(BASIS, json={"stand": AKTUELLER_STAND}).status_code == 401
        repository.zustimmen.assert_not_called()

    def test_zu_lange_kennung_422(self, client, repository):
        antwort = client.post(
            BASIS, headers=PERSON, json={"stand": "x" * (STAND_KENNUNG_MAX + 1)}
        )

        assert antwort.status_code == 422


class TestSperre:
    def test_zugestimmt_und_eingewilligt_kommt_durch(self, client):
        assert client.post("/speichern", headers=PERSON).status_code == 200

    def test_ohne_zustimmung_403_mit_kennzeichen(self, client, repository):
        repository.lesen.return_value = None

        antwort = client.post("/speichern", headers=PERSON)

        assert antwort.status_code == 403
        assert antwort.json() == {"detail": NUTZUNGSBEDINGUNGEN_FEHLEN}

    def test_nutzungsbedingungen_vor_der_einwilligung(
        self, client, repository, art9_einwilligung_ohne_datenbank
    ):
        """Fehlt beides, meldet die Sperre zuerst die Nutzungsbedingungen."""
        repository.lesen.return_value = None
        art9_einwilligung_ohne_datenbank.lesen.return_value = None

        antwort = client.post("/speichern", headers=PERSON)

        assert antwort.json() == {"detail": NUTZUNGSBEDINGUNGEN_FEHLEN}
        art9_einwilligung_ohne_datenbank.lesen.assert_not_called()

    def test_mit_zustimmung_ohne_einwilligung_art9_kennzeichen(
        self, client, art9_einwilligung_ohne_datenbank
    ):
        art9_einwilligung_ohne_datenbank.lesen.return_value = None

        antwort = client.post("/speichern", headers=PERSON)

        assert antwort.json() == {"detail": ART9_EINWILLIGUNG_FEHLT}

    def test_ohne_anmeldung_entscheidet_der_endpunkt(self, client, repository):
        repository.lesen.return_value = None

        assert client.post("/speichern").status_code == 200
        repository.lesen.assert_not_called()

    def test_lesefehler_500_ohne_durchlassen(self, client, repository):
        repository.lesen.side_effect = RuntimeError("weg")

        assert client.post("/speichern", headers=PERSON).status_code == 500

    def test_direkter_aufruf_prueft_auch(self, repository):
        """Ausformulieren (api/v1/einwurf.py) ruft die Pruefung selbst auf."""
        from fastapi import HTTPException

        repository.lesen.return_value = None

        with pytest.raises(HTTPException) as fehler:
            require_art9_einwilligung("user-001")
        assert fehler.value.detail == NUTZUNGSBEDINGUNGEN_FEHLEN


class TestStaende:
    def test_aktueller_stand_ist_bekannt_und_gilt(self):
        assert AKTUELLER_STAND in STAENDE
        assert AKTUELLER_STAND in GELTENDE_STAENDE
        assert GELTENDE_STAENDE <= set(STAENDE)

    def test_kennungen_sind_tage_und_passen_in_die_spalte(self):
        for kennung in STAENDE:
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", kennung)
            assert len(kennung) <= STAND_KENNUNG_MAX

    def test_spalte_im_modell_so_lang_wie_erlaubt(self):
        from infrastructure.database.models import NutzungsbedingungenZustimmungZeile

        spalte = NutzungsbedingungenZustimmungZeile.__table__.c.stand
        assert spalte.type.length == STAND_KENNUNG_MAX
