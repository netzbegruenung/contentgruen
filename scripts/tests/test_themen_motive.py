"""
Die Motive der Themen (Album in "Meine Beitraege") stehen an drei Stellen: im Feld
"motiv" von domain/themen.json, als Dateien unter public/themen und, fuer die
Fluent-Motive, im Skript, das sie holt. Laufen sie auseinander, zeigt ein Themenkopf
ein kaputtes Bild oder eine Datei liegt ohne Verwendung herum.
"""

import json
import pathlib
import re
import xml.etree.ElementTree as ET

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
SKRIPT = FRONTEND / "scripts/themen_motive_holen.py"
LISTE = WURZEL / "mvp/backend/semantic-search-service/app/domain/themen.json"
ALBUM = FRONTEND / "src/app/meine-beitraege/album/album.ts"
BILDER = FRONTEND / "public/themen"
SVG = "{http://www.w3.org/2000/svg}svg"

# Kein Fluent-Motiv: eigene Zeichnung, Herkunft in HINWEIS-EUROPA.txt.
EIGENE = {"europa.svg"}


def _liste() -> dict[str, str]:
    return {e["schluessel"]: e["motiv"] for e in json.loads(LISTE.read_text())}


def _ohne_thema() -> str:
    return re.search(r"motiv: '(themen/[a-z-]+\.svg)'", ALBUM.read_text()).group(1)


def _skript() -> list[str]:
    return re.findall(r'\(\s*"([a-z0-9-]+\.svg)",', SKRIPT.read_text())


def test_jedes_thema_hat_ein_motiv_unter_public():
    for schluessel, motiv in _liste().items():
        assert motiv, schluessel
        assert (FRONTEND / "public" / motiv).is_file(), motiv


def test_jede_datei_ist_ein_motiv_und_umgekehrt():
    verwendet = {pathlib.PurePath(m).name for m in _liste().values()}
    verwendet.add(pathlib.PurePath(_ohne_thema()).name)
    dateien = {p.name for p in BILDER.iterdir() if p.suffix == ".svg"}
    assert dateien == verwendet
    assert set(_skript()) == verwendet - EIGENE


def test_motive_sind_svg_ohne_skript_und_mit_quellhinweis():
    for datei in BILDER.glob("*.svg"):
        text = datei.read_text()
        erwartet = "<!-- Eigenes Werk" if datei.name in EIGENE else "<!-- Fluent Emoji"
        assert text.startswith(erwartet), datei.name
        wurzel = ET.fromstring(text.split("-->", 1)[1])
        assert wurzel.tag == SVG, datei.name
        assert wurzel.get("viewBox") == "0 0 32 32", datei.name
        assert "<script" not in text and "href" not in text, datei.name


def test_europa_nutzt_die_farben_des_emblems_und_zwoelf_sterne():
    wurzel = ET.fromstring((BILDER / "europa.svg").read_text().split("-->", 1)[1])
    flagge = wurzel.find("{http://www.w3.org/2000/svg}rect")
    assert flagge.get("fill") == "#003399"
    assert float(flagge.get("width")) / float(flagge.get("height")) == 1.5
    sterne = wurzel.find("{http://www.w3.org/2000/svg}g")
    assert sterne.get("fill") == "#FFCC00"
    assert len(sterne.findall("{http://www.w3.org/2000/svg}polygon")) == 12


def test_lizenz_und_hinweis_liegen_neben_den_bildern_und_stehen_in_copyright():
    lizenz = (BILDER / "FLUENT-EMOJI-LIZENZ.txt").read_text()
    assert "MIT License" in lizenz
    assert "Copyright (c) Microsoft Corporation." in lizenz
    commit = re.search(r'COMMIT = "([0-9a-f]{40})"', SKRIPT.read_text()).group(1)
    assert commit in lizenz
    hinweis = (BILDER / "HINWEIS-EUROPA.txt").read_text()
    assert "https://european-union.europa.eu/legal-notice_en" in hinweis
    copyright_text = (WURZEL / "COPYRIGHT").read_text()
    assert "public/themen/" in copyright_text
    assert "HINWEIS-EUROPA.txt" in copyright_text
