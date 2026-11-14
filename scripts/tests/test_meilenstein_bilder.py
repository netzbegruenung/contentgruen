"""
Die Motive der Meilensteine (#351) stehen an drei Stellen: im Skript, das sie aus
Fluent Emoji holt, in der Liste der Meilensteine im Backend und als Dateien unter
public/meilensteine. Laufen sie auseinander, zeigt das Medaillon ein kaputtes Bild
oder eine Datei liegt ohne Verwendung herum.
"""

import pathlib
import re
import xml.etree.ElementTree as ET

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
SKRIPT = FRONTEND / "scripts/meilensteine_holen.py"
DOMAENE = WURZEL / "mvp/backend/semantic-search-service/app/domain/meilensteine.py"
BILDER = FRONTEND / "public/meilensteine"


def _skript() -> list[str]:
    return re.findall(r'\(\s*"([a-z0-9-]+\.svg)",', SKRIPT.read_text())


def _domaene() -> list[str]:
    return re.findall(r'bild=_bild\("([a-z0-9-]+\.svg)"\)', DOMAENE.read_text())


def test_skript_und_backend_nennen_dieselben_bilder():
    assert sorted(_skript()) == sorted(_domaene())
    assert len(_domaene()) == len(set(_domaene()))


def test_jede_datei_ist_ein_motiv_und_umgekehrt():
    dateien = {p.name for p in BILDER.iterdir() if p.suffix != ".txt"}
    assert dateien == set(_domaene())


def test_motive_sind_svg_ohne_skript_und_mit_quellhinweis():
    for name in _domaene():
        text = (BILDER / name).read_text()
        assert text.startswith("<!-- Fluent Emoji"), name
        wurzel = ET.fromstring(text.split("-->", 1)[1])
        assert wurzel.tag == "{http://www.w3.org/2000/svg}svg", name
        assert "<script" not in text and "href" not in text, name


def test_lizenz_liegt_neben_den_bildern_und_steht_in_copyright():
    lizenz = (BILDER / "FLUENT-EMOJI-LIZENZ.txt").read_text()
    assert "MIT License" in lizenz
    assert "Copyright (c) Microsoft Corporation." in lizenz
    commit = re.search(r'COMMIT = "([0-9a-f]{40})"', SKRIPT.read_text()).group(1)
    assert commit in lizenz
    assert "public/meilensteine/" in (WURZEL / "COPYRIGHT").read_text()
