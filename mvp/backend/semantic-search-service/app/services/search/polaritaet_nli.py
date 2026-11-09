"""
Polaritaetsstrafe der Suche mit dem Urteil der NLI-Stufe (#574).

Bis #574 strafte die Suche Aussagen, deren Polaritaet der Suchanfrage widerspricht,
nur nach Regeln und Wortlisten (utils/negation_detector.py ueber
PolarityFilterService). Gegenteile ohne Verneinungswort ("Windraeder schuetzen Voegel"
gegen "Windraeder toeten Voegel") blieben so ungestraft. Hier urteilt stattdessen das
NLI-Modell der NLI-Stufe (NLI_MODELL, dasselbe Objekt wie in StatementService, kein
zweites im Speicher): Widerspricht eine Aussage der Suchanfrage in beiden Richtungen mit
mindestens suche_polaritaet_widerspruch_ab, sinkt ihr Score, und ihre Antworten kommen
auch nicht ueber den direkten Weg zurueck (SearchOrchestrator.collect_direct).

Beide Richtungen, nicht eine: Echte Gegenteile widersprechen sich am Suchtestset in beiden
Richtungen mit 0,98 und mehr. Umgangssprachliche Umformulierungen ("Windkraftanlagen
bringen massenhaft Voegel um" zu "Windraeder toeten die Voegel!") liest das Modell oft in
einer Richtung als Widerspruch (0,99), in der anderen kaum (0,53). Gemessen in
tests/regression/SUCHTESTSET.md, Abschnitt Polaritaet mit NLI.

suche_polaritaet_nli (core/config.py):

- aus: die Regel von heute (Wortlisten).
- schatten: Die Regel entscheidet, das Modell urteilt im Hintergrund mit, gezaehlt wird
  nur, wie oft beide uebereinstimmen (wie der Schattenbetrieb der NLI-Stufe: nur
  Zaehler, keine Suchtexte, keine IDs, kein Ereignis je Suche, #239).
- an: Das Modell entscheidet. Ist es nicht verfuegbar, laedt es noch oder urteilt es
  laenger als SUCHE_WARTET_HOECHSTENS fuer eine andere Anfrage, gilt die Regel.

Mit enable_polarity_filtering = false straft keine der beiden.
"""

import asyncio
import logging
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple, TypeVar

from services.dieselbe_behauptung.regel import ist_frage
from services.dieselbe_behauptung.nli_modell import NliModell, NliPruefer
from services.polarity_filter_service import (
    HasScore,
    PolarityFilterResult,
    PolarityFilterService,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=HasScore)

# So lange wartet eine Suche hoechstens auf das Modell (Sekunden), danach gilt die Regel.
SUCHE_WARTET_HOECHSTENS = 2.0
# Strafe bei Widerspruch: wie die Regel (calculate_polarity_penalty), mit der
# Widerspruchswahrscheinlichkeit als Sicherheit; 0,5 ergibt 0,65, 0,99 ergibt 0,31.
STRAFE_JE_WIDERSPRUCH = 0.7
STRAFE_HOECHSTENS = 0.2
ZUSAMMENFASSUNG_ALLE = 100
# Kuerzere Suchanfragen sind Schlagwoerter, keine Behauptung (urteilbar).
MINDESTENS_WOERTER = 3

# Was der Schattenbetrieb zaehlt (je Aussagetreffer, nicht je Suche):
# - beide_strafe / beide_keine: Regel und Modell stimmen ueberein.
# - nur_regel: Die Regel straft, das Modell sieht keinen Widerspruch.
# - nur_nli: Das Modell sieht einen Widerspruch, die Regel straft nicht.
# - ohne_modell: Das Modell konnte nicht urteilen (je Suche gezaehlt).
# - uebersprungen: Ein anderes Urteil lief noch (je Suche gezaehlt).
ARTEN = (
    "beide_strafe",
    "beide_keine",
    "nur_regel",
    "nur_nli",
    "ohne_modell",
    "uebersprungen",
)


def _schluessel(treffer) -> str:
    """Der Schluessel der Metadaten je Treffer, wie in PolarityFilterService."""
    return getattr(treffer, "id", str(id(treffer)))


def urteilbar(query_text: str) -> bool:
    """Urteilt das Modell ueber diese Suchanfrage? Nur ueber eine Behauptung: Eine Frage
    behauptet nichts (ist_frage), und Schlagwoerter ("Dunkelflaute Blackout")
    liest das Modell als Widerspruch zu passenden Aussagen. Fuer beide gilt die Regel.
    """
    return not ist_frage(query_text) and len(query_text.split()) >= MINDESTENS_WOERTER


def strafe(widerspruch: float) -> float:
    """Der Faktor fuer den Score bei einem Widerspruch mit dieser Wahrscheinlichkeit."""
    return max(STRAFE_HOECHSTENS, min(1.0, 1.0 - widerspruch * STRAFE_JE_WIDERSPRUCH))


