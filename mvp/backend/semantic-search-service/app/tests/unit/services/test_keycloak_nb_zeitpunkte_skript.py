"""
Das Exportskript mvp/scripts/manual/keycloak_nb_zeitpunkte.py: liest den Zeitpunkt der
Keycloak-Zustimmung (Attribut terms_and_conditions, Unix-Sekunden) je Konto, nur
lesend. Keycloak steht hier als httpx.MockTransport.
"""

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "keycloak_nb_zeitpunkte.py"


@pytest.fixture(scope="module")
def skript():
    spec = importlib.util.spec_from_file_location("keycloak_nb_zeitpunkte", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _keycloak(konten, je_seite, anfragen):
    def antworten(anfrage: httpx.Request) -> httpx.Response:
        anfragen.append(anfrage)
        if anfrage.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t"})
        assert anfrage.method == "GET"
        assert anfrage.url.params["briefRepresentation"] == "false"
        erstes = int(anfrage.url.params["first"])
        return httpx.Response(200, json=konten[erstes : erstes + je_seite])

    return httpx.MockTransport(antworten)


def test_liest_zeitpunkte_seitenweise_und_aendert_nichts(skript, monkeypatch):
    monkeypatch.setattr(skript, "JE_SEITE", 2)
    konten = [
        {
            "id": "a",
            "username": "a@x",
            "attributes": {"terms_and_conditions": ["1762070400"]},
        },
        {"id": "b", "username": "b@x", "attributes": {}},
        {
            "id": "c",
            "username": "c@x",
            "attributes": {"terms_and_conditions": ["kaputt"]},
        },
        {"id": "d", "username": "service-account-gutgesagt-einladungen"},
        {"id": "e", "username": "e@x"},
    ]
    anfragen = []

    ergebnis = skript.zeitpunkte_lesen(
        "https://kc.example",
        "gutgesagt",
        "id",
        "geheim",
        _keycloak(konten, 2, anfragen),
    )

    assert ergebnis.konten == 4
    assert ergebnis.dienstkonten == 1
    assert ergebnis.zeitpunkte == {
        "a": datetime(2025, 11, 2, 8, 0, tzinfo=timezone.utc)
    }
    assert ergebnis.unlesbar == 1
    assert ergebnis.ohne_zeitpunkt == 2
    assert {a.method for a in anfragen} == {"POST", "GET"}
    assert [a.method for a in anfragen].count("POST") == 1


def test_zahlen_vor_der_trennzeile_kennungen_nur_mit_zeitpunkte(skript, capsys):
    ergebnis = skript.Ergebnis(
        konten=2, zeitpunkte={"a": datetime(2026, 11, 2, tzinfo=timezone.utc)}
    )

    skript.zahlen_ausgeben(ergebnis)
    zahlen = capsys.readouterr().out
    assert "a," not in zahlen
    assert "mit Zeitpunkt der Zustimmung: 1" in zahlen

    skript.zeitpunkte_ausgeben(ergebnis)
    danach = capsys.readouterr().out
    assert danach.index(skript.TRENNZEILE) < danach.index("a,2026-11-02")


def test_ohne_jeden_zeitpunkt_der_hinweis_auf_unmanaged_attributes(skript, capsys):
    skript.zahlen_ausgeben(skript.Ergebnis(konten=3))

    assert "Unmanaged attributes" in capsys.readouterr().out


class _KeycloakMitKonten:
    """Konten im Speicher; PUT ersetzt die Darstellung, ausser ``nur_lesen``."""

    def __init__(self, konten, nur_lesen=False):
        self.konten = {k["id"]: k for k in konten}
        self.nur_lesen = nur_lesen
        self.puts = []

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        import json

        pfad = anfrage.url.path
        if pfad.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t"})
        if pfad.endswith("/users") and anfrage.method == "GET":
            erstes = int(anfrage.url.params["first"])
            return httpx.Response(200, json=list(self.konten.values())[erstes:])
        kennung = pfad.rsplit("/", 1)[-1]
        if anfrage.method == "GET":
            return httpx.Response(200, json=self.konten[kennung])
        if anfrage.method == "PUT":
            koerper = json.loads(anfrage.content)
            self.puts.append(koerper)
            if not self.nur_lesen:
                self.konten[kennung] = koerper
            return httpx.Response(204)
        return httpx.Response(405)


def _konten_mit_attribut():
    return [
        {
            "id": "a",
            "username": "a@x",
            "email": "a@x",
            "firstName": "Anna",
            "attributes": {"terms_and_conditions": ["1762070400"], "andere": ["1"]},
        },
        {"id": "b", "username": "b@x", "attributes": {}},
    ]


def test_attribut_loeschen_trockenlauf_zaehlt_und_schreibt_nichts(skript):
    keycloak = _KeycloakMitKonten(_konten_mit_attribut())

    bericht = skript.attribut_loeschen(
        "https://kc.example",
        "gutgesagt",
        "id",
        "geheim",
        False,
        httpx.MockTransport(keycloak),
    )

    assert bericht.mit_attribut == 1
    assert bericht.ausgefuehrt is False
    assert keycloak.puts == []


def test_attribut_loeschen_entfernt_nur_dieses_attribut(skript):
    keycloak = _KeycloakMitKonten(_konten_mit_attribut())

    bericht = skript.attribut_loeschen(
        "https://kc.example",
        "gutgesagt",
        "id",
        "geheim",
        True,
        httpx.MockTransport(keycloak),
    )

    assert (bericht.geloescht, bericht.fehler, bericht.unveraendert) == (1, 0, 0)
    (geschrieben,) = keycloak.puts
    assert geschrieben["attributes"] == {"andere": ["1"]}
    assert geschrieben["firstName"] == "Anna"
    assert geschrieben["username"] == "a@x"


def test_attribut_loeschen_meldet_wenn_keycloak_es_stehen_laesst(skript, capsys):
    keycloak = _KeycloakMitKonten(_konten_mit_attribut(), nur_lesen=True)

    bericht = skript.attribut_loeschen(
        "https://kc.example",
        "gutgesagt",
        "id",
        "geheim",
        True,
        httpx.MockTransport(keycloak),
    )
    skript.loeschbericht_ausgeben(bericht)

    assert bericht.unveraendert == 1
    assert "Admin can edit" in capsys.readouterr().out
