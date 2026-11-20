"""
Inhaltstor mit dem echten Sprachmodell (de_core_news_sm, wie das Gegenlesen): der
Wortlaut von Produktion. Ohne spaCy uebersprungen, in CI Pflicht (wie
test_gegenlesen_service.py).
"""

import importlib.util
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.gegenlesen.gegenlesen_service import SPACY_MODELL, Sprachwerkzeuge
from services.search.inhaltstor import Inhaltstor

pytestmark = [pytest.mark.unit]

if any(
    importlib.util.find_spec(p) is None for p in ("spacy", "charsplit", SPACY_MODELL)
):
    _GRUND = "spaCy nicht installiert: pip install -r requirements.txt"
    if os.environ.get("CI"):
        pytest.fail(_GRUND, pytrace=False)
    pytest.skip(_GRUND, allow_module_level=True)

ARBEITSERLAUBNIS = (
    "Das Problem hier ist die oft fehlende Arbeitserlaubnis, dies aus verschiedensten "
    "Gründen viel zu lange auf sich warten lässt. Die Menschen hingegen wollen "
    "größtenteils unbedingt arbeiten, dürfen jedoch nicht!"
)


@pytest.fixture(scope="module")
def werkzeuge():
    w = Sprachwerkzeuge()
    w.laden()
    return w


def _tor(werkzeuge, *aussagen):
    return Inhaltstor(
        werkzeuge,
        AsyncMock(return_value=[SimpleNamespace(text=t) for t in aussagen]),
        0.82,
        0.92,
        0.90,
    )


@pytest.mark.asyncio
async def test_arbeitserlaubnis_zu_open_source_zaehlt_nicht(werkzeuge):
    beitrag = SimpleNamespace(
        id="b", score=0.821, title="Arbeitserlaubnis ist Schuld", text=ARBEITSERLAUBNIS
    )
    tor = _tor(werkzeuge, "Flüchtlinge wollen gar nicht arbeiten.")
    assert not await tor.direkt_zaehlt("Open Source ist unsicher!", beitrag)


@pytest.mark.asyncio
async def test_umformulierung_mit_gemeinsamem_nomen_zaehlt(werkzeuge):
    beitrag = SimpleNamespace(
        id="b",
        score=0.879,
        title="Kriminalität hat viele Ursachen",
        text="Armut und fehlende Perspektiven erklären mehr als die Herkunft.",
    )
    tor = _tor(werkzeuge)
    assert await tor.direkt_zaehlt(
        "Durch die Zuwanderung gibt es mehr Kriminalität", beitrag
    )


def test_gleich_gebauter_satz_zaehlt_nicht(werkzeuge):
    tor = _tor(werkzeuge)
    assert not tor.aussage_zaehlt(
        "Katzen wollen gar nicht arbeiten",
        0.912,
        "Flüchtlinge wollen gar nicht arbeiten.",
        SimpleNamespace(title="Arbeit lohnt sich", text="Viele wollen arbeiten."),
    )
