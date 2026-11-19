"""
Die Entscheidung der NLI-Stufe fuer einen Text und seine Vektortreffer (#387, #614):
welche Kandidaten das erste Modell prueft, welche dieselbe Behauptung sind und, wenn
keiner, welche der Bestaetiger rettet. Eine Funktion fuer StatementService und den
Bericht ueber den Bestand (tests/regression/dieselbe_bericht.py), damit beide gleich
entscheiden. Die Modelle kommen als Parameter: Der Dienst gibt seine, der Bericht die
des Prozesses (nli_modell), auch wenn der Dienst mit dieselbe_aussage_nli = aus keins hat.
"""

import time
from typing import List, NamedTuple, Optional, Sequence

from core.config import Settings
from domain.models.base_content import BaseContentSearchResult
from services.dieselbe_behauptung import regel
from services.dieselbe_behauptung.nli_modell import NliPruefer

# Der Weg, auf dem ein Kandidat dieselbe wurde.
WEG_NLI = "nli"
WEG_BESTAETIGER = "bestaetiger"


class Dieselbe(NamedTuple):
    """Ein Kandidat, den die NLI-Stufe als dieselbe Behauptung sieht. folgerung ist die
    beidseitige Folgerung des Modells, das entschieden hat (auf dem Weg ueber den
    Bestaetiger also dessen)."""

    kandidat: BaseContentSearchResult
    folgerung: float
    weg: str


def kandidaten_waehlen(
    text: str,
    treffer: Sequence[BaseContentSearchResult],
    settings: Settings,
    mit_bestaetiger: bool,
) -> List[BaseContentSearchResult]:
    """Die Treffer, die das erste Modell pruefen soll: ab nli_kandidaten_ab, die
    Vorpruefungen bestanden (regel.nli_darf_pruefen), hoechstens
    nli_kandidaten_hoechstens; mit Bestaetiger dazu hoechstens ebenso viele, die nur
    regel.bestaetiger_darf_pruefen bestehen."""
    hoechstens = settings.nli_kandidaten_hoechstens
    ab_untergrenze = [
        k
        for k in treffer
        if k.score is not None and k.score >= settings.nli_kandidaten_ab
    ]
    kandidaten = [k for k in ab_untergrenze if regel.nli_darf_pruefen(text, k.text)]
    if not mit_bestaetiger:
        return kandidaten[:hoechstens]
    # Paare, die nur der Bestaetiger pruefen darf ("kein"), kommen dazu, ohne einem
    # Kandidaten der Regel oben den Platz zu nehmen.
    nur_bestaetiger = [
        k
        for k in ab_untergrenze
        if regel.bestaetiger_darf_pruefen(text, k.text)
        and not regel.nli_darf_pruefen(text, k.text)
    ]
    return kandidaten[:hoechstens] + nur_bestaetiger[:hoechstens]


async def dieselben_finden(
    text: str,
    treffer: Sequence[BaseContentSearchResult],
    nli: NliPruefer,
    bestaetiger: Optional[NliPruefer],
    settings: Settings,
    warte_hoechstens: Optional[float] = None,
) -> Optional[List[Dieselbe]]:
    """
    Alle Kandidaten, die das erste Modell als dieselbe Behauptung sieht
    (regel.entscheiden); ist es keiner, mit Bestaetiger alle, die er bestaetigt
    (regel.bestaetigt, nur im unsicheren Band des ersten Modells). Leer, wenn keiner.
    None, wenn das erste Modell nicht urteilen konnte - dann gilt die Schwelle; kann
    der Bestaetiger nicht urteilen, bleibt es beim ersten Modell. warte_hoechstens gilt
    fuer beide Modelle zusammen (None: unbegrenzt).
    """
    beginn = time.monotonic()
    kandidaten = kandidaten_waehlen(text, treffer, settings, bestaetiger is not None)
    if not kandidaten:
        return []
    urteile = await nli.urteile(
        [(text, k.text) for k in kandidaten], warte_hoechstens=warte_hoechstens
    )
    if urteile is None:
        return None
    dieselben = [
        Dieselbe(k, u.folgerung, WEG_NLI)
        for k, u in zip(kandidaten, urteile)
        if regel.entscheiden(
            text,
            k.text,
            k.score,
            u,
            kandidaten_ab=settings.nli_kandidaten_ab,
            folgerung_ab=settings.nli_folgerung_ab,
            widerspruch_unter=settings.nli_widerspruch_unter,
        )
    ]
    if dieselben or bestaetiger is None:
        return dieselben
    band = [
        (k, u)
        for k, u in zip(kandidaten, urteile)
        if regel.braucht_bestaetiger(
            u, settings.nli_widerspruch_unter, settings.nli_bestaetiger_veto_ab
        )
    ]
    if not band:
        return []
    rest = (
        None
        if warte_hoechstens is None
        else max(0.0, warte_hoechstens - (time.monotonic() - beginn))
    )
    bestaetigungen = await bestaetiger.urteile(
        [(text, k.text) for k, _ in band], warte_hoechstens=rest
    )
    if bestaetigungen is None:
        return []
    return [
        Dieselbe(k, b.folgerung, WEG_BESTAETIGER)
        for (k, u), b in zip(band, bestaetigungen)
        if regel.bestaetigt(
            text,
            k.text,
            k.score,
            u,
            b,
            kandidaten_ab=settings.nli_kandidaten_ab,
            folgerung_ab=settings.nli_folgerung_ab,
            widerspruch_unter=settings.nli_widerspruch_unter,
            veto_folgerung_ab=settings.nli_bestaetiger_veto_ab,
        )
    ]


def staerkste(dieselben: Sequence[Dieselbe]) -> Optional[BaseContentSearchResult]:
    """Der Kandidat mit der staerksten beidseitigen Folgerung; None, wenn keiner."""
    return max(dieselben, key=lambda d: d.folgerung).kandidat if dieselben else None
