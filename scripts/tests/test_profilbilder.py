"""
Die Profilbilder (#437) stehen an drei Stellen: im Skript, das sie aus Fluent Emoji
erzeugt, im Frontend, das sie zur Wahl stellt, und als Dateien unter public/avatars.
Laufen sie auseinander, zeigt der Dialog ein kaputtes Bild oder eine Datei liegt
ohne Verwendung herum.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
SKRIPT = FRONTEND / "scripts/profilbilder_holen.py"
DIENST = FRONTEND / "src/app/services/profilbild.service.ts"
AVATARE = FRONTEND / "public/avatars"


def _skript() -> list[str]:
    return re.findall(r'\(\s*"([a-z0-9-]+\.png)",', SKRIPT.read_text())


def _frontend() -> list[str]:
    return re.findall(r"url: '/avatars/([a-z0-9-]+\.png)'", DIENST.read_text())


def test_skript_und_frontend_nennen_dieselben_bilder_in_derselben_reihenfolge():
    assert _skript() == _frontend()
    assert len(_frontend()) == 40


def test_jede_datei_ist_ein_angebotenes_bild_und_umgekehrt():
    dateien = {p.name for p in AVATARE.iterdir() if p.suffix != ".txt"}
    assert dateien == set(_frontend())


def test_bilder_sind_128_px_gross():
    for name in _frontend():
        kopf = (AVATARE / name).read_bytes()[:24]
        assert kopf[:8] == b"\x89PNG\r\n\x1a\n", name
        assert int.from_bytes(kopf[16:20]) == 128, name
        assert int.from_bytes(kopf[20:24]) == 128, name


def test_lizenz_liegt_neben_den_bildern():
    lizenz = (AVATARE / "FLUENT-EMOJI-LIZENZ.txt").read_text()
    assert "MIT License" in lizenz
    assert "Copyright (c) Microsoft Corporation." in lizenz
    commit = re.search(r'COMMIT = "([0-9a-f]{40})"', SKRIPT.read_text()).group(1)
    assert commit in lizenz
