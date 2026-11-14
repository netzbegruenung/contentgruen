"""Platzhalter, die vor einem Release-Tag ersetzt sein muessen (docs/DEPLOYMENT.md, Releases).

Die Datenschutzerklaerung und das Loeschkonzept nennen fuer Widerrufe vor dem Einspielen der
Loeschauftraege ein Datum, das erst beim Release feststeht. Bis dahin steht dort
``[Datum des Einspielens]``. Die Spec der Datenschutzerklaerung laesst Platzhalter oder Datum
zu; diese Pruefung laeuft nur bei Tags (.woodpecker/ci.yaml, Schritt release-platzhalter) und
macht den Lauf rot, solange der Platzhalter noch steht. Ohne gruenes ci baut release.yaml nichts.

Aufruf: ``python3 scripts/release_platzhalter.py`` aus der Wurzel des Repos. Nur Standardbibliothek.
"""

import pathlib
import sys

WURZEL = pathlib.Path(__file__).resolve().parents[1]

PLATZHALTER = "[Datum des Einspielens]"

DATEIEN = (
    "mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html",
    "docs/LOESCHKONZEPT.md",
)


def fundstellen(wurzel=WURZEL, dateien=DATEIEN):
    """(Datei, Zeilennummer) jeder Zeile, in der der Platzhalter noch steht."""
    treffer = []
    for datei in dateien:
        for nummer, zeile in enumerate((wurzel / datei).read_text(encoding="utf-8").splitlines(), 1):
            if PLATZHALTER in zeile:
                treffer.append((datei, nummer))
    return treffer


def main():
    treffer = fundstellen()
    for datei, nummer in treffer:
        print(f"{datei}:{nummer}: {PLATZHALTER} noch nicht ersetzt (docs/DEPLOYMENT.md, Releases)")
    if treffer:
        return 1
    print("Keine offenen Platzhalter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
