"""
Bezug einer Aussage zur Suchanfrage: Hat sie inhaltlich mit ihr zu tun?

Die Einbettung (EMBEDDING_MODELL) gibt auch Saetzen ohne gemeinsames Thema eine hohe
Aehnlichkeit, wenn sie gleich gebaut sind oder ein Schlagwort teilen: "Open Source ist
unsicher!" liegt bei 0,862 zu "Migranten machen unsere Staedte unsicher.". Mit einem
Kommentar (Relevanz 1,0) braucht eine Aussage fuer MINIMUM_SCORE_THRESHOLD (0,82) aber
nur 0,743 (0,7 * Aehnlichkeit + 0,3 * Relevanz), und die Ergebnisseite zeigte "Erkannt
als" mit der fremden Aussage. Gemessen in tests/regression/SUCHTESTSET.md, Abschnitt
"Bezug".

Fuer eine Suchanfrage ab MINDESTENS_WOERTER Woertern (Behauptung oder Frage) gilt
deshalb, an der Aehnlichkeit der Einbettung vor Polaritaet und Schlagwoertern:

- unter suche_bezug_ab: kein Bezug.
- ab suche_bezug_sicher_ab: Bezug, ohne Modell.
- dazwischen bei einer Frage: Bezug. Bei einer Behauptung (urteilbar wie bei der
  Polaritaet, #574) nur, wenn das NLI-Modell (NLI_MODELL, dasselbe Objekt wie die
  NLI-Stufe) in einer Richtung mindestens suche_bezug_folgerung_ab Folgerung sieht.
  Gleich gebaute Saetze ueber anderes ("Golf ist nur was fuer Reiche" zu "Bio ist nur
  was fuer Reiche.") folgern in keiner Richtung, Umformulierungen meist in einer. Mit
  suche_bezug_nli = false, ohne geladenes Modell oder wenn es laenger als
  SUCHE_WARTET_HOECHSTENS belegt ist: Bezug.

Eine Aussage ohne Bezug faellt aus den Aussagetreffern. Ihre Antworten kann der
direkte Weg trotzdem bringen, wenn sie selbst der Suchanfrage aehnlich genug sind; sie
stehen dann ohne "Erkannt als" da. Am Startbestand holt das sechs Faelle Umgangssprache
zurueck ("Woelfe haben in Deutschland nichts verloren"); ein fremder Fall ("Ein neues
Handy lohnt sich nicht") zeigt dafuer eine Antwort zu Balkonsolar, ohne "Erkannt als".

Schlagwoerter (unter MINDESTENS_WOERTER Woertern) prueft das nicht: Sie liegen oft
niedriger, etwa "Genderzwang" oder "Migration Kriminalitaet", und fuer sie gilt die
Schwelle der Suche allein. Die Fragen des Suchtestsets liegen bei 0,896 bis 0,901.
"""

import logging
from typing import Callable, List, Optional, Set, TypeVar

from services.dieselbe_behauptung.nli_modell import NliPruefer
from services.search.polaritaet_nli import (
    MINDESTENS_WOERTER,
    SUCHE_WARTET_HOECHSTENS,
    urteilbar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AussageBezug:
    def __init__(
        self,
        nli: Optional[NliPruefer],
        ab: float,
        sicher_ab: float,
        folgerung_ab: float,
    ):
        self._nli = nli
        self._ab = ab
        self._sicher_ab = sicher_ab
        self._folgerung_ab = folgerung_ab

    async def ohne_bezug(
        self,
        query_text: str,
        treffer: List[T],
        get_text_fn: Callable[[T], str],
        get_score_fn: Callable[[T], float],
    ) -> Set[int]:
        """Die Positionen in ``treffer`` ohne Bezug zur Suchanfrage (Regeln oben)."""
        if not treffer or len(query_text.split()) < MINDESTENS_WOERTER:
            return set()
        ohne = {i for i, t in enumerate(treffer) if get_score_fn(t) < self._ab}
        band = [
            i
            for i, t in enumerate(treffer)
            if self._ab <= get_score_fn(t) < self._sicher_ab
        ]
        if not band or self._nli is None or not urteilbar(query_text):
            return ohne
        try:
            urteile = await self._nli.urteile(
                [(query_text, get_text_fn(treffer[i])) for i in band],
                warte_hoechstens=SUCHE_WARTET_HOECHSTENS,
            )
        except Exception as e:
            logger.warning("Bezug der Aussagen nicht geprueft (%s)", type(e).__name__)
            return ohne
        if urteile is None:
            return ohne
        return ohne | {
            i
            for i, urteil in zip(band, urteile)
            if max(urteil.hin.folgerung, urteil.rueck.folgerung) < self._folgerung_ab
        }


_AUSSAGE_BEZUG: Optional[AussageBezug] = None


def get_aussage_bezug() -> AussageBezug:
    """Die eine AussageBezug dieses Prozesses, nach den Einstellungen beim ersten Aufruf."""
    global _AUSSAGE_BEZUG
    if _AUSSAGE_BEZUG is None:
        from core.config import NLI_MODELL, settings
        from services.dieselbe_behauptung.nli_modell import nli_modell

        _AUSSAGE_BEZUG = AussageBezug(
            nli_modell(NLI_MODELL) if settings.suche_bezug_nli else None,
            settings.suche_bezug_ab,
            settings.suche_bezug_sicher_ab,
            settings.suche_bezug_folgerung_ab,
        )
    return _AUSSAGE_BEZUG
