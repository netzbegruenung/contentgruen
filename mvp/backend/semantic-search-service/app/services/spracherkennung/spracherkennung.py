"""
Spracherkennung beim Schreiben (#405): Gut gesagt nimmt an, dass jeder Text deutsch ist
(Stoppliste, Stemmer, Gegenlesen). Ist ein Beitrag oder eine Aussage offenbar in einer
anderen Sprache, zeigt das Formular einen Sprachhinweis. Er sperrt nichts: Auf kurzen
Texten ist die Erkennung unsicher, deshalb fragt sie erst ab MIN_WOERTER Wörtern.

Erkannt wird mit Lingua (Apache-2.0), lokal und deterministisch, beschränkt auf wenige
Sprachen, damit es wenig Speicher braucht (ADR 0005). Nichts davon wird gespeichert oder
geloggt: Den Sprachhinweis sieht nur die schreibende Person. Suchanfragen erkennt sie
nicht.
"""

import re
import threading
from typing import Callable, Dict, Optional

#: Die Sprachen, unter denen Lingua wählt (ISO 639-1): Deutsch, die Nachbarsprachen und
#: die großen Sprachen der Einwanderung. Mit nur vier Sprachen (de, en, fr, tr) hielt
#: Lingua Spanisch und Niederländisch für Deutsch; mit allen 75 braucht es rund 200 MB
#: statt rund 45 MB und ist sich bei deutschen Sätzen unsicherer (Messung im PR zu #405).
#: Eine Sprache außerhalb der Liste erkennt Lingua als die nächstliegende darunter; für
#: den Sprachhinweis reicht das, weil er nur sagt, dass ein Text nicht deutsch ist.
SPRACHEN = ("de", "en", "fr", "tr", "es", "it", "pl", "ru", "uk", "ar", "nl")

#: Ab so vielen Wörtern fragt die Erkennung: Auf Sätzen erkennt Lingua Deutsch zu
#: 99,7 %, auf einzelnen Wörtern nur zu 74,2 %.
MIN_WOERTER = 5

#: Unter dieser Sicherheit für Deutsch gilt ein Text als nicht deutsch, sofern eine
#: andere Sprache vorn liegt. Mit Abstand: Ein deutscher Text mit Anglizismen oder
#: englischem Zitat liegt manchmal knapp hinter Englisch, aber nie so weit.
DEUTSCH_UNTER = 0.2

#: Ein Wort sind Buchstaben am Stück; Zahlen, Zeichen und Emoji zählen nicht.
_WORT = re.compile(r"[^\W\d_]+")

#: Sicherheit je Sprache (ISO 639-1) für einen Text, zusammen 1.
Erkenner = Callable[[str], Dict[str, float]]


def _lingua_bauen() -> Erkenner:
    from lingua import IsoCode639_1, Language, LanguageDetectorBuilder

    sprachen = [
        Language.from_iso_code_639_1(getattr(IsoCode639_1, code.upper()))
        for code in SPRACHEN
    ]
    # Ohne Vorladen lädt Lingua die Modelle erst, wenn ein Text sie braucht (je Schrift
    # beim ersten Text, rund 80 ms); so wartet kein Sprachhinweis darauf.
    detector = (
        LanguageDetectorBuilder.from_languages(*sprachen)
        .with_preloaded_language_models()
        .build()
    )

    def erkennen(text: str) -> Dict[str, float]:
        return {
            wert.language.iso_code_639_1.name.lower(): wert.value
            for wert in detector.compute_language_confidence_values(text)
        }

    return erkennen


class Spracherkennung:
    """Lingua, beim ersten Gebrauch geladen; der Start lädt es vor (main.py)."""

    def __init__(self, bauen: Callable[[], Erkenner] = _lingua_bauen):
        self._bauen = bauen
        self._lock = threading.Lock()
        self._erkenner: Optional[Erkenner] = None

    def laden(self) -> None:
        with self._lock:
            if self._erkenner is None:
                self._erkenner = self._bauen()

    def fremdsprache(self, text: str) -> Optional[str]:
        """Die Sprache (ISO 639-1), wenn der Text offenbar nicht deutsch ist, sonst None."""
        text = (text or "").strip()
        if len(_WORT.findall(text)) < MIN_WOERTER:
            return None
        self.laden()
        werte = self._erkenner(text)
        if not werte:
            return None
        vorn = max(werte, key=werte.get)
        if vorn == "de" or werte.get("de", 0.0) >= DEUTSCH_UNTER:
            return None
        return vorn


#: Eine Instanz je Prozess: Der Endpunkt nutzt sie, der Start lädt sie vor (main.py).
SPRACHERKENNUNG = Spracherkennung()
