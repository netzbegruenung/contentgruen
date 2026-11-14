"""
Symbole der App: Jede Datei, die index.html (Favicons, apple-touch-icon, og:image) oder das
Manifest nennt, liegt unter public/. nginx liefert Bilder mit "expires 1y" aus; ein
geaendertes Symbol bekommt deshalb einen neuen Dateinamen, und ein vergessener Verweis darauf
faellt hier auf statt erst als fehlendes Symbol auf dem Handy.
"""

import json
import pathlib
import re

from PIL import Image

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
PUBLIC = FRONTEND / "public"
INDEX = FRONTEND / "src/index.html"
MANIFEST = PUBLIC / "manifest.webmanifest"
PRODUKTION = "https://gutgesagt.netzbegruenung.de/"

LINK = re.compile(r'<link\s+rel="(?:icon|apple-touch-icon|manifest)"[^>]*\shref="([^"]+)"')
OG_BILD = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"')


def _verweise_index() -> list[str]:
    html = INDEX.read_text(encoding="utf-8")
    pfade = LINK.findall(html)
    pfade += [b[len(PRODUKTION) :] for b in OG_BILD.findall(html) if b.startswith(PRODUKTION)]
    return pfade


def _verweise_manifest() -> list[str]:
    return [i["src"] for i in json.loads(MANIFEST.read_text(encoding="utf-8"))["icons"]]


def test_verweise_gefunden():
    # Sonst prueften die Tests unten nach einer Umformatierung still nichts mehr
    assert len(_verweise_index()) >= 5
    assert len(_verweise_manifest()) >= 3


def test_jede_genannte_symboldatei_existiert():
    fehlend = [p for p in _verweise_index() + _verweise_manifest() if not (PUBLIC / p).is_file()]
    assert not fehlend, f"genannt, aber nicht unter public/: {fehlend}"


def test_logo_im_kopf_mit_neuem_namen_und_vorhanden():
    # Das Logo im Kopf und auf "Über": dieselbe Cache-Regel wie die Symbole
    vorlagen = list((FRONTEND / "src/app").rglob("*.html"))
    pfade = {m for v in vorlagen for m in re.findall(r'src="(marke/[^"]+)"', v.read_text(encoding="utf-8"))}
    assert "marke/logo-v2.svg" in pfade
    assert "marke/logo.svg" not in pfade
    assert "marke/logo-v2.svg" in _verweise_index()
    fehlend = sorted(p for p in pfade if not (PUBLIC / p).is_file())
    assert not fehlend, f"genannt, aber nicht unter public/: {fehlend}"


def test_markendateien_im_code_vorhanden():
    # Auch Pfade in TypeScript, etwa das Bild im Band des Home-Hinweises (rundgang-daten.ts)
    pfade = {
        m.lstrip("/")
        for d in (FRONTEND / "src/app").rglob("*.ts")
        for m in re.findall(r"'(/?marke/[^']+)'", d.read_text(encoding="utf-8"))
    }
    assert "marke/apple-touch-icon-180.png" in pfade
    fehlend = sorted(p for p in pfade if not (PUBLIC / p).is_file())
    assert not fehlend, f"genannt, aber nicht unter public/: {fehlend}"


def test_apple_touch_icon_180_ohne_transparenz():
    # iOS fuellt Transparenz schwarz
    pfad = re.search(r'<link\s+rel="apple-touch-icon"[^>]*\shref="([^"]+)"', INDEX.read_text(encoding="utf-8"))
    bild = Image.open(PUBLIC / pfad.group(1))
    assert bild.size == (180, 180)
    assert bild.mode == "RGB"


def test_manifest_startet_ohne_browserleiste():
    assert json.loads(MANIFEST.read_text(encoding="utf-8"))["display"] == "standalone"
