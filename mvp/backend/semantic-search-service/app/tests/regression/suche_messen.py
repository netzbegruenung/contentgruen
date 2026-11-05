"""
Misst das Suchtestset (suche_testset.py) gegen den Bestand eines Stacks: je Schwelle
Treffer, Fehltreffer und keine Treffer, dazu Praezision, Recall@k und die Zerfaserung.
Regeln und Ergebnis in SUCHTESTSET.md.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.suche_messen            # Tabellen
    ../venv/bin/python -m tests.regression.suche_messen --faelle   # dazu jeder Fall
    ../venv/bin/python -m tests.regression.suche_messen --json messung.json

Verbindet sich wie der Dienst (SEMANTIC_SEARCH_QDRANT_URL, ..._QDRANT_COLLECTION) und
laedt das Einbettungsmodell (~1,5 GB RAM). Im Container des Semantic-Search-Service:
`python -m tests.regression.suche_messen`.

Liest nur: Es ruft dieselben Schritte wie die Suche (api/v1/search.py: Aussagetreffer,
Polaritaetsfilter, Schlagwort-Ueberlappung, Orchestrator), aber nicht den Endpunkt. Es
legt keine Aussage aus der Suchanfrage an und zaehlt weder Suchereignis noch Suche ohne
Treffer. Gesammelt wird ohne Schwelle; welche Treffer eine Schwelle zeigen wuerde,
rechnet die Auswertung danach aus. So kostet ein Vergleich vieler Schwellen eine Messung.

Schnittstelle fuer Folgetickets (naechtlicher Lauf, Stemmer, Modellwechsel): messen()
liefert je Fall eine FallMessung, auswerten() und zerfaserung() rechnen daraus ohne
Stack; --json schreibt beides als Datei.
"""

import argparse
import asyncio
import json
import sys
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from tests.regression.suche_testset import FAELLE, Fall
from utils.text_normalisierung import text_normalisiert

# Die Schwelle der Suche steht in services/search/search_orchestrator.py
# (MINIMUM_SCORE_THRESHOLD, siehe schwelle_heute()). Das Modul wird erst bei Bedarf
# geladen: Es braucht ein initialisiertes Logging (main()).

# So viele Treffer fragt das Frontend je Suche an (result-view.component.ts).
K = 10
STANDARD_SCHWELLEN = (0.76, 0.78, 0.79, 0.80, 0.81, 0.82, 0.84, 0.86)
# Gesammelt wird unterhalb jeder sinnvollen Schwelle und mit grosszuegigem Limit, damit
# die Auswertung jede Schwelle nachrechnen kann.
SAMMELSCHWELLE = 0.0
SAMMELLIMIT = 100

VORLAEUFIG = (
    "Vorläufig: gemessen am Testbestand (Seed). Nach dem Startbestand (#288) einmal neu "
    "messen, siehe SUCHTESTSET.md."
)

EINORDNUNGEN = ("treffer", "fehltreffer", "keine")


class Kandidat(NamedTuple):
    """Ein Beitrag, den die Suche zu einer Suchanfrage findet, vor jeder Schwelle."""

    beitrag_id: str
    typ: str
    aussage_text: str  # leer bei einem direkten Treffer
    schwellenwert: float  # damit vergleicht die Suche die Schwelle
    rangwert: float  # danach sortiert sie
    passt: bool


class FallMessung(NamedTuple):
    fall: Fall
    kandidaten: Tuple[Kandidat, ...]
    # Aussagen aus fall.erwartet, die im gemessenen Bestand fehlen. Ist eine davon
    # nicht da, zaehlt der Fall nicht mit.
    fehlt: Tuple[str, ...]
    # Nur bei dieselbe_behauptung: Landet die Suchanfrage auf einer erwarteten Aussage
    # (True) oder ergaebe sie eine neue bzw. landet auf einer anderen (False)?
    landet_auf_erwarteter: Optional[bool]


