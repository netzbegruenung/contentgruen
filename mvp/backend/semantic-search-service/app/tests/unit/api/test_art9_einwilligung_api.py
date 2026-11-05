"""
Art.-9-Einwilligung (#489): Stand lesen, einwilligen, widerrufen
(GET/POST/DELETE /api/v1/art9-einwilligung) und die Sperre der Endpunkte, die
ohne Einwilligung nichts speichern duerfen (``require_art9_einwilligung``).

Die Datenbank ersetzt ``art9_einwilligung_ohne_datenbank`` (tests/conftest.py).
"""

import datetime

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.v1.art9_einwilligung import router as art9_router
from dependencies import ART9_EINWILLIGUNG_FEHLT, require_art9_einwilligung
from domain.art9_einwilligung import AKTUELLER_WORTLAUT, WORTLAUTE
from repositories.art9_einwilligung_repository import Art9Einwilligung

pytestmark = [pytest.mark.unit, pytest.mark.api]

BASIS = "/api/v1/art9-einwilligung"
PERSON = {"X-User": "user-001"}
AM = datetime.datetime(2026, 11, 5, 9, 30, tzinfo=datetime.timezone.utc)
SPAETER = datetime.datetime(2026, 11, 6, 9, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(art9_router, prefix=BASIS)
    return TestClient(app)


@pytest.fixture
def repository(art9_einwilligung_ohne_datenbank):
    return art9_einwilligung_ohne_datenbank


class TestStand:
    def test_get_ohne_anmeldung_401(self, client):
        assert client.get(BASIS).status_code == 401
        assert client.get(BASIS, headers={"X-User": "anonymous"}).status_code == 401

    def test_get_ohne_zeile_nicht_eingewilligt_mit_aktuellem_wortlaut(
        self, client, repository
    ):
        repository.lesen.return_value = None

        antwort = client.get(BASIS, headers=PERSON)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "eingewilligt": False,
            "wortlaut": None,
            "eingewilligt_am": None,
            "widerrufen_am": None,
            "aktueller_wortlaut": {
                "kennung": AKTUELLER_WORTLAUT,
                "text": WORTLAUTE[AKTUELLER_WORTLAUT],
            },
        }
        repository.lesen.assert_called_once_with("user-001")

    def test_get_eingewilligt_mit_zeitpunkt_und_wortlaut(self, client, repository):
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, None)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["eingewilligt"] is True
        assert stand["wortlaut"] == "2026-11-05"
        assert stand["eingewilligt_am"].startswith("2026-11-05T09:30")

    def test_get_widerrufen_nicht_eingewilligt_wortlaut_bleibt(
        self, client, repository
    ):
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        stand = client.get(BASIS, headers=PERSON).json()

        assert stand["eingewilligt"] is False
        assert stand["wortlaut"] == "2026-11-05"
        assert stand["widerrufen_am"].startswith("2026-11-06T09:30")


class TestEinwilligen:
    def test_post_bekannter_wortlaut_speichert_kennung(self, client, repository):
        antwort = client.post(
            BASIS, headers=PERSON, json={"wortlaut": AKTUELLER_WORTLAUT}
        )

        assert antwort.status_code == 204
        repository.einwilligen.assert_called_once_with("user-001", AKTUELLER_WORTLAUT)

    def test_post_unbekannter_wortlaut_422_ohne_speichern(self, client, repository):
        antwort = client.post(BASIS, headers=PERSON, json={"wortlaut": "2099-01-01"})

        assert antwort.status_code == 422
        repository.einwilligen.assert_not_called()

    def test_post_ohne_anmeldung_401(self, client, repository):
        antwort = client.post(BASIS, json={"wortlaut": AKTUELLER_WORTLAUT})

        assert antwort.status_code == 401
        repository.einwilligen.assert_not_called()


