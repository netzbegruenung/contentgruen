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
import statistics
import sys
import time
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
# Recall je Phaenomen: das groesste k aus RECALL_BEI (wie das Tor fuer Roadmap-Stufe 3).
RECALL_JE_PHAENOMEN = max(RECALL_BEI)
# Exit-Code, wenn kein Fall mit Erwartung gemessen wurde: Der Bestand passt nicht zum
# Set (leere oder falsche Sammlung, ein Bestand ohne Aussagen aus Seed oder Startbestand).
BESTAND_PASST_NICHT = 2
# Aehnliche Aussagen wie die Vorschlaege im Beitragsformular (statement.service.ts:
# VORSCHLAG_ANZAHL, Settings.aussage_vorschlag_schwelle): hoechstens so viele gepflegte
# Aussagen, und nur ab dieser unteren Grenze. Ein Unit-Test haelt beide Stellen gleich.
AEHNLICHE_ANZAHL = 3
AEHNLICHE_AB = 0.885

HINWEIS = (
    "Bewertet am Seed und am Entwurf des Startbestands, lokal (SUCHTESTSET.md). Nach "
    "dem Import des Startbestands auf Produktion (#288) einmal zur Kontrolle messen."
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
    # Die aehnlichen Aussagen zur Suchanfrage (AEHNLICHE_ANZAHL, ab AEHNLICHE_AB), je
    # Aussage: ist sie eine erwartete? Unabhaengig von der Schwelle der Suche.
    aehnliche: Tuple[bool, ...] = ()
    # Aussagen aus fall.nur_ohne, die im gemessenen Bestand stehen: Der Fall ist dort
    # nicht fremd und zaehlt nicht mit. (Fehlt eine aus fall.nur_mit, steht sie in fehlt.)
    ausgeschlossen: Tuple[str, ...] = ()
    # Wie lange aussagetreffer_finden fuer diesen Fall brauchte (Millisekunden):
    # Einbettung, Aussagesuche, Polaritaet (Wortlisten oder NLI-Modell, #574) und
    # Schlagwoerter. None, wenn der Fall nicht gemessen wurde.
    aussagetreffer_ms: Optional[float] = None
    # Mit dem Ersatz gemessen (fall.ersatz, #606): Dem Bestand fehlen diese Aussagen aus
    # dem urspruenglichen erwartet; fall traegt dann die Erwartung des Ersatzes.
    ersatz_fuer: Tuple[str, ...] = ()
    # Nur bei dieselbe_behauptung und NLI-Stufe "an": Hat vorhandene_finden ohne Urteil
    # eines Modells entschieden? RUECKFALL_SCHWELLE: Das erste Modell urteilte nicht
    # (nicht rechtzeitig frei, DIESELBE_WARTET_HOECHSTENS, oder nicht verfuegbar), es
    # galt die Schwelle. RUECKFALL_OHNE_BESTAETIGER: ebenso der Bestaetiger, es galt nur
    # das erste Modell. Leer: kein Rueckfall.
    rueckfall: str = ""


RUECKFALL_SCHWELLE = "schwelle"
RUECKFALL_OHNE_BESTAETIGER = "ohne_bestaetiger"


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


class Rueckfaelle(NamedTuple):
    geprueft: int  # gemessene Faelle mit dieselbe_behauptung (vorhandene_finden)
    schwelle: Tuple[str, ...]  # Fall-IDs mit RUECKFALL_SCHWELLE
    ohne_bestaetiger: Tuple[str, ...]  # Fall-IDs mit RUECKFALL_OHNE_BESTAETIGER


class AehnlicheAussagen(NamedTuple):
    mit_erwartung: int  # gemessene Faelle mit Erwartung
    erwartete_dabei: int  # davon eine erwartete Aussage unter den aehnlichen
    ohne_erwartung: int  # gemessene Faelle ohne Erwartung
    ohne_mit_vorschlag: int  # davon mit mindestens einer aehnlichen Aussage


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


def passend_unter(gezeigt: Sequence[AngezeigterBeitrag], k: int) -> bool:
    """Ist unter den ersten k angezeigten Beitraegen ein passender (Zaehler von Recall@k)?"""
    return any(c.passt for c in gezeigt[:k])


def gemessen(messungen: Iterable[FallMessung]) -> List[FallMessung]:
    """
    Nur Faelle, deren erwartete Aussagen (und die aus nur_mit) alle im Bestand sind und
    keine aus nur_ohne.
    """
    return [m for m in messungen if not m.fehlt and not m.ausgeschlossen]


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
                gefunden_bei[k] += passend_unter(gezeigt, k)
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
    """
    Je Phaenomen, wie viele Faelle treffer, fehltreffer und keine sind, dazu
    mit_erwartung und gefunden@k (k = RECALL_JE_PHAENOMEN): Faelle mit Erwartung und
    einem passenden Beitrag unter den ersten k (Recall@k = gefunden@k / mit_erwartung).
    """
    gefunden_k = f"gefunden@{RECALL_JE_PHAENOMEN}"
    tabelle: Dict[str, Dict[str, int]] = {}
    for m in gemessen(messungen):
        zeile = tabelle.setdefault(
            m.fall.phaenomen,
            {**dict.fromkeys(EINORDNUNGEN, 0), "mit_erwartung": 0, gefunden_k: 0},
        )
        gezeigt = m.angezeigt[schwelle]
        zeile[einordnen(m.fall, gezeigt)] += 1
        if m.fall.erwartet:
            zeile["mit_erwartung"] += 1
            zeile[gefunden_k] += passend_unter(gezeigt, RECALL_JE_PHAENOMEN)
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


def rueckfaelle(messungen: Iterable[FallMessung]) -> Rueckfaelle:
    """In welchen gemessenen Faellen vorhandene_finden ohne Urteil eines NLI-Modells
    entschied (FallMessung.rueckfall). Solche Faelle verfaelschen die Zerfaserung still
    in Richtung Schwelle bzw. ohne Bestaetiger."""
    dieselbe = [m for m in gemessen(messungen) if m.landet_auf_erwarteter is not None]
    return Rueckfaelle(
        geprueft=len(dieselbe),
        schwelle=tuple(
            m.fall.id for m in dieselbe if m.rueckfall == RUECKFALL_SCHWELLE
        ),
        ohne_bestaetiger=tuple(
            m.fall.id for m in dieselbe if m.rueckfall == RUECKFALL_OHNE_BESTAETIGER
        ),
    )


def aehnliche_aussagen(messungen: Iterable[FallMessung]) -> AehnlicheAussagen:
    """
    Untere Grenze fuer aehnliche Aussagen: Bei wie vielen Faellen mit Erwartung ist eine
    erwartete Aussage unter den aehnlichen, bei wie vielen ohne Erwartung erscheint
    trotzdem eine (die waere unpassend).
    """
    faelle = gemessen(messungen)
    mit = [m for m in faelle if m.fall.erwartet]
    ohne = [m for m in faelle if not m.fall.erwartet]
    return AehnlicheAussagen(
        mit_erwartung=len(mit),
        erwartete_dabei=sum(1 for m in mit if any(m.aehnliche)),
        ohne_erwartung=len(ohne),
        ohne_mit_vorschlag=sum(1 for m in ohne if m.aehnliche),
    )


# ---------------------------------------------------------------------- #
# Ausgabe
# ---------------------------------------------------------------------- #


def laufzeit(messungen: Iterable[FallMessung]) -> Optional[Tuple[float, float]]:
    """Median und 95. Perzentil von aussagetreffer_ms ueber die gemessenen Faelle."""
    werte = sorted(m.aussagetreffer_ms for m in messungen if m.aussagetreffer_ms)
    if not werte:
        return None
    p95 = werte[min(len(werte) - 1, round(0.95 * (len(werte) - 1)))]
    return statistics.median(werte), p95


def polaritaet_modus() -> str:
    from core.config import settings

    return f"Polarität mit NLI: {settings.suche_polaritaet_nli}"


def zuordnung_weg(settings=None) -> dict:
    """
    Der Weg der Pruefung auf dieselbe Aussage, mit dem dieser Prozess misst: der Modus
    der NLI-Stufe und ob der Bestaetiger mitentscheidet. Aus der geladenen Konfiguration
    (core.config.settings, aus der auch der StatementService der Messung entsteht);
    vorhandene_finden fragt NLI und Bestaetiger nur bei "an"; bei "schatten" und "aus"
    gilt dort die Schwelle, der Bestaetiger wirkt also nur mit "an". Die Zerfaserung
    haengt davon ab (SUCHTESTSET.md, Zerfaserung).
    """
    if settings is None:
        from core.config import settings
    modus = settings.dieselbe_aussage_nli
    return {
        "dieselbe_aussage_nli": modus,
        "nli_bestaetiger": bool(settings.nli_bestaetiger and modus == "an"),
    }


def zuordnung_text(weg: Optional[dict] = None) -> str:
    weg = zuordnung_weg() if weg is None else weg
    modus = weg["dieselbe_aussage_nli"]
    if modus != "an":
        return (
            f"Zuordnung (dieselbe Aussage): NLI-Stufe {modus}, es gilt die Schwelle "
            "(ohne NLI und Bestätiger)."
        )
    bestaetiger = "an" if weg["nli_bestaetiger"] else "aus"
    return f"Zuordnung (dieselbe Aussage): NLI-Stufe an, Bestätiger {bestaetiger}."


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
        HINWEIS,
        "",
        f"{len(faelle)} von {len(messungen)} Fällen gemessen, je Beitragstyp höchstens "
        f"{k} Beiträge, Schwelle der Suche heute {aktuell}.",
        zuordnung_text(),
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
        "| Phänomen | Treffer | Fehltreffer | keine "
        f"| passend unter den ersten {RECALL_JE_PHAENOMEN} / mit Erwartung |",
        "|---|---|---|---|---|",
    ]
    for phaenomen, zeile in sorted(je_phaenomen(messungen, aktuell).items()):
        zeilen.append(
            f"| {phaenomen} | {zeile['treffer']} | {zeile['fehltreffer']} "
            f"| {zeile['keine']} "
            f"| {zeile[f'gefunden@{RECALL_JE_PHAENOMEN}']}/{zeile['mit_erwartung']} |"
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
    r = rueckfaelle(messungen)
    if r.schwelle or r.ohne_bestaetiger:
        zeilen += ["", f"Ohne NLI-Urteil entschieden (von {r.geprueft} Prüfungen):"]
        if r.schwelle:
            zeilen.append(
                f"- {len(r.schwelle)} auf die Schwelle zurückgefallen, das NLI-Modell "
                f"war nicht rechtzeitig frei oder nicht verfügbar: {', '.join(r.schwelle)}"
            )
        if r.ohne_bestaetiger:
            zeilen.append(
                f"- {len(r.ohne_bestaetiger)} ohne Bestätiger, er war nicht "
                f"rechtzeitig frei oder nicht verfügbar: {', '.join(r.ohne_bestaetiger)}"
            )
    a = aehnliche_aussagen(messungen)
    zeilen += [
        "",
        f"Ähnliche Aussagen (höchstens {AEHNLICHE_ANZAHL}, ab {AEHNLICHE_AB}): "
        f"erwartete Aussage dabei bei {a.erwartete_dabei} von {a.mit_erwartung} "
        f"Fällen mit Erwartung; {a.ohne_mit_vorschlag} von {a.ohne_erwartung} Fällen "
        "ohne Erwartung zeigen trotzdem eine.",
    ]
    dauer = laufzeit(messungen)
    if dauer:
        zeilen += [
            "",
            "Laufzeit der Aussagetreffer je Suche (Einbettung, Aussagesuche, Polarität, "
            f"Schlagwörter): Median {dauer[0]:.0f} ms, 95. Perzentil {dauer[1]:.0f} ms "
            f"({polaritaet_modus()}).",
        ]
    fehlend = [m for m in messungen if m.fehlt]
    if fehlend:
        zeilen += ["", "Nicht gemessen (Aussage fehlt im Bestand):"]
        zeilen += [f"- {m.fall.id}: {', '.join(m.fehlt)}" for m in fehlend]
    mit_ersatz = [m for m in gemessen(messungen) if m.ersatz_fuer]
    if mit_ersatz:
        zeilen += [
            "",
            "Mit Ersatz gemessen (Aussage fehlt im Bestand, erwartet statt ihrer):",
        ]
        zeilen += [
            f"- {m.fall.id}: {', '.join(m.ersatz_fuer)} -> {', '.join(m.fall.erwartet)}"
            for m in mit_ersatz
        ]
    ausgeschlossen = [m for m in messungen if m.ausgeschlossen and not m.fehlt]
    if ausgeschlossen:
        zeilen += [
            "",
            "Nicht gemessen (nicht fremd, der Bestand hat eine Aussage dazu):",
        ]
        zeilen += [
            f"- {m.fall.id}: {', '.join(m.ausgeschlossen)}" for m in ausgeschlossen
        ]
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
        "hinweis": HINWEIS,
        "umgebung": umgebung or {},
        "k": k,
        "schwelle_heute": heute,
        "auswertung": [auswerten(messungen, s)._asdict() for s in schwellen],
        "je_phaenomen": je_phaenomen(messungen, heute),
        "zerfaserung": zerfaserung(messungen, heute)._asdict(),
        "rueckfaelle": rueckfaelle(messungen)._asdict(),
        "aehnliche_aussagen": aehnliche_aussagen(messungen)._asdict(),
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
                "ersatz_fuer": list(m.ersatz_fuer),
                "ausgeschlossen": list(m.ausgeschlossen),
                "landet_auf_erwarteter": m.landet_auf_erwarteter,
                "rueckfall": m.rueckfall,
                "aehnliche": list(m.aehnliche),
                "aussagetreffer_ms": m.aussagetreffer_ms,
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


class UrteileZaehlen:
    """
    Reicht urteile() an ein NLI-Modell durch und zaehlt, wie oft es kein Urteil gab
    (None: nicht rechtzeitig frei oder nicht verfuegbar). Der Dienst faellt dann still
    zurueck (StatementService._nli_entscheiden, stufe.dieselben_finden); die Messung
    setzt den Zaehler vor ihre Modelle, ohne das Verhalten zu aendern.
    """

    def __init__(self, pruefer):
        self._pruefer = pruefer
        self.ohne_urteil = 0

    async def urteile(self, paare, warte_hoechstens=None):
        urteile = await self._pruefer.urteile(paare, warte_hoechstens=warte_hoechstens)
        if urteile is None:
            self.ohne_urteil += 1
        return urteile

    def __getattr__(self, name):
        return getattr(self._pruefer, name)


class NliZaehler(NamedTuple):
    """Die Zaehler vor dem ersten Modell und dem Bestaetiger des StatementService (je
    None, wenn er keins hat)."""

    nli: Optional[UrteileZaehlen]
    bestaetiger: Optional[UrteileZaehlen]

    @classmethod
    def einsetzen(cls, statement_service) -> "NliZaehler":
        """Setzt die Zaehler vor die Modelle des StatementService (Attribute _nli und
        _bestaetiger, siehe dessen __init__)."""
        zaehler = []
        for attribut in ("_nli", "_bestaetiger"):
            modell = getattr(statement_service, attribut)
            z = None if modell is None else UrteileZaehlen(modell)
            if z is not None:
                setattr(statement_service, attribut, z)
            zaehler.append(z)
        return cls(*zaehler)

    def stand(self) -> Tuple[int, int]:
        return tuple(0 if z is None else z.ohne_urteil for z in self)

    def rueckfall_seit(self, vorher: Tuple[int, int]) -> str:
        """Der Rueckfall seit dem Stand vorher (FallMessung.rueckfall)."""
        nli, bestaetiger = self.stand()
        if nli > vorher[0]:
            return RUECKFALL_SCHWELLE
        if bestaetiger > vorher[1]:
            return RUECKFALL_OHNE_BESTAETIGER
        return ""


class Dienste(NamedTuple):
    statement_service: "StatementService"
    specs: List["ContentTypeSearchSpec"]
    reference_service: object
    # Zaehlt Rueckfaelle in vorhandene_finden (FallMessung.rueckfall).
    zaehler: Optional[NliZaehler] = None


async def dienste_starten() -> Dienste:
    """Die Dienste wie beim Start des Semantic-Search-Service, ohne Jobs.

    Braucht die App-Datenbank (app_database_url): initialize_services legt den
    VotingService an, und der oeffnet sie (#576). Im naechtlichen Lauf ist das der
    Dienst postgres, lokal die Datenbank des Dev-Stacks.
    """
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
    # Ebenso das Modell der Polaritaet (#574), falls die NLI-Stufe aus ist.
    from services.search.polaritaet_nli import get_nli_polaritaet

    await get_nli_polaritaet().laden_abwarten()
    return Dienste(
        statement_service=get_statement_service(),
        zaehler=NliZaehler.einsetzen(get_statement_service()),
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
    ausgeschlossen: Tuple[str, ...] = ()


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
    """
    Die erwarteten Aussagen im Bestand: ihre IDs und die ihrer Beitraege. Dazu, welche
    aus erwartet und nur_mit fehlen und welche aus nur_ohne im Bestand stehen.
    """

    async def im_bestand(text: str):
        if text not in cache:
            cache[text] = await _aussage_im_bestand(dienste, text)
        return cache[text]

    aussage_ids, beitrag_ids, fehlt = set(), set(), []
    for text in fall.erwartet:
        aussage = await im_bestand(text)
        if aussage is None:
            fehlt.append(text)
            continue
        aussage_ids.add(str(aussage.id))
        beitrag_ids.update(str(r.id) for r in aussage.replysuggestions)
    fehlt += [t for t in fall.nur_mit if await im_bestand(t) is None]
    ausgeschlossen = tuple(
        [t for t in fall.nur_ohne if await im_bestand(t) is not None]
    )
    return _Erwartung(
        frozenset(aussage_ids), frozenset(beitrag_ids), tuple(fehlt), ausgeschlossen
    )


async def _erwartung_mit_ersatz(
    dienste: Dienste, fall: Fall, cache: dict
) -> Tuple[Fall, _Erwartung, Tuple[str, ...]]:
    """
    Wie _erwartung; fehlt eine Aussage aus erwartet und hat der Fall einen Ersatz, gilt
    dessen Erwartung (der Fall wird mit ihr gemessen und ausgewertet). Zurueck kommen
    der gemessene Fall, seine Erwartung und die ersetzten Aussagen (leer ohne Ersatz).
    """
    erwartung = await _erwartung(dienste, fall, cache)
    fehlt_erwartet = tuple(t for t in erwartung.fehlt if t in fall.erwartet)
    if not fehlt_erwartet or fall.ersatz is None:
        return fall, erwartung, ()
    ersetzt = fall._replace(
        erwartet=fall.ersatz.erwartet,
        dieselbe_behauptung=fall.ersatz.dieselbe_behauptung,
        phaenomen=fall.ersatz.phaenomen or fall.phaenomen,
        ersatz=None,
    )
    erwartung_ersatz = await _erwartung(dienste, ersetzt, cache)
    if erwartung_ersatz.fehlt:
        # Auch der Ersatz fehlt: Der Fall zaehlt nicht, genannt wird das Original.
        return fall, erwartung, ()
    return ersetzt, erwartung_ersatz, fehlt_erwartet


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

    fall, erwartung, ersatz_fuer = await _erwartung_mit_ersatz(
        dienste, fall, {} if cache is None else cache
    )
    if erwartung.fehlt or erwartung.ausgeschlossen:
        # Zaehlt nicht mit (gemessen()): keine Suche. Am Seed sind das die Faelle zum
        # Startbestand, im naechtlichen Lauf mehr als die Haelfte. Ohne Eintrag je
        # Schwelle, sonst stuende im JSON "keine" fuer eine Suche, die es nie gab.
        return FallMessung(
            fall,
            {},
            erwartung.fehlt,
            None,
            (),
            erwartung.ausgeschlossen,
            ersatz_fuer=ersatz_fuer,
        )
    beginn = time.perf_counter()
    aussagetreffer, polaritaet = await aussagetreffer_finden(
        dienste.statement_service, fall.anfrage
    )
    dauer_ms = (time.perf_counter() - beginn) * 1000

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
    rueckfall = ""
    if fall.dieselbe_behauptung:
        vorher = dienste.zaehler.stand() if dienste.zaehler else None
        vorhanden = await dienste.statement_service.vorhandene_finden(fall.anfrage)
        landet = vorhanden is not None and str(vorhanden.id) in erwartung.aussage_ids
        if dienste.zaehler:
            rueckfall = dienste.zaehler.rueckfall_seit(vorher)
    # Dieselbe Abfrage wie die Vorschlaege im Beitragsformular (aussageVorschlaege).
    aehnliche = await dienste.statement_service.search_filtered(
        fall.anfrage,
        AEHNLICHE_ANZAHL,
        nur_kuratiert=True,
        min_similarity=AEHNLICHE_AB,
    )
    return FallMessung(
        fall,
        angezeigt,
        erwartung.fehlt,
        landet,
        tuple(str(a.id) in erwartung.aussage_ids for a in aehnliche),
        erwartung.ausgeschlossen,
        dauer_ms,
        ersatz_fuer,
        rueckfall,
    )


KEIN_FALL_GEMESSEN = (
    "Kein Fall mit Erwartung gemessen: Der Bestand passt nicht zum Suchtestset "
    "(leere oder falsche Sammlung, oder ein Bestand ohne die Aussagen aus Seed oder "
    "Startbestand, siehe 'Nicht gemessen'). "
    "Die Zahlen oben sind nicht aussagekraeftig."
)


def bestand_passt(messungen: Iterable[FallMessung]) -> bool:
    """Mindestens ein Fall mit Erwartung ist gemessen, sonst sagen die Zahlen nichts."""
    return any(m.fall.erwartet for m in gemessen(messungen))


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
                als_json(messungen, schwellen, args.k, umgebung()),
                datei,
                ensure_ascii=False,
                indent=1,
            )
    if not bestand_passt(messungen):
        print(KEIN_FALL_GEMESSEN, file=sys.stderr)
        return BESTAND_PASST_NICHT
    return 0


def umgebung() -> dict:
    """Womit gemessen wurde, fuer den Vergleich zweier Messungen."""
    from core.config import EMBEDDING_MODELL, settings

    return {
        "gemessen_am": date.today().isoformat(),
        "modell": EMBEDDING_MODELL,
        "sammlung": settings.qdrant_collection,
        "dubletten_schwelle": settings.statement_similarity_threshold,
        "suche_polaritaet_nli": settings.suche_polaritaet_nli,
        **zuordnung_weg(settings),
    }


if __name__ == "__main__":
    sys.exit(main())