class Auswertung(NamedTuple):
    schwelle: float
    faelle: int
    mit_erwartung: int
    treffer: int
    fehltreffer: int
    keine: int
    ohne_erwartung: int
    ohne_richtig_keine: int
    ohne_fehltreffer: int
    praezision: Optional[float]  # passende / alle angezeigten Beitraege
    recall_at_k: Optional[float]  # Faelle mit Erwartung und passendem Beitrag unter k


class Zerfaserung(NamedTuple):
    schwelle: float
    dieselbe_behauptung: int  # gemessene Faelle mit dieselbe_behauptung
    davon_neu: int  # landen nicht auf der erwarteten Aussage
    ohne_treffer: int  # alle gemessenen Faelle ohne angezeigten Beitrag
    ohne_treffer_dieselbe: int  # davon dieselbe_behauptung
    ohne_treffer_neu: int  # davon landen nicht auf der erwarteten Aussage


# ---------------------------------------------------------------------- #
# Auswertung (ohne Stack)
# ---------------------------------------------------------------------- #


def schwelle_heute() -> float:
    """Die Schwelle, mit der die Suche heute arbeitet."""
    from services.search.search_orchestrator import MINIMUM_SCORE_THRESHOLD

    return MINIMUM_SCORE_THRESHOLD


def angezeigt(
    kandidaten: Iterable[Kandidat], schwelle: float, k: int = K
) -> List[Kandidat]:
    """Was die Suche bei dieser Schwelle zeigen wuerde: ueber der Schwelle, die besten k."""
    ueber = [c for c in kandidaten if c.schwellenwert > schwelle]
    ueber.sort(key=lambda c: c.rangwert, reverse=True)
    return ueber[:k]


def einordnen(fall: Fall, gezeigt: Sequence[Kandidat]) -> str:
    """
    treffer: der erste angezeigte Beitrag passt. fehltreffer: es wird etwas angezeigt,
    der erste passt nicht (bei einem Fall ohne Erwartung: irgendetwas). keine: nichts.
    """
    if not gezeigt:
        return "keine"
    if fall.erwartet and gezeigt[0].passt:
        return "treffer"
    return "fehltreffer"


def gemessen(messungen: Iterable[FallMessung]) -> List[FallMessung]:
    """Nur Faelle, deren erwartete Aussagen alle im Bestand sind."""
    return [m for m in messungen if not m.fehlt]


def auswerten(
    messungen: Iterable[FallMessung], schwelle: float, k: int = K
) -> Auswertung:
    faelle = gemessen(messungen)
    zaehler = {"treffer": 0, "fehltreffer": 0, "keine": 0}
    ohne = {"keine": 0, "fehltreffer": 0}
    passend = gezeigt_gesamt = gefunden = 0
    for m in faelle:
        gezeigt = angezeigt(m.kandidaten, schwelle, k)
        einordnung = einordnen(m.fall, gezeigt)
        gezeigt_gesamt += len(gezeigt)
        passend += sum(c.passt for c in gezeigt)
        if m.fall.erwartet:
            zaehler[einordnung] += 1
            gefunden += any(c.passt for c in gezeigt)
        else:
            ohne[einordnung] += 1
    mit_erwartung = sum(1 for m in faelle if m.fall.erwartet)
    return Auswertung(
        schwelle=schwelle,
        faelle=len(faelle),
        mit_erwartung=mit_erwartung,
        treffer=zaehler["treffer"],
        fehltreffer=zaehler["fehltreffer"],
        keine=zaehler["keine"],
        ohne_erwartung=len(faelle) - mit_erwartung,
        ohne_richtig_keine=ohne["keine"],
        ohne_fehltreffer=ohne["fehltreffer"],
        praezision=passend / gezeigt_gesamt if gezeigt_gesamt else None,
        recall_at_k=gefunden / mit_erwartung if mit_erwartung else None,
    )


def je_phaenomen(
    messungen: Iterable[FallMessung], schwelle: float, k: int = K
) -> Dict[str, Dict[str, int]]:
    """Je Phaenomen, wie viele Faelle treffer, fehltreffer und keine sind."""
    tabelle: Dict[str, Dict[str, int]] = {}
    for m in gemessen(messungen):
        zeile = tabelle.setdefault(m.fall.phaenomen, dict.fromkeys(EINORDNUNGEN, 0))
        zeile[einordnen(m.fall, angezeigt(m.kandidaten, schwelle, k))] += 1
    return tabelle


