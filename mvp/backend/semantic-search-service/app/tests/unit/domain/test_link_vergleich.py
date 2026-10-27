"""
Wann zwei Links als gleich gelten (#263).

Entscheidung des Maintainers vom 2026-10-26: gleich nach Bereinigung um
Tracking-Parameter, "www.", Schraegstrich am Ende und den Unterschied http/https.
Alles andere bleibt ein Unterschied.
"""

import re
from pathlib import Path

import pytest

from domain.link_vergleich import (
    HOST_TRACKING_PARAMETER,
    TRACKING_PARAMETER,
    TRACKING_PRAEFIXE,
    gleicher_link,
    vergleichsform,
    vorfilter_teile,
)

pytestmark = pytest.mark.unit


class TestGleicherLink:
    @pytest.mark.parametrize(
        "eingeworfen, vorhanden",
        [
            # http/https
            ("http://example.org/artikel", "https://example.org/artikel"),
            # www.
            ("https://www.example.org/artikel", "https://example.org/artikel"),
            # Schraegstrich am Ende
            ("https://example.org/artikel/", "https://example.org/artikel"),
            ("https://example.org/", "https://example.org"),
            # Tracking-Parameter, global und je Host
            (
                "https://www.instagram.com/reel/ABC/?igsh=xyz&stkn=1",
                "https://instagram.com/reel/ABC",
            ),
            (
                "https://example.org/artikel?utm_source=x&utm_medium=y",
                "https://example.org/artikel",
            ),
            (
                "https://www.youtube.com/watch?v=abc&si=TEILEN",
                "https://youtube.com/watch?v=abc",
            ),
            # Host ist ohnehin gross/klein-unabhaengig
            ("https://Example.ORG/artikel", "https://example.org/artikel"),
            # Alles zusammen
            (
                "http://WWW.example.org/artikel/?fbclid=abc",
                "https://example.org/artikel",
            ),
        ],
    )
    def test_gleicher_link_nach_bereinigung_gleich(self, eingeworfen, vorhanden):
        assert gleicher_link(eingeworfen, vorhanden)

    @pytest.mark.parametrize(
        "eingeworfen, vorhanden",
        [
            # Inhaltliche Parameter bleiben
            ("https://youtube.com/watch?v=abc", "https://youtube.com/watch?v=xyz"),
            # si ist nur auf YouTube Tracking, anderswo Inhalt
            ("https://example.org/?si=1", "https://example.org/?si=2"),
            # Pfade unterscheiden Gross- und Kleinschreibung
            ("https://example.org/Artikel", "https://example.org/artikel"),
            # Andere Subdomain ist ein anderer Host
            ("https://m.example.org/artikel", "https://example.org/artikel"),
            ("https://example.org/artikel", "https://example.org/artikel-2"),
            # Nur ein Schraegstrich am Ende faellt weg
            ("https://example.org/artikel//", "https://example.org/artikel"),
            # Userinfo und Anker sind kein Bereinigungsgrund
            ("https://jemand@example.org/artikel", "https://example.org/artikel"),
            ("https://example.org/artikel#teil", "https://example.org/artikel"),
        ],
    )
    def test_gleicher_link_sonst_verschieden(self, eingeworfen, vorhanden):
        assert not gleicher_link(eingeworfen, vorhanden)

    @pytest.mark.parametrize(
        "kein_link", [None, "", "kein link", "ftp://example.org/x"]
    )
    def test_gleicher_link_ohne_link_nie_gleich(self, kein_link):
        assert not gleicher_link(kein_link, kein_link)


class TestVergleichsform:
    def test_vergleichsform_ohne_schema_www_und_tracking(self):
        assert (
            vergleichsform("http://www.example.org/a/b/?utm_campaign=x&seite=2")
            == "example.org/a/b?seite=2"
        )

    def test_vergleichsform_kein_link_ist_none(self):
        assert vergleichsform("einfach Text") is None

    def test_vorfilter_teile_host_pfad_und_uebrige_parameter(self):
        assert vorfilter_teile(
            "https://jemand@www.youtube.com/watch/?v=abc&si=x&t=1#teil"
        ) == ["youtube.com/watch", "v=abc", "t=1"]

    def test_vorfilter_teile_kein_link_ist_none(self):
        assert vorfilter_teile("einfach Text") is None

    @pytest.mark.parametrize(
        "vorhanden",
        [
            "http://WWW.YouTube.com/watch/?v=abc&utm_source=x&t=1",
            "https://youtube.com/watch?v=abc&t=1",
        ],
    )
    def test_vorfilter_teile_stehen_in_jedem_gleichen_link(self, vorhanden):
        """Sonst verwirft die Datenbank einen gleichen Link schon im Vorfilter."""
        eingeworfen = "https://www.youtube.com/watch?v=abc&t=1&si=TEILEN"
        assert gleicher_link(eingeworfen, vorhanden)
        for teil in vorfilter_teile(eingeworfen):
            assert teil.lower() in vorhanden.lower()


FRONTEND_BEREINIGUNG = (
    Path(__file__).resolve().parents[6]
    / "frontend/gutgesagt-frontend/src/app/shared/url-bereinigen.ts"
)


def _ts_liste(quelltext: str, name: str) -> set:
    """Die Zeichenketten der Konstante ``name`` aus dem TypeScript-Quelltext."""
    block = re.search(rf"const {name}\b[^=]*=\s*\[(.*?)\];", quelltext, re.S)
    assert block, f"{name} nicht in url-bereinigen.ts gefunden"
    ohne_kommentare = re.sub(r"//[^\n]*", "", block.group(1))
    return set(re.findall(r"'([^']+)'", ohne_kommentare))


@pytest.mark.skipif(
    not FRONTEND_BEREINIGUNG.exists(), reason="Frontend nicht im Checkout"
)
def test_link_vergleich_tracking_wie_frontend():
    """Das Frontend entfernt beim Einwerfen dieselben Parameter, die hier wegfallen."""
    quelltext = FRONTEND_BEREINIGUNG.read_text(encoding="utf-8")

    assert _ts_liste(quelltext, "TRACKING_PARAMETER") == set(TRACKING_PARAMETER)
    assert _ts_liste(quelltext, "TRACKING_PRAEFIXE") == set(TRACKING_PRAEFIXE)
    assert _ts_liste(quelltext, "HOST_TRACKING_PARAMETER") == {
        wert
        for domains, parameter in HOST_TRACKING_PARAMETER
        for wert in (*domains, *parameter)
    }