class NliPolaritaet:
    def __init__(
        self,
        nli: Optional[NliPruefer],
        modus: str,
        widerspruch_ab: float,
    ):
        self._nli = nli if modus != "aus" else None
        self._modus = modus
        self._widerspruch_ab = widerspruch_ab
        self.zaehler: Counter[str] = Counter()
        self._schatten_laeuft = False
        self._schatten_tasks: set[asyncio.Task] = set()

    async def laden_abwarten(self) -> bool:
        """Warten, bis das Modell geladen ist (Messskripte); True, wenn es bereitsteht."""
        if isinstance(self._nli, NliModell):
            return await asyncio.to_thread(self._nli.laden_abwarten)
        return self._nli is not None

    async def gewichten(
        self,
        regel: PolarityFilterService,
        query_text: str,
        treffer: List[T],
        get_text_fn: Callable[[T], str],
    ) -> Tuple[List[T], Dict[str, PolarityFilterResult]]:
        """
        Die Aussagetreffer mit Polaritaetsstrafe, neu sortiert, und die Metadaten je
        Treffer-ID - dieselbe Rueckgabe wie
        PolarityFilterService.analyze_and_filter_statement_results.
        """
        if (
            not regel.enable_filtering
            or not treffer
            or self._nli is None
            or not urteilbar(query_text)
        ):
            return regel.analyze_and_filter_statement_results(
                query_text, treffer, get_text_fn
            )
        if self._modus == "schatten":
            texte = [get_text_fn(t) for t in treffer]
            schluessel = [_schluessel(t) for t in treffer]
            ergebnis = regel.analyze_and_filter_statement_results(
                query_text, treffer, get_text_fn
            )
            regel_straft = [
                k in ergebnis[1] and ergebnis[1][k].polarity_mismatch_detected
                for k in schluessel
            ]
            self._schatten_starten(query_text, texte, regel_straft)
            return ergebnis

        urteile = await self._urteile(query_text, [get_text_fn(t) for t in treffer])
        if urteile is None:
            return regel.analyze_and_filter_statement_results(
                query_text, treffer, get_text_fn
            )
        metadaten: Dict[str, PolarityFilterResult] = {}
        for t, widerspruch in zip(treffer, urteile):
            vorher = t.score
            faktor = strafe(widerspruch) if widerspruch >= self._widerspruch_ab else 1.0
            t.score = vorher * faktor
            metadaten[_schluessel(t)] = PolarityFilterResult(
                original_score=vorher,
                adjusted_score=t.score,
                polarity_penalty_applied=faktor,
                polarity_mismatch_detected=faktor < 1.0,
                query_polarity="nli",
                result_polarity="widerspruch" if faktor < 1.0 else "vertraeglich",
                explanation=f"NLI-Widerspruch {widerspruch:.2f}",
                antworten_ausschliessen=faktor < 1.0,
            )
        treffer = sorted(treffer, key=lambda t: t.score, reverse=True)
        return treffer, metadaten

    async def _urteile(
        self, query_text: str, texte: List[str]
    ) -> Optional[List[float]]:
        """Je Text die schwaechere Widerspruchswahrscheinlichkeit beider Richtungen;
        None, wenn das Modell nicht urteilen kann oder scheitert."""
        try:
            urteile = await self._nli.urteile(
                [(query_text, text) for text in texte],
                warte_hoechstens=SUCHE_WARTET_HOECHSTENS,
            )
        except Exception as e:
            logger.warning("NLI-Polaritaet gescheitert (%s)", type(e).__name__)
            return None
        if urteile is None:
            return None
        return [min(u.hin.widerspruch, u.rueck.widerspruch) for u in urteile]

    def zaehlen(self, art: str, anzahl: int = 1) -> None:
        vorher = sum(self.zaehler.values())
        self.zaehler[art] += anzahl
        if vorher // ZUSAMMENFASSUNG_ALLE != (vorher + anzahl) // ZUSAMMENFASSUNG_ALLE:
            logger.info(
                "NLI-Polaritaet im Schattenbetrieb seit Start: %s",
                ", ".join(f"{a}={self.zaehler[a]}" for a in ARTEN),
            )

    def _schatten_starten(
        self,
        query_text: str,
        texte: List[str],
        regel_straft: List[bool],
    ) -> None:
        """Das Modell im Hintergrund urteilen lassen, ohne dass die Suche wartet. Laeuft
        schon ein Urteil, wird dieses uebersprungen (gezaehlt)."""
        if self._schatten_laeuft:
            self.zaehlen("uebersprungen")
            return
        self._schatten_laeuft = True

        async def urteilen():
            try:
                urteile = await self._urteile(query_text, texte)
                if urteile is None:
                    self.zaehlen("ohne_modell")
                    return
                for straft, widerspruch in zip(regel_straft, urteile):
                    nli = widerspruch >= self._widerspruch_ab
                    if straft and nli:
                        self.zaehlen("beide_strafe")
                    elif straft:
                        self.zaehlen("nur_regel")
                    elif nli:
                        self.zaehlen("nur_nli")
                    else:
                        self.zaehlen("beide_keine")
            except Exception as e:  # der Schatten darf die Suche nie stoeren
                logger.warning(
                    "NLI-Polaritaet im Schatten gescheitert (%s)", type(e).__name__
                )
            finally:
                self._schatten_laeuft = False

        task = asyncio.create_task(urteilen())
        # Referenz halten: asyncio haelt Tasks nur schwach.
        self._schatten_tasks.add(task)
        task.add_done_callback(self._schatten_tasks.discard)


_NLI_POLARITAET: Optional[NliPolaritaet] = None


def get_nli_polaritaet() -> NliPolaritaet:
    """Die eine NliPolaritaet dieses Prozesses, nach den Einstellungen beim ersten Aufruf."""
    global _NLI_POLARITAET
    if _NLI_POLARITAET is None:
        from core.config import NLI_MODELL, settings
        from services.dieselbe_behauptung.nli_modell import nli_modell

        modus = settings.suche_polaritaet_nli
        _NLI_POLARITAET = NliPolaritaet(
            nli_modell(NLI_MODELL) if modus != "aus" else None,
            modus,
            settings.suche_polaritaet_widerspruch_ab,
        )
    return _NLI_POLARITAET
