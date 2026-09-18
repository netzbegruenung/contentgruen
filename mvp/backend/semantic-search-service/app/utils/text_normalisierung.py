"""
Wann zwei Texte "derselbe Text" sind - fuer die Dublettenpruefung von Aussagen
und Kommentaren.

Der Vektorvergleich allein trennt das nicht: Eine Aussage in Grossbuchstaben
erreicht gegen ihr Original nur 0,902, eine Verneinung ("... sind keine
Verbotspartei") 0,969 (Messung in tests/regression/aehnlichkeit_paare.py).
Deshalb gilt normalisiert gleicher Text immer als dasselbe, unabhaengig vom Score.

Die Normalisierung ist ein Datenformat: Sie steht als Payload-Feld
text_normalisiert in Qdrant (Keyword-Index). Wer sie aendert, muss den Bestand
neu nachtragen (services/wartung/text_normalisiert_nachtrag.py).
"""

import asyncio
import re
import unicodedata
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

# Payload-Feld und die Inhaltstypen, fuer die es gepflegt wird.
FELD_TEXT_NORMALISIERT = "text_normalisiert"
TYPEN_MIT_TEXT_NORMALISIERT = frozenset({"statement", "commentary"})

_APOSTROPHE = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_ANFUEHRUNGSZEICHEN = re.compile(r"[\"„“”‚«»‹›]")
# Punkt, Ausrufezeichen und Auslassungspunkte am Ende aendern nichts an der Aussage.
# Das Fragezeichen bleibt: "Die Gruenen wollen alles verbieten?" fragt, "... verbieten."
# behauptet - das sind nicht dieselben Saetze.
_SATZZEICHEN_AM_ENDE = ".!…"


def text_normalisiert(text: str) -> str:
    """
    Gross/klein, Leerraum, Anfuehrungszeichen sowie Punkt, Ausrufezeichen und
    Auslassungspunkte am Ende spielen keine Rolle; typografische Apostrophe gelten
    wie der gerade. Ein Fragezeichen am Ende bleibt stehen.
    """
    t = unicodedata.normalize("NFC", text or "").translate(_APOSTROPHE)
    t = _ANFUEHRUNGSZEICHEN.sub("", t)
    t = " ".join(t.split()).casefold()
    return t.rstrip(_SATZZEICHEN_AM_ENDE + " ")


def ist_dasselbe(
    kandidat_normalisiert: str,
    bestand_normalisiert: str,
    score: float | None,
    schwelle: float,
) -> bool:
    """
    Normalisiert gleich, oder der Vektorvergleich liegt mindestens auf der Schwelle.
    Eine leere Normalform (nur Satzzeichen) gilt nicht als gleich - sonst fielen
    alle solchen Texte zusammen.
    """
    if kandidat_normalisiert and kandidat_normalisiert == bestand_normalisiert:
        return True
    return score is not None and score >= schwelle


class SperreJeText:
    """
    Serialisiert Schreibvorgaenge mit normalisiert gleichem Text.

    Pruefen und Schreiben sind zwei Schritte: Zwei gleichzeitige Anfragen mit
    demselben neuen Text bestehen sonst beide die Pruefung und legen zwei Punkte
    an. Prozesslokal - genuegt, weil der Dienst mit einem uvicorn-Worker laeuft.
    Sperren werden freigegeben, sobald niemand sie mehr haelt oder auf sie wartet.
    """

    def __init__(self):
        self._sperren: Dict[str, asyncio.Lock] = {}
        self._belegt: Dict[str, int] = {}

    @asynccontextmanager
    async def halten(self, text: str) -> AsyncIterator[str]:
        """Haelt die Sperre fuer diesen Text und liefert seine Normalform."""
        schluessel = text_normalisiert(text)
        sperre = self._sperren.setdefault(schluessel, asyncio.Lock())
        self._belegt[schluessel] = self._belegt.get(schluessel, 0) + 1
        try:
            async with sperre:
                yield schluessel
        finally:
            self._belegt[schluessel] -= 1
            if self._belegt[schluessel] == 0:
                del self._belegt[schluessel]
                del self._sperren[schluessel]
