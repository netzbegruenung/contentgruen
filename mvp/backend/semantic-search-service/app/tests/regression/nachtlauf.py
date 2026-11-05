"""
Pruefung des naechtlichen Laufs (#391, .woodpecker/nacht.yaml): misst das Suchtestset
am Seed mit der Schwelle von heute und vergleicht mit dem Soll. Rot (Exit 1), wenn eine
Zahl um mehr als die Toleranz abweicht, in beide Richtungen, oder wenn Tor fuer
Roadmap-Stufe 3 bzw. untere Grenze fuer aehnliche Aussagen unterschritten sind.

    cd mvp/backend/semantic-search-service/app
    SEMANTIC_SEARCH_QDRANT_COLLECTION=nachtlauf ../venv/bin/python -m tests.regression.seed_laden
    SEMANTIC_SEARCH_QDRANT_COLLECTION=nachtlauf ../venv/bin/python -m tests.regression.nachtlauf

Erwartet genau den Seed in der Sammlung (seed_laden); gegen einen anderen Bestand ist
das Soll bedeutungslos. Regeln, Soll und Grenzen in SUCHTESTSET.md ("Nächtlicher Lauf").
"""

import argparse
import asyncio
import json
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence

from tests.regression.suche_messen import (
    BESTAND_PASST_NICHT,
    FallMessung,
    _umgebung,
    aehnliche_aussagen,
    als_json,
    auswerten,
    gemessen,
    messen,
    schwelle_heute,
    tabellen,
    zerfaserung,
)

# Exit-Code bei einer Abweichung (BESTAND_PASST_NICHT = 2 bleibt fuer "nichts gemessen").
ABWEICHUNG = 1

# Messung am Seed (mvp/data/seed/v1.0) vom 06.11.2026 mit intfloat/multilingual-e5-base
# und der Schwelle von heute, dieselben Zahlen wie in SUCHTESTSET.md (ein Unit-Test
# vergleicht). Aendert sich eine Zahl gewollt (Modell, Schwelle, Stemmer, Normalisierung,
# neue Faelle), wird sie hier und in SUCHTESTSET.md im selben PR nachgezogen.
SOLL: Dict[str, int] = {
    "gemessen": 42,
    "treffer": 29,
    "fehltreffer": 2,
    "keine": 2,
    "ohne_richtig_keine": 2,
    "ohne_fehltreffer": 7,
    "dieselbe_behauptung": 15,
    "zerfaserung_neu": 14,
    "aehnliche_erwartete_dabei": 25,
    "aehnliche_ohne_mit_vorschlag": 6,
}

# So viele Faelle darf eine Zahl vom Soll abweichen: Scores direkt an einer Schwelle
# koennen auf anderer Hardware kippen (vgl. KNAPP im Messset). Jede groessere
# Abweichung ist ein Befund, auch eine Verbesserung.
TOLERANZ_FAELLE = 1

# Tor fuer Roadmap-Stufe 3 (docs/VISION.md, "Testset vor Stellschrauben"): Mindestwerte
# bei der Schwelle von heute, unabhaengig vom Soll. Recall@10: Bei so vielen Faellen mit
# Erwartung steht eine passende Antwort unter den ersten 10. Praezision: so viel des
# Angezeigten passt. Vorlaeufig am Seed gesetzt, mit dem Startbestand neu (#568).
# Liegt unter dem Soll abzueglich Toleranz, sonst waere ein erlaubter Ausreisser rot.
TOR_STUFE_3: Dict[str, float] = {
    "recall_bei_10": 0.80,
    "praezision": 0.25,
}

# Untere Grenze fuer aehnliche Aussagen: Anteil der Faelle mit Erwartung, bei denen eine
# erwartete Aussage unter den aehnlichen Aussagen ist (AEHNLICHE_ANZAHL ab AEHNLICHE_AB
# in suche_messen.py, wie im Beitragsformular). Vorlaeufig am Seed gesetzt (#568).
UNTERE_GRENZE_AEHNLICHE = 0.70


class Pruefung(NamedTuple):
    name: str
    soll: str
    gemessen: str
    ok: bool
    grund: str = ""


def _gegen_soll(name: str, schluessel: str, wert: int, nenner: str = "") -> Pruefung:
    soll = SOLL[schluessel]
    abweichung = wert - soll
    ok = abs(abweichung) <= TOLERANZ_FAELLE
    grund = ""
    if not ok:
        richtung = "mehr" if abweichung > 0 else "weniger"
        grund = (
            f"{abs(abweichung)} {richtung} als das Soll; gewollt, dann SOLL in "
            "tests/regression/nachtlauf.py und SUCHTESTSET.md nachziehen"
        )
    return Pruefung(
        name,
        f"{soll}{nenner} ±{TOLERANZ_FAELLE}",
        f"{wert}{nenner}",
        ok,
        grund,
    )


