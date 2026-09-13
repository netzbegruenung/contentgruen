"""
Das Titel-Limit von Kommentar und Hintergrundinfo festnageln.

Der Titel ist eine Behauptung in einem Satz, hoechstens 120 Zeichen. Die Zahl ist
nicht beliebig: Die Titelbox der Suchkarte ist auf genau diese Laenge ausgemessen
(4 Zeilen Desktop, 5 Zeilen mobil). Wer das Limit hier aendert, muss die Karte neu
messen -- deshalb steht es in einem Test und nicht nur im Modell.

Bild und Post haben eigene Titelregeln und bleiben unberuehrt.
"""

import pytest
from pydantic import ValidationError

from domain.models.commentary import Commentary
from domain.models.generic_text import GenericText
from domain.models.image import Image

TITEL_LIMIT = 120


def _kommentar(title: str) -> Commentary:
    return Commentary(text="Ein Kommentartext mit Inhalt.", title=title, references=[])


def _hintergrundinfo(title: str) -> GenericText:
    return GenericText(text="Eine Hintergrundinfo mit Inhalt.", title=title)


@pytest.mark.unit
@pytest.mark.parametrize("bauen", [_kommentar, _hintergrundinfo])
class TestTitelLimit:
    def test_title_limit_120_zeichen_werden_angenommen(self, bauen):
        assert len(bauen("a" * TITEL_LIMIT).title) == TITEL_LIMIT

    def test_title_limit_121_zeichen_werden_abgewiesen(self, bauen):
        with pytest.raises(ValidationError):
            bauen("a" * (TITEL_LIMIT + 1))

    def test_title_limit_beispielsatz_passt(self, bauen):
        satz = "Wärmepumpen rechnen sich im Altbau, wenn man die Förderung mitrechnet"
        assert bauen(satz).title == satz


@pytest.mark.unit
def test_title_limit_bild_bleibt_bei_200():
    """Die Titelregel gilt nicht fuer Bilder."""
    feld = Image.model_fields["title"]
    max_laengen = [m.max_length for m in feld.metadata if hasattr(m, "max_length")]
    assert max_laengen == [200]
