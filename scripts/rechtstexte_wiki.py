"""Schreibt die Uebersicht der Rechtstext-Ablage ins Wiki des Repositorys (#503).

Die Ablage liegt als eine Datei je Eintrag (#500); die Tabellen erzeugt
scripts/rechtstexte_uebersicht.py. Eingecheckt wird die Uebersicht nicht, damit lesen sie
Menschen ohne Python im Wiki, Seite Rechtstexte-Uebersicht. Der Workflow
.woodpecker/rechtstexte-wiki.yaml ruft das Skript nach jedem Merge auf main auf, der die
Ablage beruehrt; jeder Lauf ueberschreibt die ganze Seite.

Nur Standardbibliothek: der Schritt laeuft ohne venv.

Aufruf: python3 scripts/rechtstexte_wiki.py
Umgebung: CI_FORGE_URL, CI_REPO_OWNER, CI_REPO_NAME, CI_COMMIT_SHA (setzt Woodpecker),
FORGEJO_TOKEN (Secret forgejo_wiki_token).
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

import rechtstexte_uebersicht as uebersicht
from ci_bericht import _NETZFEHLER, ZEITLIMIT_S, _fehler_melden, _pflicht

TITEL = "Rechtstexte-Uebersicht"


def kopf(quelle: str, commit: str) -> str:
    """Hinweis oben auf der Seite: woher sie kommt und wo man sie aendert."""
    return (
        "Erzeugt aus der Ablage auf main, Commit "
        f"[{commit[:7]}]({quelle}), mit `scripts/rechtstexte_uebersicht.py seite`. "
        "**Nicht hier bearbeiten:** Der nächste Merge überschreibt die Seite. "
        "Einträge ändert ein Pull Request an der Datei des Eintrags in "
        f"[docs/rechtstexte-luecken/]({quelle}/docs/rechtstexte-luecken) bzw. "
        f"[docs/nutzungsbedingungen-staende/]({quelle}/docs/nutzungsbedingungen-staende); "
        "dort steht auch, wie die Ablage aufgebaut ist.\n\n"
    )


def _anfrage(
    methode: str, url: str, token: str, daten: Optional[dict] = None
) -> int:
    anfrage = urllib.request.Request(
        url,
        data=None if daten is None else json.dumps(daten).encode(),
        method=methode,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT_S) as antwort:
        return antwort.status


def main(env=os.environ) -> int:
    token = env.get("FORGEJO_TOKEN")
    if not token:
        print(
            "FORGEJO_TOKEN ist nicht gesetzt (Secret forgejo_wiki_token): "
            "Wiki-Seite nicht geschrieben.",
            file=sys.stderr,
        )
        return 1
    forge = _pflicht(env, "CI_FORGE_URL").rstrip("/")
    repo = f"{_pflicht(env, 'CI_REPO_OWNER')}/{_pflicht(env, 'CI_REPO_NAME')}"
    commit = _pflicht(env, "CI_COMMIT_SHA")
    api = f"{forge}/api/v1/repos/{repo}/wiki"
    inhalt = kopf(f"{forge}/{repo}/src/commit/{commit}", commit) + uebersicht.seite()
    daten = {
        "title": TITEL,
        "content_base64": base64.b64encode(inhalt.encode()).decode(),
        "message": f"Rechtstexte-Übersicht aus {commit[:7]}",
    }

    # Gibt es die Seite schon, wird sie ueberschrieben, sonst angelegt.
    try:
        _anfrage("GET", f"{api}/page/{TITEL}", token)
        methode, ziel = "PATCH", f"{api}/page/{TITEL}"
    except urllib.error.HTTPError as fehler:
        if fehler.code != 404:
            _fehler_melden(f"Wiki-Seite {TITEL} lesen", fehler)
            return 1
        methode, ziel = "POST", f"{api}/new"
    except _NETZFEHLER as fehler:
        _fehler_melden(f"Wiki-Seite {TITEL} lesen", fehler)
        return 1

    try:
        status = _anfrage(methode, ziel, token, daten)
    except _NETZFEHLER as fehler:
        _fehler_melden(f"Wiki-Seite {TITEL} schreiben", fehler)
        return 1
    print(f"Wiki-Seite {TITEL} ({methode}): HTTP {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