class TestWiderrufen:
    def test_delete_widerruft(self, client, repository):
        antwort = client.delete(BASIS, headers=PERSON)

        assert antwort.status_code == 204
        repository.widerrufen.assert_called_once_with("user-001")

    def test_delete_ohne_anmeldung_401(self, client, repository):
        assert client.delete(BASIS).status_code == 401
        repository.widerrufen.assert_not_called()


@pytest.fixture
def gesperrt_client():
    app = FastAPI()

    @app.post("/speichern", dependencies=[Depends(require_art9_einwilligung)])
    def speichern():
        return {"ok": True}

    app.include_router(art9_router, prefix=BASIS)
    return TestClient(app)


class TestSperre:
    def test_eingewilligt_kommt_durch(self, gesperrt_client):
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

    def test_ohne_einwilligung_403_mit_kennzeichen(self, gesperrt_client, repository):
        repository.lesen.return_value = None

        antwort = gesperrt_client.post("/speichern", headers=PERSON)

        assert antwort.status_code == 403
        assert antwort.json() == {"detail": ART9_EINWILLIGUNG_FEHLT}

    def test_widerrufen_403(self, gesperrt_client, repository):
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

    def test_ohne_anmeldung_entscheidet_der_endpunkt(self, gesperrt_client, repository):
        repository.lesen.return_value = None

        assert gesperrt_client.post("/speichern").status_code == 200
        assert (
            gesperrt_client.post(
                "/speichern", headers={"X-User": "anonymous"}
            ).status_code
            == 200
        )
        repository.lesen.assert_not_called()

    def test_nach_widerruf_sofort_gesperrt(self, gesperrt_client, repository):
        # Der Dienst merkt sich ein Ja; der Widerruf muss es vergessen.
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

        gesperrt_client.delete(BASIS, headers=PERSON)
        repository.lesen.return_value = Art9Einwilligung("2026-11-05", AM, SPAETER)

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

    def test_nach_einwilligen_sofort_frei(self, gesperrt_client, repository):
        repository.lesen.return_value = None
        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 403

        gesperrt_client.post(
            BASIS, headers=PERSON, json={"wortlaut": AKTUELLER_WORTLAUT}
        )

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 200

    def test_datenbankfehler_500_ohne_durchlassen(self, gesperrt_client, repository):
        repository.lesen.side_effect = RuntimeError("weg")

        assert gesperrt_client.post("/speichern", headers=PERSON).status_code == 500


# Was ohne Art.-9-Einwilligung gesperrt ist: alles, was mit Personenbezug etwas
# speichert, aus dem sich auf die politische Meinung schliessen laesst. Kommt ein
# solcher Endpunkt dazu, gehoert er hierher und an ihn die Sperre.
GESPERRT = {
    ("POST", "/api/v1/commentary/addCommentary"),
    ("POST", "/api/v1/generic_text/addGenericText"),
    ("POST", "/api/v1/post/addPost"),
    ("POST", "/api/v1/image/addImage"),
    ("POST", "/api/v1/statement/addStatement"),
    ("POST", "/api/v1/statement/vorab"),
    ("POST", "/api/v1/reference/add"),
    ("PUT", "/api/v1/content/{beitrag_id}"),
    ("POST", "/api/v1/rawinput/addRawInput"),
    ("PUT", "/api/v1/rawinput/{einwurf_id}/draft"),
    ("PATCH", "/api/v1/rawinput/{einwurf_id}/status"),
    ("PUT", "/api/v1/voting/content/{content_id}/like"),
    ("PUT", "/api/v1/voting/content/{content_id}/dislike"),
}


def _gesperrte_routen():
    from main import app

    gesperrt = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if any(
            d.call is require_art9_einwilligung for d in route.dependant.dependencies
        ):
            gesperrt |= {(methode, route.path) for methode in route.methods}
    return gesperrt


def test_app_sperrt_genau_die_endpunkte_mit_art9_daten():
    assert _gesperrte_routen() == GESPERRT


def test_app_loeschen_bleibt_ohne_einwilligung_offen():
    gesperrt = _gesperrte_routen()

    assert not [eintrag for eintrag in gesperrt if eintrag[0] == "DELETE"]
