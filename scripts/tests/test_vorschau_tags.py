"""
Linkvorschau in Messengern (Persona-Runde 2, P01): index.html traegt allgemeine og-Tags, sonst
zeigt WhatsApp einen nackten Link. og:title gleicht dem <title>; die Beschreibung ist der
freigegebene Text (E4, 14.11.2026); das Bild steht mit absoluter Adresse.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = WURZEL / "mvp/frontend/gutgesagt-frontend"
INDEX = FRONTEND / "src/index.html"

META = re.compile(r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"\s*/?>')


def _meta() -> dict[str, str]:
    return dict(META.findall(INDEX.read_text(encoding="utf-8")))


def test_og_grundtags_vorhanden():
    meta = _meta()
    for name in ("og:type", "og:site_name", "og:title", "og:description", "og:image"):
        assert meta.get(name), f"{name} fehlt in index.html"
    assert meta["twitter:card"] == "summary"


def test_og_title_gleicht_seitentitel():
    titel = re.search(r"<title>([^<]+)</title>", INDEX.read_text(encoding="utf-8")).group(1)
    assert _meta()["og:title"] == titel


def test_beschreibung_freigegeben_und_gleich():
    meta = _meta()
    assert meta["og:description"] == "Gute Antworten gegen Stimmungsmache im Netz. Finden, kopieren, posten."
    assert meta["twitter:description"] == meta["og:description"]
    assert "TODO" not in INDEX.read_text(encoding="utf-8")


def test_og_bild_absolut_und_im_public_ordner():
    bild = _meta()["og:image"]
    praefix = "https://gutgesagt.netzbegruenung.de/"
    assert bild.startswith(praefix), "WhatsApp zeigt nur Bilder mit absoluter Adresse"
    assert (FRONTEND / "public" / bild[len(praefix) :]).is_file()


# Vorschau je Beitrag und fuer die Ergebnisseite (#360): nginx ersetzt per SSI den Block
# "linkvorschau_allgemein" durch das Stueck aus api/v1/linkvorschau.py. Wie das in nginx
# wirkt, prueft tests/integration/test_linkvorschau_nginx.py im Suchdienst.
LINKVORSCHAU = WURZEL / "mvp/backend/semantic-search-service/app/services/linkvorschau.py"


def test_allgemeine_angaben_im_ssi_block():
    text = INDEX.read_text(encoding="utf-8")
    block = re.search(
        r'<!--# block name="linkvorschau_allgemein" -->(.*?)<!--# endblock -->\s*'
        r'<!--# include virtual="\$linkvorschau" stub="linkvorschau_allgemein" -->',
        text,
        re.S,
    )
    assert block, "SSI-Block fuer die Linkvorschau fehlt oder ist umgestellt"
    im_block = dict(META.findall(block.group(1)))
    # Genau das, was das Stueck des Suchdienstes ersetzt; Bild und Seitenname bleiben aussen.
    assert set(im_block) == {"og:title", "og:description", "twitter:description"}
    assert text.count("<!--#") == 3


def test_allgemeine_beschreibung_im_suchdienst_gleich():
    quelle = LINKVORSCHAU.read_text(encoding="utf-8")
    beschreibung = re.search(r'ALLGEMEINE_BESCHREIBUNG = \(?\s*"([^"]+)"', quelle).group(1)
    assert beschreibung == _meta()["og:description"]


def test_beide_nginx_konfigurationen_werten_ssi_aus():
    for konfiguration in ("nginx.conf", "nginx.docker.conf"):
        text = (FRONTEND / konfiguration).read_text(encoding="utf-8")
        assert text.count("ssi on;") == 2, konfiguration
        assert "location /_linkvorschau/ {\n        internal;" in text, konfiguration
        assert "set $linkvorschau_dienst gutgesagt-semantic-search:8000;" in text, konfiguration
