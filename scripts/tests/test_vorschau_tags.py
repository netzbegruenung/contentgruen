"""
Linkvorschau in Messengern (Persona-Runde 2, P01): index.html traegt allgemeine og-Tags, sonst
zeigt WhatsApp einen nackten Link. og:title gleicht dem <title>; og:description steht als
Platzhalter TODO-E4, bis die Textentscheidung E4 gefallen ist.
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


def test_og_bild_liegt_im_public_ordner():
    bild = _meta()["og:image"].lstrip("/")
    assert (FRONTEND / "public" / bild).is_file()