def zerfaserung(
    messungen: Iterable[FallMessung], schwelle: float, k: int = K
) -> Zerfaserung:
    """
    Wie viele Suchanfragen, die dieselbe Behauptung wie eine vorhandene Aussage sind,
    trotzdem eine neue Aussage anlegen wuerden; insgesamt und unter den Suchen ohne
    Treffer (die landen in "Hier fehlt eine Antwort").
    """
    faelle = gemessen(messungen)
    dieselbe = [m for m in faelle if m.fall.dieselbe_behauptung]
    ohne = [m for m in faelle if not angezeigt(m.kandidaten, schwelle, k)]
    ohne_dieselbe = [m for m in ohne if m.fall.dieselbe_behauptung]
    return Zerfaserung(
        schwelle=schwelle,
        dieselbe_behauptung=len(dieselbe),
        davon_neu=sum(1 for m in dieselbe if not m.landet_auf_erwarteter),
        ohne_treffer=len(ohne),
        ohne_treffer_dieselbe=len(ohne_dieselbe),
        ohne_treffer_neu=sum(1 for m in ohne_dieselbe if not m.landet_auf_erwarteter),
    )


# ---------------------------------------------------------------------- #
# Ausgabe
# ---------------------------------------------------------------------- #


def _anteil(wert: Optional[float]) -> str:
    return "–" if wert is None else f"{wert:.2f}"


def tabellen(
    messungen: Sequence[FallMessung],
    schwellen: Sequence[float],
    k: int = K,
    aktuell: Optional[float] = None,
) -> str:
    aktuell = schwelle_heute() if aktuell is None else aktuell
    faelle = gemessen(messungen)
    zeilen = [
        VORLAEUFIG,
        "",
        f"{len(faelle)} von {len(messungen)} Fällen gemessen, die besten {k} Beiträge "
        f"je Suche, Schwelle der Suche heute {aktuell}.",
        "",
        "| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer "
        "| Präzision | Recall@k |",
        "|---|---|---|---|---|---|---|",
    ]
    for schwelle in schwellen:
        a = auswerten(messungen, schwelle, k)
        markierung = " (heute)" if abs(schwelle - aktuell) < 1e-9 else ""
        zeilen.append(
            f"| {schwelle:.2f}{markierung} | {a.treffer}/{a.mit_erwartung} "
            f"| {a.fehltreffer} | {a.keine} "
            f"| {a.ohne_richtig_keine}/{a.ohne_erwartung} / {a.ohne_fehltreffer} "
            f"| {_anteil(a.praezision)} | {_anteil(a.recall_at_k)} |"
        )
    zeilen += [
        "",
        f"Je Phänomen bei {aktuell}:",
        "",
        "| Phänomen | Treffer | Fehltreffer | keine |",
        "|---|---|---|---|",
    ]
    for phaenomen, zeile in sorted(je_phaenomen(messungen, aktuell, k).items()):
        zeilen.append(
            f"| {phaenomen} | {zeile['treffer']} | {zeile['fehltreffer']} "
            f"| {zeile['keine']} |"
        )
    z = zerfaserung(messungen, aktuell, k)
    zeilen += [
        "",
        f"Zerfaserung bei {aktuell}: {z.davon_neu} von {z.dieselbe_behauptung} "
        "Suchanfragen, die dieselbe Behauptung wie eine vorhandene Aussage sind, "
        "landen nicht auf ihr. Unter den "
        f"{z.ohne_treffer} Suchen ohne Treffer sind {z.ohne_treffer_dieselbe} dieselbe "
        f"Behauptung wie eine vorhandene Aussage, davon landen {z.ohne_treffer_neu} "
        "nicht auf ihr.",
    ]
    fehlend = [m for m in messungen if m.fehlt]
    if fehlend:
        zeilen += ["", "Nicht gemessen (Aussage fehlt im Bestand):"]
        zeilen += [f"- {m.fall.id}: {', '.join(m.fehlt)}" for m in fehlend]
    return "\n".join(zeilen)


