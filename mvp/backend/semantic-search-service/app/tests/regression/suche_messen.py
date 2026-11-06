"""
Misst das Suchtestset (suche_testset.py) gegen den Bestand eines Stacks: je Schwelle
Treffer, Fehltreffer und keine Treffer, dazu Praezision, Recall@k und die Zerfaserung.
Regeln, Ergebnis und Exit-Codes in SUCHTESTSET.md.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.suche_messen            # Tabellen
    ../venv/bin/python -m tests.regression.suche_messen --faelle   # dazu jeder Fall
    ../venv/bin/python -m tests.regression.suche_messen --json messung.json

Verbindet sich wie der Dienst (SEMANTIC_SEARCH_QDRANT_URL, ..._QDRANT_COLLECTION) und
laedt das Einbettungsmodell (~1,5 GB RAM). Im Container des Semantic-Search-Service:
`python -m tests.regression.suche_messen`.

Liest nur: Es ruft dieselben Schritte wie die Suche (api/v1/search.py: Aussagetreffer,
Polaritaetsfilter, Schlagwort-Ueberlappung, dann der SearchOrchestrator mit Limit und
Kuerzen), aber nicht den Endpunkt. Es legt keine Aussage aus der Suchanfrage an und
zaehlt weder Suchereignis noch Suche ohne Treffer. Je Schwelle laeuft der Orchestrator
einmal, so wie er im Dienst mit dieser Schwelle liefe; die Aussagetreffer werden je Fall
nur einmal gesucht.

Schnittstelle fuer Folgetickets (naechtlicher Lauf, Stemmer, Modellwechsel): messen()
liefert je Fall eine FallMessung, auswerten(), je_phaenomen() und zerfaserung() rechnen
daraus ohne Stack; --json schreibt alles als Datei.
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)

from tests.regression.suche_testset import FAELLE, Fall
from utils.text_normalisierung import text_normalisiert

if TYPE_CHECKING:
    from services.content.statement_service import StatementService
    from services.search.search_orchestrator import (
        ContentTypeSearchSpec,
        SearchOrchestrator,
    )

# Die Schwelle der Suche steht in services/search/search_orchestrator.py
# (MINIMUM_SCORE_THRESHOLD, siehe schwelle_heute()). Das Modul wird erst bei Bedarf
# geladen: Es braucht ein initialisiertes Logging (main()).

# So viele Treffer je Beitragstyp fragt das Frontend an (result-view.component.ts).
K = 10
STANDARD_SCHWELLEN = (0.76, 0.78, 0.79, 0.80, 0.81, 0.82, 0.84, 0.86)
# Die Abschnitte der Ergebnisseite in ihrer Reihenfolge (result-view.component.html);
# Bilder zeigt sie nicht.
ANGEZEIGTE_TYPEN = ("commentary", "generic_text", "post")
# Recall@k ueber die Ergebnisseite in ihrer Reihenfolge (ANGEZEIGTE_TYPEN).
RECALL_BEI = (5, 10)
# Exit-Code, wenn kein Fall mit Erwartung gemessen wurde: Der Bestand passt nicht zum
# Set (leere oder falsche Sammlung, Startbestand ohne passende Faelle).
BESTAND_PASST_NICHT = 2

VORLAEUFIG = (
    "Vorläufig: gemessen am Testbestand (Seed). Nach dem Startbestand (#288) einmal neu "
    "messen, siehe SUCHTESTSET.md."
)

EINORDNUNGEN = ("treffer", "fehltreffer", "keine")


class AngezeigterBeitrag(NamedTuple):
    """Ein Beitrag, den die Suche zu einer Suchanfrage zeigt."""

    beitrag_id: str
    typ: str
    aussage_text: str  # leer bei einem direkten Treffer
    score: float  # wie im Suchergebnis (direkt: mit DIRECT_MATCH_PENALTY)
    passt: bool


class FallMessung(NamedTuple):
    fall: Fall
    # Je Schwelle die angezeigten Beitraege in der Reihenfolge der Ergebnisseite:
    # Kommentare, Hintergrundinfos, Posts, je Typ hoechstens k.
    angezeigt: Dict[float, Tuple[AngezeigterBeitrag, ...]]
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
    # Je k in RECALL_BEI: Faelle mit Erwartung und einem passenden Beitrag unter den
    # ersten k der Ergebnisseite. Recall@1 ist Treffer / mit_erwartung.
    recall_bei: Dict[int, Optional[float]]
    # Faelle mit Erwartung und einem passenden Beitrag irgendwo auf der Ergebnisseite
    # (je Beitragstyp hoechstens k, also bis zu drei mal k Beitraege).
    recall_seite: Optional[float]
    direkt_angezeigt: int  # angezeigte Beitraege ohne Aussage (direkter Weg)
    direkt_passend: int


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


def einordnen(fall: Fall, gezeigt: Sequence[AngezeigterBeitrag]) -> str:
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


def auswerten(messungen: Iterable[FallMessung], schwelle: float) -> Auswertung:
    faelle = gemessen(messungen)
    zaehler = {"treffer": 0, "fehltreffer": 0, "keine": 0}
    ohne = {"keine": 0, "fehltreffer": 0}
    passend = gezeigt_gesamt = gefunden = direkt = direkt_passend = 0
    gefunden_bei = dict.fromkeys(RECALL_BEI, 0)
    for m in faelle:
        gezeigt = m.angezeigt[schwelle]
        einordnung = einordnen(m.fall, gezeigt)
        gezeigt_gesamt += len(gezeigt)
        passend += sum(c.passt for c in gezeigt)
        direkt += sum(1 for c in gezeigt if not c.aussage_text)
        direkt_passend += sum(1 for c in gezeigt if not c.aussage_text and c.passt)
        if m.fall.erwartet:
            zaehler[einordnung] += 1
            gefunden += any(c.passt for c in gezeigt)
            for k in RECALL_BEI:
                gefunden_bei[k] += any(c.passt for c in gezeigt[:k])
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
        recall_bei={
            k: (n / mit_erwartung if mit_erwartung else None)
            for k, n in gefunden_bei.items()
        },
        recall_seite=gefunden / mit_erwartung if mit_erwartung else None,
        direkt_angezeigt=direkt,
        direkt_passend=direkt_passend,
    )


def je_phaenomen(
    messungen: Iterable[FallMessung], schwelle: float
) -> Dict[str, Dict[str, int]]:
    """Je Phaenomen, wie viele Faelle treffer, fehltreffer und keine sind."""
    tabelle: Dict[str, Dict[str, int]] = {}
    for m in gemessen(messungen):
        zeile = tabelle.setdefault(m.fall.phaenomen, dict.fromkeys(EINORDNUNGEN, 0))
        zeile[einordnen(m.fall, m.angezeigt[schwelle])] += 1
    return tabelle


def zerfaserung(messungen: Iterable[FallMessung], schwelle: float) -> Zerfaserung:
    """
    Wie viele Suchanfragen, die dieselbe Behauptung wie eine vorhandene Aussage sind,
    trotzdem eine neue Aussage anlegen wuerden; insgesamt und unter den Suchen ohne
    Treffer (die landen in "Hier fehlt eine Antwort"). Nur gemessene Faelle zaehlen:
    landet_auf_erwarteter ist True oder False, None hiesse nicht geprueft.
    """
    faelle = gemessen(messungen)
    dieselbe = [m for m in faelle if m.fall.dieselbe_behauptung]
    ohne = [m for m in faelle if not m.angezeigt[schwelle]]
    ohne_dieselbe = [m for m in ohne if m.fall.dieselbe_behauptung]
    return Zerfaserung(
        schwelle=schwelle,
        dieselbe_behauptung=len(dieselbe),
        davon_neu=sum(1 for m in dieselbe if m.landet_auf_erwarteter is False),
        ohne_treffer=len(ohne),
        ohne_treffer_dieselbe=len(ohne_dieselbe),
        ohne_treffer_neu=sum(
            1 for m in ohne_dieselbe if m.landet_auf_erwarteter is False
        ),
    )


# ---------------------------------------------------------------------- #
# Ausgabe
# ---------------------------------------------------------------------- #


def _anteil(wert: Optional[float]) -> str:
    return "–" if wert is None else f"{wert:.2f}"


def tabellen(
    messungen: Sequence[FallMessung],
    schwellen: Sequence[float],
    aktuell: Optional[float] = None,
    k: int = K,
) -> str:
    aktuell = schwelle_heute() if aktuell is None else aktuell
    faelle = gemessen(messungen)
    zeilen = [
        VORLAEUFIG,
        "",
        f"{len(faelle)} von {len(messungen)} Fällen gemessen, je Beitragstyp höchstens "
        f"{k} Beiträge, Schwelle der Suche heute {aktuell}.",
        "",
        "| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer "
        "| Präzision | "
        + "".join(f"Recall@{k} | " for k in RECALL_BEI)
        + "Recall (Seite) | direkt: passend / angezeigt |",
        "|---|---|---|---|---|---|" + "---|" * len(RECALL_BEI) + "---|---|",
    ]
    for schwelle in schwellen:
        a = auswerten(messungen, schwelle)
        markierung = " (heute)" if abs(schwelle - aktuell) < 1e-9 else ""
        zeilen.append(
            f"| {schwelle:.2f}{markierung} | {a.treffer}/{a.mit_erwartung} "
            f"| {a.fehltreffer} | {a.keine} "
            f"| {a.ohne_richtig_keine}/{a.ohne_erwartung} / {a.ohne_fehltreffer} "
            f"| {_anteil(a.praezision)} | "
            + "".join(f"{_anteil(a.recall_bei[k])} | " for k in RECALL_BEI)
            + f"{_anteil(a.recall_seite)} "
            f"| {a.direkt_passend} / {a.direkt_angezeigt} |"
        )
    zeilen += [
        "",
        f"Je Phänomen bei {aktuell}:",
        "",
        "| Phänomen | Treffer | Fehltreffer | keine |",
        "|---|---|---|---|",
    ]
    for phaenomen, zeile in sorted(je_phaenomen(messungen, aktuell).items()):
        zeilen.append(
            f"| {phaenomen} | {zeile['treffer']} | {zeile['fehltreffer']} "
            f"| {zeile['keine']} |"
        )
    z = zerfaserung(messungen, aktuell)
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
    messungen: Sequence[FallMessung], schwelle: Optional[float] = None
) -> str:
    """Je Fall: Einordnung, erster angezeigter und erster passender angezeigter Beitrag."""
    schwelle = schwelle_heute() if schwelle is None else schwelle
    zeilen = [
        f"| Fall | Phänomen | bei {schwelle} | erster angezeigter "
        "| erster passender (Platz) |",
        "|---|---|---|---|---|",
    ]
    for m in gemessen(messungen):
        gezeigt = m.angezeigt[schwelle]
        platz, passender = next(
            ((i, c) for i, c in enumerate(gezeigt, 1) if c.passt), (None, None)
        )
        zeilen.append(
            f"| {m.fall.id} | {m.fall.phaenomen} | {einordnen(m.fall, gezeigt)} "
            f"| {_beitrag_text(gezeigt[0] if gezeigt else None)} "
            f"| {_beitrag_text(passender)}{f' ({platz})' if platz else ''} |"
        )
    return "\n".join(zeilen)


def _beitrag_text(c: Optional[AngezeigterBeitrag]) -> str:
    if c is None:
        return "–"
    herkunft = c.aussage_text[:40] if c.aussage_text else "direkt"
    return f"{c.typ} {c.score:.3f} {herkunft}"


def als_json(
    messungen: Sequence[FallMessung],
    schwellen: Sequence[float],
    k: int = K,
    umgebung: Optional[dict] = None,
) -> dict:
    """
    Die ganze Messung fuer Vergleiche (naechtlicher Lauf, Stemmer, Modellwechsel).
    Schwellen stehen als Text mit zwei Stellen ("0.80"), weil JSON-Schluessel Texte
    sind; umgebung (Modell, Sammlung, Datum) setzt main().
    """
    heute = schwelle_heute()
    return {
        "hinweis": VORLAEUFIG,
        "umgebung": umgebung or {},
        "k": k,
        "schwelle_heute": heute,
        "auswertung": [auswerten(messungen, s)._asdict() for s in schwellen],
        "je_phaenomen": je_phaenomen(messungen, heute),
        "zerfaserung": zerfaserung(messungen, heute)._asdict(),
        "faelle": [
            {
                "id": m.fall.id,
                "anfrage": m.fall.anfrage,
                "form": m.fall.form,
                "phaenomen": m.fall.phaenomen,
                "quelle": m.fall.quelle,
                "erwartet": list(m.fall.erwartet),
                "dieselbe_behauptung": m.fall.dieselbe_behauptung,
                "fehlt": list(m.fehlt),
                "landet_auf_erwarteter": m.landet_auf_erwarteter,
                "einordnung": {
                    f"{s:.2f}": einordnen(m.fall, kandidaten)
                    for s, kandidaten in sorted(m.angezeigt.items())
                },
                "angezeigt": {
                    f"{s:.2f}": [c._asdict() for c in kandidaten]
                    for s, kandidaten in sorted(m.angezeigt.items())
                },
            }
            for m in messungen
        ],
    }


# ---------------------------------------------------------------------- #
# Messung gegen einen Stack
# ---------------------------------------------------------------------- #


class Dienste(NamedTuple):
    statement_service: "StatementService"
    specs: List["ContentTypeSearchSpec"]
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
    # Die NLI-Stufe laedt im Hintergrund; ohne Warten mischt die Messung bis dahin die
    # Schwelle ein (#387).
    await get_statement_service().nli_laden_abwarten()
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


async def dienste_beenden() -> None:
    from core.config import settings
    from services.embeddings.qdrant_embeddings_manager import (
        get_qdrant_embeddings_manager,
    )

    await get_qdrant_embeddings_manager(settings).shutdown()


class _Erwartung(NamedTuple):
    aussage_ids: frozenset
    beitrag_ids: frozenset
    fehlt: Tuple[str, ...]


async def _aussage_im_bestand(dienste: Dienste, text: str):
    """
    Die Aussage mit genau diesem Text (normalisiert) oder None. vorhandene_finden sucht
    zuerst ueber die Normalform im Keyword-Index; nur Altbestand ohne dieses Feld geht
    ueber die Vektorsuche. Eine bloss sehr aehnliche Aussage zaehlt nicht.
    """
    vorhanden = await dienste.statement_service.vorhandene_finden(text)
    if vorhanden is None or text_normalisiert(vorhanden.text) != text_normalisiert(
        text
    ):
        return None
    return await dienste.statement_service.get(vorhanden.id)


async def _erwartung(dienste: Dienste, fall: Fall, cache: dict) -> _Erwartung:
    """Die erwarteten Aussagen im Bestand: ihre IDs und die ihrer Beitraege."""
    aussage_ids, beitrag_ids, fehlt = set(), set(), []
    for text in fall.erwartet:
        if text not in cache:
            cache[text] = await _aussage_im_bestand(dienste, text)
        aussage = cache[text]
        if aussage is None:
            fehlt.append(text)
            continue
        aussage_ids.add(str(aussage.id))
        beitrag_ids.update(str(r.id) for r in aussage.replysuggestions)
    return _Erwartung(frozenset(aussage_ids), frozenset(beitrag_ids), tuple(fehlt))


def angezeigte_beitraege(
    orchestrator: "SearchOrchestrator",
    specs: Sequence["ContentTypeSearchSpec"],
    erwartung: _Erwartung,
) -> Tuple[AngezeigterBeitrag, ...]:
    """
    Was die Ergebnisseite aus dem Ergebnis des Orchestrators zeigt, in ihrer
    Reihenfolge: Kommentare, Hintergrundinfos, Posts. Bilder laufen in der Suche mit
    (sie zaehlen beim Limit), angezeigt werden sie nicht. Ein Beitrag passt, wenn er an
    einer erwarteten Aussage haengt oder ueber sie gefunden wurde.
    """
    angezeigte = sorted(
        (s for s in specs if s.content_type.value in ANGEZEIGTE_TYPEN),
        key=lambda s: ANGEZEIGTE_TYPEN.index(s.content_type.value),
    )
    gezeigt = []
    for spec in angezeigte:
        for treffer in orchestrator.results_for(spec.content_type):
            beitrag_id = str(getattr(treffer, spec.result_field).id)
            ueber_aussage = treffer.statement_id is not None
            gezeigt.append(
                AngezeigterBeitrag(
                    beitrag_id=beitrag_id,
                    typ=spec.content_type.value,
                    aussage_text=treffer.statement_text if ueber_aussage else "",
                    score=treffer.score,
                    passt=(
                        beitrag_id in erwartung.beitrag_ids
                        or (
                            ueber_aussage
                            and str(treffer.statement_id) in erwartung.aussage_ids
                        )
                    ),
                )
            )
    return tuple(gezeigt)


async def fall_messen(
    dienste: Dienste,
    fall: Fall,
    schwellen: Sequence[float],
    k: int = K,
    cache: Optional[dict] = None,
) -> FallMessung:
    from api.v1.search import aussagetreffer_finden, treffer_sammeln
    from services.search.search_orchestrator import SearchOrchestrator

    erwartung = await _erwartung(dienste, fall, {} if cache is None else cache)
    aussagetreffer, polaritaet = await aussagetreffer_finden(
        dienste.statement_service, fall.anfrage
    )

    angezeigt = {}
    for schwelle in schwellen:
        # Wie search_by_text, mit dem Limit der Anfrage je Beitragstyp.
        orchestrator = SearchOrchestrator(
            dienste.specs,
            reference_service=dienste.reference_service,
            usage_service=None,
            voting_service=None,
            schwelle=schwelle,
        )
        await treffer_sammeln(orchestrator, fall.anfrage, k, aussagetreffer, polaritaet)

        angezeigt[schwelle] = angezeigte_beitraege(
            orchestrator, dienste.specs, erwartung
        )

    landet = None
    if fall.dieselbe_behauptung:
        vorhanden = await dienste.statement_service.vorhandene_finden(fall.anfrage)
        landet = vorhanden is not None and str(vorhanden.id) in erwartung.aussage_ids
    return FallMessung(fall, angezeigt, erwartung.fehlt, landet)


def mit_schwelle_heute(schwellen: Iterable[float]) -> Tuple[float, ...]:
    """
    Die Schwellen aufsteigend, die von heute immer dabei: Phaenomene, Zerfaserung und
    die Faelle in tabellen(), faelle_text() und als_json() beziehen sich auf sie.
    """
    return tuple(sorted(set(schwellen) | {schwelle_heute()}))


async def messen(
    schwellen: Sequence[float], faelle: Sequence[Fall] = FAELLE, k: int = K
) -> List[FallMessung]:
    schwellen = mit_schwelle_heute(schwellen)
    dienste = await dienste_starten()
    try:
        cache: dict = {}
        return [await fall_messen(dienste, f, schwellen, k, cache) for f in faelle]
    finally:
        await dienste_beenden()


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
    parser.add_argument("--k", type=int, default=K, help="Beitraege je Typ")
    parser.add_argument("--faelle", action="store_true", help="jeden Fall ausgeben")
    parser.add_argument("--json", metavar="PFAD", help="Messung als JSON schreiben")
    args = parser.parse_args(argv)

    from core.logging import LoggingConfig, initialize_logging

    # Nur Warnungen, damit die Tabellen lesbar bleiben.
    initialize_logging(LoggingConfig(level="WARNING", enable_console_utf8=False))
    heute = schwelle_heute()
    schwellen = mit_schwelle_heute(args.schwellen)

    messungen = asyncio.run(messen(schwellen, k=args.k))
    print(tabellen(messungen, schwellen, heute, args.k))
    if args.faelle:
        print()
        print(faelle_text(messungen, heute))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as datei:
            json.dump(
                als_json(messungen, schwellen, args.k, _umgebung()),
                datei,
                ensure_ascii=False,
                indent=1,
            )
    if not any(m.fall.erwartet for m in gemessen(messungen)):
        print(
            "Kein Fall mit Erwartung gemessen: Der Bestand passt nicht zum Suchtestset "
            "(leere oder falsche Sammlung, oder Faelle fuer den Startbestand fehlen). "
            "Die Zahlen oben sind nicht aussagekraeftig.",
            file=sys.stderr,
        )
        return BESTAND_PASST_NICHT
    return 0


def _umgebung() -> dict:
    """Womit gemessen wurde, fuer den Vergleich zweier Messungen."""
    from core.config import EMBEDDING_MODELL, settings

    return {
        "gemessen_am": date.today().isoformat(),
        "modell": EMBEDDING_MODELL,
        "sammlung": settings.qdrant_collection,
        "dubletten_schwelle": settings.statement_similarity_threshold,
    }


if __name__ == "__main__":
    sys.exit(main())
