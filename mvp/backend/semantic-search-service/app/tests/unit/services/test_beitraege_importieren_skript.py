"""
Das Skript mvp/scripts/manual/beitraege_importieren.py (#592): Startbestand aus
Markdown lesen und als Kommentare anlegen, Beitraege per Liste entfernen. Statt
des BFF steht hier ein Bestand im Speicher; den Aufruf ueber das echte BFF prueft
tests/integration/api/test_beitraege_importieren_bff.py.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
MANUAL = REPO_WURZEL / "mvp" / "scripts" / "manual"
SKRIPT = MANUAL / "beitraege_importieren.py"


@pytest.fixture(scope="module")
def skript():
    spec = importlib.util.spec_from_file_location("beitraege_importieren", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _datei(tmp_path, inhalt, name="bestand.md"):
    pfad = tmp_path / name
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad


# Gliederung wie im Entwurf des Startbestands: Block, nummerierte Aussage in
# Anfuehrungszeichen, je Kommentar eine ###-Ueberschrift und fette Felder.
ENTWURF = """\
# Startbestand: Entwurf

## Stand

### Nicht zum Bestand
**Titel:** Gehoert zur Einleitung

---

# 1. Klima und Energie

## 1.1 „Windräder töten die Vögel!“

### (a) Kommentarspalte

**Titel:** Wer Vögel schützen will, fängt bei Glasscheiben an

**Kurz:** Kurz und knapp.

**Mittel:** Der Haupttext.

**Herkunft:** https://example.org/voegel – Übersicht der Gefahren für Vögel.
geprüft: ja, 07.11.2026. Stelle: „Mehr als 100 Millionen“.

### (b) Sachlich

**Titel:** Windkraft und Vogelschutz passen zusammen

**Mittel:** Erster Satz.

**Lang:** Erste Zeile.
Zweite Zeile.

