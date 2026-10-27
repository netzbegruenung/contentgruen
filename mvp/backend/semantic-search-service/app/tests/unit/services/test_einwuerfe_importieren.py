"""
Das Importskript mvp/scripts/manual/einwuerfe_importieren.py (#341): Liste lesen
und je Zeile einwerfen. Statt des BFF steht hier ein Client im Speicher; den Weg
ueber das echte BFF prueft tests/integration/test_einwuerfe_importieren.py.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
MANUAL = REPO_WURZEL / "mvp" / "scripts" / "manual"
SKRIPT = MANUAL / "einwuerfe_importieren.py"


@pytest.fixture(scope="module")
def skript():
    spec = importlib.util.spec_from_file_location("einwuerfe_importieren", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _datei(tmp_path, name, inhalt):
    pfad = tmp_path / name
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad


class TestCsvLesen:
    def test_link_und_hinweis_je_zeile(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "liste.csv",
            "link,hinweis\n"
            "https://example.org/a,Gute Zahl zur Wärmepumpe\n"
            "https://example.org/b,\n",
        )

        zeilen, fehler = skript.liste_lesen(pfad)

        assert fehler == []
        assert [(z.nummer, z.link, z.hinweis) for z in zeilen] == [
            (2, "https://example.org/a", "Gute Zahl zur Wärmepumpe"),
            (3, "https://example.org/b", None),
        ]

    def test_semikolon_und_ohne_hinweisspalte(self, skript, tmp_path):
        pfad = _datei(
            tmp_path, "liste.csv", "Link;Hinweis\nhttps://example.org/a;Zitat\n"
        )
        nur_link = _datei(tmp_path, "nur.csv", "link\n https://example.org/b \n")

        assert [(z.link, z.hinweis) for z in skript.liste_lesen(pfad)[0]] == [
            ("https://example.org/a", "Zitat")
        ]
        assert [(z.link, z.hinweis) for z in skript.liste_lesen(nur_link)[0]] == [
            ("https://example.org/b", None)
        ]

    def test_zeile_ohne_link_ist_fehler_leerzeile_nicht(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "liste.csv",
            "link,hinweis\n,nur ein Hinweis\n\nkein-link,x\nhttps://example.org/a,\n",
        )

        zeilen, fehler = skript.liste_lesen(pfad)

        assert [z.link for z in zeilen] == ["https://example.org/a"]
        assert [f.nummer for f in fehler] == [2, 4]

    def test_ohne_spalte_link_bricht_ab(self, skript, tmp_path):
        pfad = _datei(tmp_path, "liste.csv", "url,text\nhttps://example.org/a,x\n")

        with pytest.raises(skript.ListeUnlesbar, match="link"):
            skript.liste_lesen(pfad)


class TestMarkdownLesen:
    def test_listenpunkte_mit_link_und_hinweis(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "liste.md",
            "# Fundstücke\n"
            "\n"
            "Etwas Fließtext mit https://example.org/kein-punkt\n"
            "- https://example.org/a\n"
            "* https://example.org/b – Gute Zahl zur Wärmepumpe\n"
            "1. [Studie zum Altbau](https://example.org/c): Seite 3\n"
            "+ <https://example.org/d>\n",
        )

        zeilen, fehler = skript.liste_lesen(pfad)

        assert fehler == []
        assert [(z.nummer, z.link, z.hinweis) for z in zeilen] == [
            (4, "https://example.org/a", None),
            (5, "https://example.org/b", "Gute Zahl zur Wärmepumpe"),
            (6, "https://example.org/c", "Studie zum Altbau: Seite 3"),
            (7, "https://example.org/d", None),
        ]

    def test_listenpunkt_ohne_link_ist_fehler(self, skript, tmp_path):
        pfad = _datei(
            tmp_path, "liste.md", "- nur ein Gedanke\n- https://example.org/a\n"
        )

        zeilen, fehler = skript.liste_lesen(pfad)

        assert [z.link for z in zeilen] == ["https://example.org/a"]
        assert [f.nummer for f in fehler] == [1]


def test_beispieldateien_sind_lesbar_und_harmlos(skript):
    for name in ("einwuerfe_beispiel.csv", "einwuerfe_beispiel.md"):
        zeilen, fehler = skript.liste_lesen(MANUAL / name)

        assert zeilen and fehler == []
        assert all(
            z.link.startswith(("https://example.org/", "https://example.com/"))
            for z in zeilen
        )


class FangkorbImSpeicher:
    """Steht fuer das BFF: gleicher Link heisst hier wortgleich, das reicht fuer den Ablauf."""

    def __init__(self, skript, vorhanden=(), scheitert_bei=()):
        self.skript = skript
        self.einwuerfe = [
            {"id": f"alt-{i}", "url": link, "status": status}
            for i, (link, status) in enumerate(vorhanden)
        ]
        self.scheitert_bei = set(scheitert_bei)

    def gleiche_einwuerfe(self, link):
        return [e for e in self.einwuerfe if e["url"] == link]

    def einwerfen(self, link, hinweis):
        if link in self.scheitert_bei:
            raise self.skript.ApiFehler(422, "zu lang")
        einwurf = {
            "id": f"neu-{len(self.einwuerfe)}",
            "url": link,
            "content": hinweis,
            "status": "open",
        }
        self.einwuerfe.append(einwurf)
        return einwurf["id"]


def _zeilen(skript, *eintraege):
    return [
        skript.Zeile(nummer, link, hinweis)
        for nummer, (link, hinweis) in enumerate(eintraege, start=2)
    ]


class TestImportieren:
    def test_legt_je_zeile_einen_einwurf_mit_hinweis_an(self, skript):
        fangkorb = FangkorbImSpeicher(skript)
        zeilen = _zeilen(
            skript, ("https://example.org/a", "Zitat"), ("https://example.org/b", None)
        )

        bericht = skript.importieren(zeilen, fangkorb)

        assert [(e["url"], e["content"]) for e in fangkorb.einwuerfe] == [
            ("https://example.org/a", "Zitat"),
            ("https://example.org/b", None),
        ]
        assert [z.nummer for z, _ in bericht.angelegt] == [2, 3]
        assert bericht.uebersprungen == [] and bericht.fehlgeschlagen == []

    def test_gleicher_link_wird_uebersprungen_und_gemeldet(self, skript):
        fangkorb = FangkorbImSpeicher(
            skript, vorhanden=[("https://example.org/a", "discarded")]
        )
        zeilen = _zeilen(skript, ("https://example.org/a", "nochmal"))

        bericht = skript.importieren(zeilen, fangkorb)

        assert len(fangkorb.einwuerfe) == 1
        ((zeile, grund),) = bericht.uebersprungen
        assert zeile.nummer == 2
        assert "alt-0" in grund and "verworfen" in grund

    def test_gleicher_link_zweimal_in_der_liste_nur_einmal(self, skript):
        fangkorb = FangkorbImSpeicher(skript)
        zeilen = _zeilen(
            skript, ("https://example.org/a", None), ("https://example.org/a", None)
        )

        bericht = skript.importieren(zeilen, fangkorb)

        assert len(fangkorb.einwuerfe) == 1
        assert [z.nummer for z, _ in bericht.uebersprungen] == [3]

    def test_trockenlauf_legt_nichts_an_meldet_aber_dasselbe(self, skript):
        fangkorb = FangkorbImSpeicher(
            skript, vorhanden=[("https://example.org/a", "open")]
        )
        zeilen = _zeilen(
            skript,
            ("https://example.org/a", None),
            ("https://example.org/b", None),
            ("https://example.org/b", None),
        )

        bericht = skript.importieren(zeilen, fangkorb, trockenlauf=True)

        assert len(fangkorb.einwuerfe) == 1
        assert [(z.nummer, einwurf_id) for z, einwurf_id in bericht.angelegt] == [
            (3, None)
        ]
        assert [z.nummer for z, _ in bericht.uebersprungen] == [2, 4]

    def test_abgelehnte_zeile_haelt_den_rest_nicht_auf(self, skript):
        fangkorb = FangkorbImSpeicher(skript, scheitert_bei=["https://example.org/a"])
        zeilen = _zeilen(
            skript, ("https://example.org/a", None), ("https://example.org/b", None)
        )

        bericht = skript.importieren(zeilen, fangkorb)

        assert [z.nummer for z, _ in bericht.fehlgeschlagen] == [2]
        assert [z.nummer for z, _ in bericht.angelegt] == [3]
