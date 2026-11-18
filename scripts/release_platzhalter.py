"""Platzhalter und Stand-Daten, die vor einem Release-Tag stimmen muessen.

Beschrieben in docs/CI.md, "Placeholders before a release".

Die Datenschutzerklaerung und das Loeschkonzept nennen fuer Widerrufe vor dem Einspielen der
Loeschauftraege ein Datum, das erst beim Release feststeht. Bis dahin steht dort
``[Datum des Einspielens]``. Die Spec der Datenschutzerklaerung laesst Platzhalter oder Datum
zu; diese Pruefung laeuft nur bei Tags (.woodpecker/ci.yaml, Schritt release-platzhalter) und
macht den Lauf rot, solange der Platzhalter noch steht. Ohne gruenes ci baut release.yaml nichts.

Zweite Pruefung: Bei den Tags in STICHTAG_TAGS, also bei Releases, deren Pull Request die Daten
der Rechtstexte auf den Produktionstag setzt, darf keines dieser Daten (STICHTAG_MUSTER: Stand der
Datenschutzerklaerung, "Wer vor dem ...") vor dem Tag des Tag-Laufs liegen. Sonst nennt die
Erklaerung einen Tag, an dem noch nichts eingespielt war (v0.9.0: Datum fuer den 17.11. gesetzt,
Produktion erst am 18.11.). Spaetere Releases pruefen die Daten nicht, sie bleiben Geschichte.

Aufruf aus der Wurzel des Repos: ``python3 scripts/release_platzhalter.py`` (Tag aus
CI_COMMIT_TAG); lokal ``--tag v0.9.0 [--stichtag 2026-11-18]``, ohne --stichtag gilt heute.
Nur Standardbibliothek.
"""

import argparse
import datetime
import os
import pathlib
import re
import sys

WURZEL = pathlib.Path(__file__).resolve().parents[1]

PLATZHALTER = "[Datum des Einspielens]"

DATEIEN = (
    "mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html",
    "docs/LOESCHKONZEPT.md",
)

# Tags, deren Release-PR die Daten der Rechtstexte auf den Produktionstag setzt; ein solcher
# Release-PR traegt seinen Tag hier ein.
STICHTAG_TAGS = ("v0.9.0",)

MONATE = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)
_DATUM = r"(\d{1,2})\. (" + "|".join(MONATE) + r") (\d{4})"

STICHTAG_MUSTER = (
    re.compile(r"<strong>Stand:</strong> " + _DATUM),
    re.compile(r"Wer vor dem " + _DATUM),
)


def fundstellen(wurzel=WURZEL, dateien=DATEIEN):
    """(Datei, Zeilennummer) jeder Zeile, in der der Platzhalter noch steht."""
    treffer = []
    for datei in dateien:
        for nummer, zeile in enumerate((wurzel / datei).read_text(encoding="utf-8").splitlines(), 1):
            if PLATZHALTER in zeile:
                treffer.append((datei, nummer))
    return treffer


def stand_daten(wurzel=WURZEL, dateien=DATEIEN):
    """(Datei, Zeilennummer, Datum) jedes Datums nach STICHTAG_MUSTER."""
    daten = []
    for datei in dateien:
        for nummer, zeile in enumerate((wurzel / datei).read_text(encoding="utf-8").splitlines(), 1):
            for muster in STICHTAG_MUSTER:
                for tag, monat, jahr in muster.findall(zeile):
                    datum = datetime.date(int(jahr), MONATE.index(monat) + 1, int(tag))
                    daten.append((datei, nummer, datum))
    return daten


def zu_frueh(stichtag, wurzel=WURZEL, dateien=DATEIEN):
    """Meldungen fuer Daten vor dem Stichtag und fuer Dateien ganz ohne Datum."""
    daten = stand_daten(wurzel, dateien)
    meldungen = [
        f"{datei}:{nummer}: {datum:%d.%m.%Y} liegt vor dem Tag-Lauf am {stichtag:%d.%m.%Y}"
        for datei, nummer, datum in daten
        if datum < stichtag
    ]
    mit_datum = {datei for datei, _, _ in daten}
    meldungen += [f"{datei}: kein Stand-Datum gefunden" for datei in dateien if datei not in mit_datum]
    return meldungen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=os.environ.get("CI_COMMIT_TAG", ""))
    parser.add_argument("--stichtag", type=datetime.date.fromisoformat, default=None)
    args = parser.parse_args(argv)

    fehler = [
        f"{datei}:{nummer}: {PLATZHALTER} noch nicht ersetzt (docs/CI.md, Placeholders before a release)"
        for datei, nummer in fundstellen()
    ]
    if args.tag in STICHTAG_TAGS:
        fehler += zu_frueh(args.stichtag or datetime.date.today())
    for zeile in fehler:
        print(zeile)
    if fehler:
        return 1
    print("Keine offenen Platzhalter, Stand-Daten passen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