def faelle_text(
    messungen: Sequence[FallMessung],
    schwelle: Optional[float] = None,
    k: int = K,
) -> str:
    """Je Fall: Einordnung, erster angezeigter Beitrag, bester passender (auch darunter)."""
    schwelle = schwelle_heute() if schwelle is None else schwelle
    zeilen = [
        f"| Fall | Phänomen | bei {schwelle} | erster angezeigter | bester passender |",
        "|---|---|---|---|---|",
    ]
    for m in gemessen(messungen):
        gezeigt = angezeigt(m.kandidaten, schwelle, k)
        passende = [c for c in m.kandidaten if c.passt]
        bester_passender = max(passende, key=lambda c: c.rangwert, default=None)
        zeilen.append(
            f"| {m.fall.id} | {m.fall.phaenomen} | {einordnen(m.fall, gezeigt)} "
            f"| {_kandidat_text(gezeigt[0] if gezeigt else None)} "
            f"| {_kandidat_text(bester_passender)} |"
        )
    return "\n".join(zeilen)


def _kandidat_text(c: Optional[Kandidat]) -> str:
    """Score, mit dem die Schwelle verglichen wird, und woher der Treffer kommt."""
    if c is None:
        return "–"
    herkunft = c.aussage_text[:40] if c.aussage_text else "direkt"
    return f"{c.schwellenwert:.4f} {herkunft}"


def als_json(
    messungen: Sequence[FallMessung], schwellen: Sequence[float], k: int = K
) -> dict:
    heute = schwelle_heute()
    return {
        "hinweis": VORLAEUFIG,
        "k": k,
        "schwelle_heute": heute,
        "auswertung": [auswerten(messungen, s, k)._asdict() for s in schwellen],
        "zerfaserung": zerfaserung(messungen, heute, k)._asdict(),
        "faelle": [
            {
                "id": m.fall.id,
                "fehlt": list(m.fehlt),
                "landet_auf_erwarteter": m.landet_auf_erwarteter,
                "kandidaten": [c._asdict() for c in m.kandidaten],
            }
            for m in messungen
        ],
    }


# ---------------------------------------------------------------------- #
# Messung gegen einen Stack
# ---------------------------------------------------------------------- #


class Dienste(NamedTuple):
    statement_service: object
    specs: list
    reference_service: object


async def dienste_starten() -> Dienste:
    """Die Dienste wie beim Start des Semantic-Search-Service, ohne Datenbank und Jobs."""
    from api.v1.search import suchspezifikationen
    from core.config import settings
    from dependencies import (
        get_commentary_service,
        get_generic_text_service,
        get_image_service,
        get_post_service,
        get_reference_service,
        get_statement_service,
        initialize_services,
    )
    from services.embeddings.qdrant_embeddings_manager import (
        get_qdrant_embeddings_manager,
    )

    await get_qdrant_embeddings_manager(settings).start()
    initialize_services()
    return Dienste(
        statement_service=get_statement_service(),
        specs=suchspezifikationen(
            get_commentary_service(),
            get_generic_text_service(),
            get_post_service(),
            get_image_service(),
        ),
        reference_service=get_reference_service(),
    )


class _Erwartung(NamedTuple):
    aussage_ids: frozenset
    beitrag_ids: frozenset
    normalformen: frozenset
    fehlt: Tuple[str, ...]


async def _erwartung(dienste: Dienste, fall: Fall) -> _Erwartung:
    """Die erwarteten Aussagen im Bestand: ihre IDs und die ihrer Beitraege."""
    aussage_ids, beitrag_ids, fehlt = set(), set(), []
    for text in fall.erwartet:
        vorhanden = await dienste.statement_service.vorhandene_finden(text)
        # Nur der Text selbst (normalisiert), nicht eine bloss sehr aehnliche Aussage.
        if vorhanden is None or text_normalisiert(vorhanden.text) != text_normalisiert(
            text
        ):
            fehlt.append(text)
            continue
        aussage_ids.add(str(vorhanden.id))
        aussage = await dienste.statement_service.get(vorhanden.id)
        beitrag_ids.update(str(r.id) for r in aussage.replysuggestions)
    return _Erwartung(
        frozenset(aussage_ids),
        frozenset(beitrag_ids),
        frozenset(text_normalisiert(t) for t in fall.erwartet),
        tuple(fehlt),
    )


