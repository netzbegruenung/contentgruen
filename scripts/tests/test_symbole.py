"""
Symbole der App: Jede Datei, die index.html (Favicons, apple-touch-icon, og:image) oder das
Manifest nennt, liegt unter public/. Ein vergessener oder vertippter Verweis faellt hier auf
statt erst als fehlendes Symbol auf dem Handy (die "-v2"-Namen stammen aus der Zeit, als nginx
Bilder ein Jahr cachen liess; Cache-Regeln: test_nginx_cache.py).
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
    # Das SVG-Favicon ist seit "-v3" das Logo auf dem App-Gelb, nicht mehr das freistehende Logo
    assert "marke/favicon-v3.svg" in _verweise_index()
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


def test_symbolgrund_ist_das_app_gelb():
    # Startbild (background_color) und Symbolgrund sind das Gelb des Such-Bandes (--kopf, Hellmodus)
    theme = (FRONTEND / "src/theme/custom-theme.scss").read_text(encoding="utf-8")
    kopf = re.search(r"--kopf:\s*(#[0-9a-fA-F]{6});", theme).group(1).lower()
    assert json.loads(MANIFEST.read_text(encoding="utf-8"))["background_color"].lower() == kopf
    bild = Image.open(PUBLIC / "marke/icon-512-v3.png").convert("RGB")
    r, g, b = bild.getpixel((2, 2))
    assert f"#{r:02x}{g:02x}{b:02x}" == kopf


def test_manifest_startet_ohne_browserleiste():
    assert json.loads(MANIFEST.read_text(encoding="utf-8"))["display"] == "standalone"
