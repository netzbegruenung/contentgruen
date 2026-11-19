"""
AnzeigenameService: Header dekodieren, nur bei Aenderung schreiben.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import dependencies
from services.anzeigename_service import (
    EHEMALIGE_PERSON_KENNUNG,
    AnzeigenameService,
    anzeigename_aus_header,
)


@pytest.fixture
def repository():
    return MagicMock()


@pytest.fixture
def service(repository):
    return AnzeigenameService(repository)


@pytest.mark.unit
class TestAnzeigenameAusHeader:
    def test_umlaute_werden_dekodiert(self):
        assert anzeigename_aus_header("J%C3%BCrgen%20%C3%96.") == "Jürgen Ö."

    def test_kein_gueltiges_utf8_ist_kein_name(self):
        assert anzeigename_aus_header("%FF%FE") is None

    def test_steuerzeichen_fallen_weg(self):
        assert anzeigename_aus_header("Anna%0D%0A%20B.") == "Anna B."

    @pytest.mark.parametrize("roh", [None, "", "%20%20", "%0A"])
    def test_leer_ist_kein_name(self, roh):
        assert anzeigename_aus_header(roh) is None

    def test_wird_gekappt(self):
        assert len(anzeigename_aus_header("A" * 500)) == 100


@pytest.mark.unit
class TestMerken:
    def test_erster_request_schreibt(self, service, repository):
        service.merken("kennung-1", "Anna%20B.")

        repository.anzeigename_speichern.assert_called_once_with("kennung-1", "Anna B.")

    def test_gleicher_name_schreibt_nicht_erneut(self, service, repository):
        service.merken("kennung-1", "Anna%20B.")
        service.merken("kennung-1", "Anna%20B.")

        assert repository.anzeigename_speichern.call_count == 1

    def test_namenswechsel_schreibt(self, service, repository):
        service.merken("kennung-1", "Anna%20B.")
        service.merken("kennung-1", "Anna%20C.")

        assert repository.anzeigename_speichern.call_count == 2
        repository.anzeigename_speichern.assert_called_with("kennung-1", "Anna C.")

    @pytest.mark.parametrize("user_id", [None, "", "anonymous"])
    def test_ohne_angemeldete_person_nichts(self, service, repository, user_id):
        service.merken(user_id, "Anna%20B.")

        repository.anzeigename_speichern.assert_not_called()

    def test_kaputter_header_schreibt_nichts(self, service, repository):
        service.merken("kennung-1", "%FF")

        repository.anzeigename_speichern.assert_not_called()

    def test_datenbankfehler_wirft_nicht_und_wird_wiederholt(self, service, repository):
        repository.anzeigename_speichern.side_effect = [RuntimeError("weg"), None]

        service.merken("kennung-1", "Anna%20B.")
        service.merken("kennung-1", "Anna%20B.")

        assert repository.anzeigename_speichern.call_count == 2


@pytest.mark.unit
class TestNamen:
    def test_namen_aus_der_tabelle(self, service, repository):
        repository.anzeigenamen.return_value = {"kennung-1": "Anna B."}

        assert service.namen(["kennung-1", "kennung-2"]) == {"kennung-1": "Anna B."}

    def test_platzhalter_heisst_ehemalige_person(self, service, repository):
        repository.anzeigenamen.return_value = {"kennung-1": "Anna B."}

        assert service.namen(["kennung-1", EHEMALIGE_PERSON_KENNUNG]) == {
            "kennung-1": "Anna B.",
            EHEMALIGE_PERSON_KENNUNG: "ehemalige Person",
        }

    def test_platzhalter_auch_wenn_die_datenbank_fehlt(self, service, repository):
        repository.anzeigenamen.side_effect = RuntimeError("weg")

        assert service.namen([EHEMALIGE_PERSON_KENNUNG]) == {
            EHEMALIGE_PERSON_KENNUNG: "ehemalige Person"
        }

    def test_platzhalter_bekommt_keinen_namen_aus_dem_header(self, service, repository):
        service.merken(EHEMALIGE_PERSON_KENNUNG, "Anna%20B.")

        repository.anzeigename_speichern.assert_not_called()


STARTKONTO = "redaktion-startkonto"
VOLL = "Redaktion%20Gut%20gesagt"


@pytest.mark.unit
class TestStartkontoVollerName:
    """Startkonten sind Funktionskonten und zeigen den ungekuerzten Namen."""

    def test_startkonto_bekommt_den_vollen_namen(self, repository):
        service = AnzeigenameService(repository, frozenset({STARTKONTO}))

        service.merken(STARTKONTO, "Redaktion%20G.", VOLL)

        repository.anzeigename_speichern.assert_called_once_with(
            STARTKONTO, "Redaktion Gut gesagt"
        )

    def test_normales_konto_bleibt_gekuerzt(self, repository):
        service = AnzeigenameService(repository, frozenset({STARTKONTO}))

        service.merken("kennung-1", "Anna%20B.", "Anna%20Berger")

        repository.anzeigename_speichern.assert_called_once_with("kennung-1", "Anna B.")

    def test_leere_startkonten_liste_aendert_nichts(self, repository):
        service = AnzeigenameService(repository, frozenset())

        service.merken(STARTKONTO, "Redaktion%20G.", VOLL)

        repository.anzeigename_speichern.assert_called_once_with(
            STARTKONTO, "Redaktion G."
        )

    def test_startkonto_ohne_vollen_namen_nimmt_den_gekuerzten(self, repository):
        service = AnzeigenameService(repository, frozenset({STARTKONTO}))

        service.merken(STARTKONTO, "Redaktion%20G.")

        repository.anzeigename_speichern.assert_called_once_with(
            STARTKONTO, "Redaktion G."
        )

    def test_nach_neustart_ersetzt_der_volle_name_den_gekuerzten(self, repository):
        # Vor dem Deploy abgelegt: "Redaktion G.". Der neue Prozess hat einen leeren
        # Cache und schreibt beim ersten Request des Startkontos den vollen Namen.
        vorher = AnzeigenameService(repository)
        vorher.merken(STARTKONTO, "Redaktion%20G.", VOLL)
        nachher = AnzeigenameService(repository, frozenset({STARTKONTO}))
        nachher.merken(STARTKONTO, "Redaktion%20G.", VOLL)
        nachher.merken(STARTKONTO, "Redaktion%20G.", VOLL)

        assert [c.args for c in repository.anzeigename_speichern.call_args_list] == [
            (STARTKONTO, "Redaktion G."),
            (STARTKONTO, "Redaktion Gut gesagt"),
        ]


@pytest.mark.unit
class TestDependency:
    """anzeigename_merken liest genau die beiden Header, die das BFF setzt."""

    @pytest.fixture
    def client(self, service, monkeypatch):
        monkeypatch.setattr(dependencies, "get_anzeigename_service", lambda: service)
        app = FastAPI(dependencies=[Depends(dependencies.anzeigename_merken)])

        @app.get("/ping")
        def ping():
            return {}

        return TestClient(app)

    def test_header_wird_abgelegt(self, client, repository):
        client.get(
            "/ping",
            headers={
                "X-User": "kennung-1",
                "X-User-Display-Name": "J%C3%BCrgen%20%C3%96.",
            },
        )

        repository.anzeigename_speichern.assert_called_once_with(
            "kennung-1", "Jürgen Ö."
        )

    def test_voller_name_wird_an_den_dienst_gereicht(self, repository, monkeypatch):
        service = AnzeigenameService(repository, frozenset({STARTKONTO}))
        monkeypatch.setattr(dependencies, "get_anzeigename_service", lambda: service)
        app = FastAPI(dependencies=[Depends(dependencies.anzeigename_merken)])

        @app.get("/ping")
        def ping():
            return {}

        TestClient(app).get(
            "/ping",
            headers={
                "X-User": STARTKONTO,
                "X-User-Display-Name": "Redaktion%20G.",
                "X-User-Full-Name": VOLL,
            },
        )

        repository.anzeigename_speichern.assert_called_once_with(
            STARTKONTO, "Redaktion Gut gesagt"
        )

    def test_ohne_header_kein_zugriff(self, client, repository):
        client.get("/ping", headers={"X-User": "kennung-1"})

        repository.anzeigename_speichern.assert_not_called()
