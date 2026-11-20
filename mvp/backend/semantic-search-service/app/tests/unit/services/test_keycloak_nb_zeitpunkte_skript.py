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
    assert ergebnis.unlesbar == {"c": "kaputt"}
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


def test_ohne_jeden_zeitpunkt_der_hinweis_auf_die_abgeschaltete_pflichtaktion(
    skript, capsys
):
    """Keycloak zeigt das Attribut nur, solange die Pflichtaktion an ist (26.8.2)."""
    skript.zahlen_ausgeben(skript.Ergebnis(konten=3))

    assert "eingeschaltet" in capsys.readouterr().out


def test_unlesbare_werte_kommen_mit_ins_archiv(skript, capsys):
    ergebnis = skript.Ergebnis(konten=1, unlesbar={"c": "kaputt"})

    skript.zeitpunkte_ausgeben(ergebnis)

    assert "c,unlesbar:kaputt" in capsys.readouterr().out
