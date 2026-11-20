"""
Die og-Angaben der Linkvorschau (#360): Kuerzen an Wortgrenzen, Maskieren fuer
Attributwerte, Suchtext aus der Adresse.
"""

import html
import re

import pytest

from services.linkvorschau import (
    ALLGEMEINE_BESCHREIBUNG,
    BESCHREIBUNG_HOECHSTENS,
    SUCHTEXT_HOECHSTENS,
    beitrag_adresse,
    beitrag_tags,
    ergebnis_tags,
    kuerzen,
    suchtext_aus_adresse,
)

META = re.compile(r'<meta (?:property|name)="([^"]+)" content="([^"]*)">')


def _werte(stueck: str) -> dict[str, str]:
    """Die Angaben, wie ein Crawler sie liest (Entitaeten aufgeloest)."""
    zeilen = stueck.strip().split("\n")
    werte = {}
    for zeile in zeilen:
        treffer = META.fullmatch(zeile)
        assert treffer, f"keine saubere meta-Zeile: {zeile!r}"
        werte[treffer.group(1)] = html.unescape(treffer.group(2))
    return werte


def test_beitrag_titel_text_und_adresse():
    werte = _werte(
        beitrag_tags(
            "Wärmepumpe lohnt sich auch im Altbau",
            "Auch alte Häuser\nlassen sich gut heizen.",
            "https://gutgesagt.example/beitrag/abc",
        )
    )
    assert werte == {
        "og:title": "Wärmepumpe lohnt sich auch im Altbau",
        "og:description": "Auch alte Häuser lassen sich gut heizen.",
        "twitter:description": "Auch alte Häuser lassen sich gut heizen.",
        "og:url": "https://gutgesagt.example/beitrag/abc",
    }


def test_beitrag_ohne_adresse_ohne_og_url():
    assert "og:url" not in _werte(beitrag_tags("Titel", "Text", None))


def test_beitrag_ohne_text_allgemeine_beschreibung():
    assert _werte(beitrag_tags("Titel", "  ", None))["og:description"] == (
        ALLGEMEINE_BESCHREIBUNG
    )


def test_beitrag_ohne_titel_keine_angaben():
    assert beitrag_tags("", "Text", None) is None
    assert beitrag_tags(None, "Text", None) is None


def test_langer_text_an_wortgrenze_gekuerzt():
    text = " ".join(["Wärmepumpe"] * 40)
    beschreibung = _werte(beitrag_tags("Titel", text, None))["og:description"]
    assert len(beschreibung) <= BESCHREIBUNG_HOECHSTENS
    assert beschreibung.endswith("Wärmepumpe…")
    assert len(beschreibung) > BESCHREIBUNG_HOECHSTENS - len("Wärmepumpe") - 2


def test_kuerzen_ohne_satzzeichen_vor_der_auslassung():
    assert kuerzen("eins zwei, drei vier", 12) == "eins zwei…"


def test_kuerzen_schneidet_ein_zu_langes_wort_hart():
    assert kuerzen("x" * 50, 10) == "x" * 9 + "…"


def test_kurzer_text_bleibt():
    assert kuerzen("kurz", 10) == "kurz"


@pytest.mark.parametrize(
    "boese",
    [
        '"><script>alert(1)</script>',
        "' onmouseover='alert(1)",
        '<!--# include virtual="/etc/passwd" -->',
        "a & b < c > d",
    ],
)
def test_titel_und_suchtext_maskiert(boese):
    for stueck in (beitrag_tags(boese, boese, None), ergebnis_tags(boese)):
        # Kein Zeichen, das Attribut, Tag oder SSI-Anweisung beenden oder beginnen kann.
        for zeile in stueck.strip().split("\n"):
            inhalt = re.fullmatch(r'<meta \w+="[^"]+" content="([^"]*)">', zeile)
            assert inhalt, zeile
            assert not set(inhalt.group(1)) & set("<>\"'")
        assert boese in _werte(stueck)["og:title"]


def test_steuerzeichen_entfernt():
    assert _werte(beitrag_tags("A\x00B\tC", "x\r\ny", None))["og:title"] == "A B C"


def test_ergebnis_titel_und_allgemeine_beschreibung():
    werte = _werte(ergebnis_tags("Wärmepumpe im Altbau"))
    assert werte == {
        "og:title": "Antworten auf: Wärmepumpe im Altbau",
        "og:description": ALLGEMEINE_BESCHREIBUNG,
        "twitter:description": ALLGEMEINE_BESCHREIBUNG,
    }


def test_ergebnis_suchtext_gekuerzt():
    titel = _werte(ergebnis_tags("Tempolimit " * 30))["og:title"]
    assert len(titel) <= len("Antworten auf: ") + SUCHTEXT_HOECHSTENS
    assert titel.endswith("…")


def test_ergebnis_ohne_suchtext_keine_angaben():
    assert ergebnis_tags("") is None
    assert ergebnis_tags("   ") is None


@pytest.mark.parametrize(
    ("roh", "suchtext"),
    [
        ("W%C3%A4rmepumpe%20im%20Altbau", "Wärmepumpe im Altbau"),
        ("W%C3%A4rmepumpe+im+Altbau", "Wärmepumpe im Altbau"),
        ("1%2B1", "1+1"),
        # Unkodiertes UTF-8 in der Adresse, von Starlette als Latin-1 gelesen
        ("Wärme".encode("utf-8").decode("latin-1"), "Wärme"),
        ("%FF", "�"),
        (None, ""),
    ],
)
def test_suchtext_aus_adresse(roh, suchtext):
    assert suchtext_aus_adresse(roh) == suchtext


def test_beitrag_adresse():
    assert (
        beitrag_adresse("https://gutgesagt.example/", "abc")
        == "https://gutgesagt.example/beitrag/abc"
    )
    assert beitrag_adresse(None, "abc") is None