**Herkunft:** https://example.org/a – Erste Herkunft. geprüft: ja
Zweite Herkunft (Anteil Erneuerbare): https://example.org/b – Zweite Herkunft. geprüft: ja, Stelle „x“
Hinweis Gegenlesen: Satz bei Bedarf streichen.
"""


class TestDateiLesen:
    def test_gliederung_des_entwurfs(self, skript, tmp_path):
        kommentare, fehler = skript.datei_lesen(_datei(tmp_path, ENTWURF))

        assert fehler == []
        a, b = kommentare
        assert (a.zeile, a.aussage, a.titel, a.kurz, a.mittel, a.lang) == (
            14,
            "Windräder töten die Vögel!",
            "Wer Vögel schützen will, fängt bei Glasscheiben an",
            "Kurz und knapp.",
            "Der Haupttext.",
            None,
        )
        # Pruefvermerke gehoeren nicht in die Beschreibung der Herkunft.
        assert a.herkuenfte == [
            skript.Herkunft(
                "https://example.org/voegel", "Übersicht der Gefahren für Vögel."
            )
        ]
        assert b.aussage == a.aussage
        assert b.lang == "Erste Zeile.\nZweite Zeile."
        assert b.herkuenfte == [
            skript.Herkunft("https://example.org/a", "Erste Herkunft."),
            skript.Herkunft("https://example.org/b", "Zweite Herkunft."),
        ]

    def test_format_mit_benannten_ueberschriften(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "## Aussage: Das E-Auto ist schlechter fürs Klima.\n"
            "### Kommentar: Über sein Leben gerechnet ist das E-Auto klimafreundlicher\n"
            "- kurz: Kurz.\n"
            "- mittel: Mittel.\n"
            "- herkunft: https://example.org/e-auto | Studie zur Klimabilanz\n"
            "- herkunft: <https://example.org/zwei>\n"
            "- herkunft: [Bericht](https://example.org/drei) aus 2024\n"
            "- zweck: eigene_leute\n"
            "- stil: Sachlich\n",
        )

        (k,), fehler = skript.datei_lesen(pfad)

        assert fehler == []
        assert k.titel == "Über sein Leben gerechnet ist das E-Auto klimafreundlicher"
        assert [(h.link, h.beschreibung) for h in k.herkuenfte] == [
            ("https://example.org/e-auto", "Studie zur Klimabilanz"),
            ("https://example.org/zwei", None),
            ("https://example.org/drei", "Bericht aus 2024"),
        ]
        anfrage = skript.anfrage(k)
        assert anfrage["commentary"]["zweck"] == "eigene_leute"
        assert anfrage["commentary"]["style"] == "sachlich"

    def test_varianten_die_beim_schreiben_vorkommen(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "## 9. Hinweise\n"
            "### Offene Fragen\n"
            "**Titel:** Gehoert nicht zum Bestand\n"
            "## 2.1 „Eine Aussage in Anführungszeichen“\n"
            "### (a)\n"
            "**Titel**: Doppelpunkt hinter dem Fettdruck\n\n"
            "**Mittel**: Text.\n\n"
            "#### Quellen\n"
            "**Herkunft**: https://de.wikipedia.org/wiki/Rotmilan_(Art) – Artikel.\n"
            "Herkunft: [Bericht](https://example.org/a_(b)) aus 2024\n"
            "**Herkunft:** keine Zahl, Allgemeinwissen. Keine Herkunft nötig.\n",
        )

        (k,), fehler = skript.datei_lesen(pfad)

        assert fehler == []
        assert k.aussage == "Eine Aussage in Anführungszeichen"
        assert (k.titel, k.mittel) == ("Doppelpunkt hinter dem Fettdruck", "Text.")
        assert [(h.link, h.beschreibung) for h in k.herkuenfte] == [
            ("https://de.wikipedia.org/wiki/Rotmilan_(Art)", "Artikel."),
            ("https://example.org/a_(b)", "Bericht aus 2024"),
        ]

    def test_laengen_und_pflichtfelder_alle_auf_einmal(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "## Aussage: Zu kurz\n"
            "### (a)\n"
            f"**Kurz:** {'k' * 281}\n\n"
            f"**Lang:** {'l' * 2001}\n\n"
            "**Herkunft:** [Quelle fehlt]\n"
            "### (b)\n"
            f"**Titel:** {'t' * 121}\n\n"
            f"**Mittel:** {'m' * 501}\n\n"
            "**Stil:** bissig\n",
        )

        kommentare, fehler = skript.datei_lesen(pfad)

        assert kommentare == []
        assert [f.zeile for f in fehler] == [2, 8]
        assert fehler[0].grund == (
            "Aussage hat 7 Zeichen, erlaubt 10-1000; kein Titel; keine Mittelfassung; "
            "Kurzfassung hat 281 Zeichen, erlaubt 280; "
            "Langfassung hat 2001 Zeichen, erlaubt 2000; "
            "Herkunft in Zeile 7 ohne http(s)-Link"
        )
        assert "Titel hat 121 Zeichen" in fehler[1].grund
        assert "Mittelfassung hat 501 Zeichen" in fehler[1].grund
        assert "Stil bissig geht nur beim Zweck eigene_leute" in fehler[1].grund

    def test_genau_an_den_grenzen_ist_gut(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            f"## Aussage: {'a' * 10}\n### x\n**Titel:** {'t' * 120}\n\n"
            f"**Kurz:** {'k' * 280}\n\n**Mittel:** {'m' * 500}\n\n**Lang:** {'l' * 2000}\n",
        )

        kommentare, fehler = skript.datei_lesen(pfad)

        assert fehler == [] and len(kommentare) == 1

    def test_anfrage_wie_das_formular(self, skript, tmp_path):
        (k, _), _ = skript.datei_lesen(_datei(tmp_path, ENTWURF))

        assert skript.anfrage(k) == {
            "commentary": {
                "title": "Wer Vögel schützen will, fängt bei Glasscheiben an",
                "text": "Der Haupttext.",
                "short_text": "Kurz und knapp.",
                "references": [],
            },
            "references": [
                {
                    "reference_string": "https://example.org/voegel",
                    "description": "Übersicht der Gefahren für Vögel.",
                }
            ],
            "statement_text": "Windräder töten die Vögel!",
            "cc0_wortlaut": "2026-11-02-formular",
        }

    def test_beispieldatei_ist_fehlerfrei(self, skript):
        kommentare, fehler = skript.datei_lesen(MANUAL / "beitraege_beispiel.md")

        assert fehler == [] and len(kommentare) == 3

    def test_cc0_kennung_kennt_der_dienst(self, skript):
        from domain.cc0_hinweis import CC0_WORTLAUTE

        assert skript.CC0_WORTLAUT in CC0_WORTLAUTE


class TestListeLesen:
    def test_typ_und_id_je_zeile(self, skript, tmp_path):
        pfad = _datei(
            tmp_path,
            "# Altbestand vom Test\n"
            "commentary 525F4E66-0000-4000-8000-000000000001  # prüfen\n"
            "\n"
            "statement 525f4e66-0000-4000-8000-000000000002\n"
            "post keine-id\n"
            "generic_text\n"
            "post 525f4e66-0000-4000-8000-000000000003\n",
            name="liste.txt",
        )

        eintraege, fehler = skript.liste_lesen(pfad)

        assert [(e.zeile, e.typ, e.id) for e in eintraege] == [
            (2, "commentary", "525f4e66-0000-4000-8000-000000000001"),
            (7, "post", "525f4e66-0000-4000-8000-000000000003"),
        ]
        assert [f.zeile for f in fehler] == [4, 5, 6]


class Speicher:
    """Ein Bestand im Speicher mit den Antworten des Dienstes."""

    def __init__(self, skript, antworten=None, fehler=None):
        self.skript = skript
        self.antworten = list(antworten or [])
        self.fehler = list(fehler or [])
        self.angelegt = []
        self.entfernt = []
        # ID -> (Typ, Titel) der Beitraege, die die Ansicht zeigt.
        self.beitraege = {}

    def kommentar_anlegen(self, daten):
        if self.fehler:
            f = self.fehler.pop(0)
            if f is not None:
                raise f
        self.angelegt.append(daten)
        if self.antworten:
            return self.antworten.pop(0)
        return {
            "id": f"k{len(self.angelegt)}",
            "statement_id": "a1",
            "statement_text": daten["statement_text"],
            "verknuepft": True,
        }

    def ansehen(self, beitrag_id):
        if beitrag_id not in self.beitraege:
            return None
        typ, titel = self.beitraege[beitrag_id]
        return {"id": beitrag_id, "content_type": typ, "title": titel}

    def entfernen(self, typ, beitrag_id):
        if beitrag_id not in self.beitraege:
            raise self.skript.ApiFehler(404, "Content not found or already deleted")
        self.entfernt.append((typ, beitrag_id))


def _kommentare(skript, tmp_path):
    return skript.datei_lesen(_datei(tmp_path, ENTWURF))[0]


class TestImportieren:
    def test_trockenlauf_ruft_nichts_auf(self, skript, tmp_path):
        bericht = skript.importieren(_kommentare(skript, tmp_path), None)

        assert [z for z, _ in bericht.angelegt] == [14, 25]
        assert bericht.fehlgeschlagen == [] and bericht.uebersprungen == []

    def test_anlegen_und_vorhandene_aussage_nennen(self, skript, tmp_path):
        speicher = Speicher(
            skript,
            antworten=[
                {
                    "id": "k1",
                    "statement_id": "a1",
                    "statement_text": "Windräder töten die Vögel!",
                    "verknuepft": True,
                },
                {
                    "id": "k2",
                    "statement_id": "a1",
                    "statement_text": "Windräder töten Vögel",
                    "verknuepft": True,
                },
            ],
        )
        bericht = skript.importieren(
            _kommentare(skript, tmp_path), speicher, ausfuehren=True
        )

        assert len(speicher.angelegt) == 2
        assert bericht.angelegt[0][1].startswith("angelegt als k1 an Aussage a1:")
        assert "an vorhandene Aussage: Windräder töten Vögel" in bericht.angelegt[1][1]

    def test_dublette_wird_gemeldet_nicht_uebergangen(self, skript, tmp_path):
        speicher = Speicher(
            skript,
            antworten=[
                {
                    "id": "alt",
                    "verknuepft": False,
                    "vorhanden": {"titel": "Schon da", "eigen": False},
                }
            ],
        )

        bericht = skript.importieren(
            _kommentare(skript, tmp_path)[:1], speicher, ausfuehren=True
        )

        assert "trotz_dublette_von" not in speicher.angelegt[0]
        assert bericht.angelegt == []
        ((zeile, grund),) = bericht.uebersprungen
        assert zeile == 14 and "aehnlicher Kommentar schon da (alt: Schon da)" in grund

    def test_nicht_verknuepft_ist_fehler(self, skript, tmp_path):
        speicher = Speicher(skript, antworten=[{"id": "k1", "verknuepft": False}])

        bericht = skript.importieren(
            _kommentare(skript, tmp_path)[:1], speicher, ausfuehren=True
        )

        assert "nicht mit der Aussage verknuepft" in bericht.fehlgeschlagen[0][1]

    def test_eigener_vorhandener_wird_an_die_aussage_gehaengt(self, skript, tmp_path):
        speicher = Speicher(
            skript,
            antworten=[
                # Aelterer Dienst: Dublette in den flachen Feldern von vor #541.
                {
                    "id": "alt",
                    "verknuepft": False,
                    "dublette": True,
                    "vorhanden_titel": "Aus dem ersten Lauf",
                    "vorhanden_eigen": True,
                },
                {"id": "alt", "statement_id": "a1", "verknuepft": True},
            ],
        )

        bericht = skript.importieren(
            _kommentare(skript, tmp_path)[:1], speicher, ausfuehren=True
        )

        erster, zweiter = speicher.angelegt
        assert "vorhanden_nehmen" not in erster
        assert zweiter["vorhanden_nehmen"] == "alt"
        assert "trotz_dublette_von" not in zweiter
        assert bericht.angelegt == [] and bericht.fehlgeschlagen == []
        ((_, grund),) = bericht.uebersprungen
        assert "eigener aehnlicher Kommentar schon da" in grund
        assert "an Aussage a1 gehaengt" in grund

    def test_stundenlimit_beendet_den_lauf(self, skript, tmp_path):
        limit = skript.ApiFehler(429, "Rate limit exceeded")
        speicher = Speicher(skript, fehler=[limit] * skript.VERSUCHE_BEI_LIMIT)
        gewartet = []

        bericht = skript.importieren(
            _kommentare(skript, tmp_path),
            speicher,
            ausfuehren=True,
            warten=gewartet.append,
        )

        assert len(gewartet) == skript.VERSUCHE_BEI_LIMIT - 1
        assert speicher.angelegt == []
        assert [z for z, _ in bericht.fehlgeschlagen] == [14, 25]
        assert all("nicht versucht: Rate-Limit" in g for _, g in bericht.fehlgeschlagen)

    def test_rate_limit_wartet_und_versucht_erneut(self, skript, tmp_path):
        speicher = Speicher(
            skript, fehler=[skript.ApiFehler(429, "Rate limit exceeded")]
        )
        gewartet = []

        bericht = skript.importieren(
            _kommentare(skript, tmp_path)[:1],
            speicher,
            ausfuehren=True,
            warten=gewartet.append,
        )

        assert gewartet == [skript.WARTEN_NACH_LIMIT]
        assert len(bericht.angelegt) == 1

    def test_aelterer_dienst_ohne_cc0_kennung(self, skript, tmp_path):
        speicher = Speicher(
            skript,
            fehler=[
                skript.ApiFehler(
                    422,
                    "Value error, Unbekannter Wortlaut des CC0-Hinweises: "
                    "2026-11-02-formular",
                )
            ],
        )

        bericht = skript.importieren(
            _kommentare(skript, tmp_path), speicher, ausfuehren=True
        )

        # Einmal abgelehnt, danach fuer alle ohne Kennung und so gemeldet.
        assert [d["cc0_wortlaut"] for d in speicher.angelegt] == [None, None]
        assert all(
            notiz.endswith("(ohne CC0-Kennung)") for _, notiz in bericht.angelegt
        )

    def test_abgelehnter_haelt_den_rest_nicht_auf(self, skript, tmp_path):
        speicher = Speicher(skript, fehler=[skript.ApiFehler(400, "kaputt"), None])

        bericht = skript.importieren(
            _kommentare(skript, tmp_path), speicher, ausfuehren=True
        )

        assert [z for z, _ in bericht.fehlgeschlagen] == [14]
        assert [z for z, _ in bericht.angelegt] == [25]

    def test_ohne_anmeldung_bricht_ab(self, skript, tmp_path):
        speicher = Speicher(skript, fehler=[skript.ApiFehler(401, "nicht angemeldet")])

        with pytest.raises(skript.ApiFehler):
            skript.importieren(_kommentare(skript, tmp_path), speicher, ausfuehren=True)


class TestEntfernen:
    def _eintraege(self, skript):
        return [
            skript.Eintrag(1, "commentary", "id-1"),
            skript.Eintrag(2, "post", "id-2"),
        ]

    def test_trockenlauf_zeigt_titel_und_entfernt_nichts(self, skript):
        speicher = Speicher(skript)
        speicher.beitraege = {"id-1": ("commentary", "Ein alter Kommentar")}

        bericht = skript.entfernen(self._eintraege(skript), speicher)

        assert speicher.entfernt == []
        assert bericht.angelegt == [
            (1, "wuerde entfernt: commentary id-1 „Ein alter Kommentar“")
        ]
        assert bericht.uebersprungen == [(2, "nicht gefunden oder gesperrt: post id-2")]

    def test_entfernen_und_fehlende_melden(self, skript):
        speicher = Speicher(skript)
        speicher.beitraege = {"id-1": ("commentary", "x")}

        bericht = skript.entfernen(self._eintraege(skript), speicher, ausfuehren=True)

        assert speicher.entfernt == [("commentary", "id-1")]
        assert bericht.uebersprungen == [
            (2, "nicht gefunden oder schon entfernt: post id-2")
        ]

    def test_typ_muss_zum_beitrag_passen(self, skript):
        speicher = Speicher(skript)
        speicher.beitraege = {"id-1": ("commentary", "x"), "id-2": ("commentary", "y")}

        bericht = skript.entfernen(self._eintraege(skript), speicher, ausfuehren=True)

        assert speicher.entfernt == [("commentary", "id-1")]
        assert bericht.fehlgeschlagen == [
            (2, "Typ passt nicht, der Beitrag ist commentary: post id-2")
        ]


class TestAufruf:
    def test_trockenlauf_braucht_weder_server_noch_passwort(
        self, skript, tmp_path, capsys
    ):
        def kein_server(adresse):
            raise AssertionError("Trockenlauf darf keinen Server ansprechen")

        assert skript.main([str(_datei(tmp_path, ENTWURF))], kein_server) == 0
        assert "Trockenlauf, wuerden angelegt: 2" in capsys.readouterr().out

    def test_fehler_in_der_datei_gibt_exit_1(self, skript, tmp_path):
        pfad = _datei(
            tmp_path, "## Aussage: Eine Aussage ohne Kommentarfelder\n### x\n"
        )

        assert skript.main([str(pfad)]) == 1

    def test_ausfuehren_braucht_eine_anmeldung(self, skript, tmp_path, monkeypatch):
        monkeypatch.delenv("GUTGESAGT_SITZUNG", raising=False)
        with pytest.raises(SystemExit):
            skript.main([str(_datei(tmp_path, ENTWURF)), "--ausfuehren"])

    def test_mit_sitzung_aus_datei(self, skript, tmp_path, capsys, monkeypatch):
        monkeypatch.delenv("GUTGESAGT_SITZUNG", raising=False)
        sitzung = _datei(tmp_path, "geheimer-wert\n", name="sitzung.txt")
        gebaut = []

        class Bff(skript.BffBestand):
            def __init__(self, adresse):
                super().__init__(adresse)
                gebaut.append(self)

            def wer(self):
                return {"userName": "Startkonto 1", "isAdmin": False}

            def kommentar_anlegen(self, daten):
                return {"id": "k", "statement_id": "a", "verknuepft": True}

        aufruf = [str(_datei(tmp_path, ENTWURF)), "--sitzung-datei", str(sitzung)]
        aufruf += ["--adresse", "https://gutgesagt.example.org", "--ausfuehren"]

        assert skript.main(aufruf, Bff) == 0

        assert gebaut[0]._kopfzeilen()["Cookie"] == "GutGesagtAuthCookie=geheimer-wert"
        ausgabe = capsys.readouterr()
        assert "Angemeldet als Startkonto 1" in ausgabe.out
        assert "geheimer-wert" not in ausgabe.out + ausgabe.err

    def test_entfernen_ohne_admin_bricht_vor_dem_ersten_eintrag_ab(
        self, skript, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setenv("GUTGESAGT_SITZUNG", "wert")
        liste = _datei(
            tmp_path, "commentary 525f4e66-0000-4000-8000-000000000001\n", "l.txt"
        )

        class Bff(skript.BffBestand):
            def wer(self):
                return {"userName": "Startkonto 1", "isAdmin": False}

            def ansehen(self, beitrag_id):
                raise AssertionError("ohne Admin nichts ansehen")

        assert skript.main([str(liste), "--entfernen"], Bff) == 2
        assert "Admin-Konto" in capsys.readouterr().err

    def test_nicht_email_und_sitzung_zugleich(self, skript, tmp_path, monkeypatch):
        monkeypatch.setenv("GUTGESAGT_SITZUNG", "wert")
        with pytest.raises(SystemExit):
            skript.main([str(_datei(tmp_path, ENTWURF)), "--email", "a@example.org"])


class TestSitzung:
    @pytest.mark.parametrize(
        "eingabe, cookie",
        [
            ("  wert\n", "GutGesagtAuthCookie=wert"),
            ("GutGesagtAuthCookie=wert", "GutGesagtAuthCookie=wert"),
            (
                "Cookie: GutGesagtAuthCookie=wert; GutGesagtAuthCookieC1=mehr",
                "GutGesagtAuthCookie=wert; GutGesagtAuthCookieC1=mehr",
            ),
        ],
    )
    def test_wert_oder_ganze_cookie_zeile(self, skript, eingabe, cookie):
        bff = skript.BffBestand("https://gutgesagt.example.org")

        bff.sitzung_nutzen(eingabe)

        assert bff._kopfzeilen()["Cookie"] == cookie

    @pytest.mark.parametrize("eingabe", ["", "  ", "a\nb", "a\rb"])
    def test_leer_oder_mit_umbruch_abgelehnt(self, skript, eingabe):
        with pytest.raises(skript.ApiFehler):
            skript.BffBestand("https://x.example.org").sitzung_nutzen(eingabe)

    def test_passwort_nur_verschluesselt(self, skript, tmp_path):
        assert (
            skript.main(
                [str(_datei(tmp_path, ENTWURF)), "--adresse", "http://example.org"]
            )
            == 2
        )