async def fall_messen(dienste: Dienste, fall: Fall) -> FallMessung:
    from api.v1.search import aussagetreffer_finden
    from services.search.search_orchestrator import (
        DIRECT_MATCH_PENALTY,
        SearchOrchestrator,
    )

    erwartung = await _erwartung(dienste, fall)

    aussagetreffer, polaritaet = await aussagetreffer_finden(
        dienste.statement_service, fall.anfrage
    )
    orchestrator = SearchOrchestrator(
        dienste.specs,
        reference_service=dienste.reference_service,
        usage_service=None,
        voting_service=None,
        schwelle=SAMMELSCHWELLE,
    )
    await orchestrator.collect_statement_based(aussagetreffer, SAMMELLIMIT, polaritaet)
    await orchestrator.collect_direct(fall.anfrage, SAMMELLIMIT)

    kandidaten = []
    for spec in dienste.specs:
        for treffer in orchestrator.results_for(spec.content_type):
            beitrag = getattr(treffer, spec.result_field)
            beitrag_id = str(beitrag.id)
            ueber_aussage = treffer.statement_id is not None
            kandidaten.append(
                Kandidat(
                    beitrag_id=beitrag_id,
                    typ=spec.content_type.value,
                    aussage_text=treffer.statement_text if ueber_aussage else "",
                    # Ein direkter Treffer steht mit DIRECT_MATCH_PENALTY gedaempft im
                    # Ergebnis, die Schwelle prueft aber den Rohscore.
                    schwellenwert=(
                        treffer.score
                        if ueber_aussage
                        else treffer.score / DIRECT_MATCH_PENALTY
                    ),
                    rangwert=treffer.score,
                    passt=(
                        beitrag_id in erwartung.beitrag_ids
                        or (
                            ueber_aussage
                            and str(treffer.statement_id) in erwartung.aussage_ids
                        )
                    ),
                )
            )

    landet = None
    if fall.dieselbe_behauptung:
        vorhanden = await dienste.statement_service.vorhandene_finden(fall.anfrage)
        landet = (
            vorhanden is not None
            and text_normalisiert(vorhanden.text) in erwartung.normalformen
        )
    return FallMessung(fall, tuple(kandidaten), erwartung.fehlt, landet)


async def messen(faelle: Sequence[Fall] = FAELLE) -> List[FallMessung]:
    dienste = await dienste_starten()
    return [await fall_messen(dienste, fall) for fall in faelle]


def _schwellen(text: str) -> Tuple[float, ...]:
    return tuple(float(s) for s in text.split(",") if s.strip())


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--schwellen",
        type=_schwellen,
        default=STANDARD_SCHWELLEN,
        help="durch Komma getrennt, z. B. 0.78,0.8,0.82",
    )
    parser.add_argument("--k", type=int, default=K)
    parser.add_argument("--faelle", action="store_true", help="jeden Fall ausgeben")
    parser.add_argument("--json", metavar="PFAD", help="Messung als JSON schreiben")
    args = parser.parse_args(argv)

    from core.logging import LoggingConfig, initialize_logging

    # Nur Warnungen, damit die Tabellen lesbar bleiben.
    initialize_logging(LoggingConfig(level="WARNING", enable_console_utf8=False))
    messungen = asyncio.run(messen())
    print(tabellen(messungen, args.schwellen, args.k))
    if args.faelle:
        print()
        print(faelle_text(messungen, k=args.k))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as datei:
            json.dump(
                als_json(messungen, args.schwellen, args.k),
                datei,
                ensure_ascii=False,
                indent=1,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