def _mindestens(name: str, wert: Optional[float], grenze: float) -> Pruefung:
    ok = wert is not None and wert >= grenze
    return Pruefung(
        name,
        f"≥ {grenze:.2f}",
        "–" if wert is None else f"{wert:.2f}",
        ok,
        "" if ok else "unter der Grenze",
    )


def pruefen(messungen: Sequence[FallMessung], schwelle: float) -> List[Pruefung]:
    a = auswerten(messungen, schwelle)
    z = zerfaserung(messungen, schwelle)
    aehnlich = aehnliche_aussagen(messungen)
    mit = f"/{a.mit_erwartung}"
    anteil_aehnlich = (
        aehnlich.erwartete_dabei / aehnlich.mit_erwartung
        if aehnlich.mit_erwartung
        else None
    )
    return [
        Pruefung(
            "gemessene Fälle",
            str(SOLL["gemessen"]),
            str(len(gemessen(messungen))),
            len(gemessen(messungen)) == SOLL["gemessen"],
            "Seed oder Suchtestset passen nicht zum Soll",
        ),
        _gegen_soll("Treffer", "treffer", a.treffer, mit),
        _gegen_soll("Fehltreffer", "fehltreffer", a.fehltreffer),
        _gegen_soll("keine", "keine", a.keine),
        _gegen_soll(
            "ohne Erwartung: keine", "ohne_richtig_keine", a.ohne_richtig_keine
        ),
        _gegen_soll(
            "ohne Erwartung: Fehltreffer", "ohne_fehltreffer", a.ohne_fehltreffer
        ),
        _gegen_soll(
            "Zerfaserung",
            "zerfaserung_neu",
            z.davon_neu,
            f"/{z.dieselbe_behauptung}",
        ),
        _gegen_soll(
            "Ähnliche Aussagen: erwartete dabei",
            "aehnliche_erwartete_dabei",
            aehnlich.erwartete_dabei,
            f"/{aehnlich.mit_erwartung}",
        ),
        _gegen_soll(
            "Ähnliche Aussagen: ohne Erwartung gezeigt",
            "aehnliche_ohne_mit_vorschlag",
            aehnlich.ohne_mit_vorschlag,
            f"/{aehnlich.ohne_erwartung}",
        ),
        _mindestens(
            "Tor Roadmap-Stufe 3: Recall@10",
            a.recall_bei.get(10),
            TOR_STUFE_3["recall_bei_10"],
        ),
        _mindestens(
            "Tor Roadmap-Stufe 3: Präzision",
            a.praezision,
            TOR_STUFE_3["praezision"],
        ),
        _mindestens(
            "Untere Grenze ähnliche Aussagen",
            anteil_aehnlich,
            UNTERE_GRENZE_AEHNLICHE,
        ),
    ]


def bericht(pruefungen: Sequence[Pruefung]) -> str:
    zeilen = [
        "| Prüfung | Soll | gemessen | Ergebnis |",
        "|---|---|---|---|",
    ]
    for p in pruefungen:
        ergebnis = "ok" if p.ok else f"ROT: {p.grund}"
        zeilen.append(f"| {p.name} | {p.soll} | {p.gemessen} | {ergebnis} |")
    return "\n".join(zeilen)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", metavar="PFAD", help="Messung als JSON schreiben")
    args = parser.parse_args(argv)

    from core.logging import LoggingConfig, initialize_logging

    initialize_logging(LoggingConfig(level="WARNING", enable_console_utf8=False))
    schwelle = schwelle_heute()
    messungen = asyncio.run(messen((schwelle,)))

    print(tabellen(messungen, (schwelle,), schwelle))
    print()
    pruefungen = pruefen(messungen, schwelle)
    print(f"Nächtlicher Lauf, Schwelle {schwelle}, Toleranz ±{TOLERANZ_FAELLE} Fall:")
    print()
    print(bericht(pruefungen))
    if args.json:
        daten = als_json(messungen, (schwelle,), umgebung=_umgebung())
        daten["pruefungen"] = [p._asdict() for p in pruefungen]
        with open(args.json, "w", encoding="utf-8") as datei:
            json.dump(daten, datei, ensure_ascii=False, indent=1)

    if not any(m.fall.erwartet for m in gemessen(messungen)):
        print("Kein Fall mit Erwartung gemessen: Seed geladen?", file=sys.stderr)
        return BESTAND_PASST_NICHT
    return 0 if all(p.ok for p in pruefungen) else ABWEICHUNG


if __name__ == "__main__":
    sys.exit(main())
