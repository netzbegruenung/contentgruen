"""Schreibt die Uebersicht der Rechtstext-Ablage ins Wiki des Repositorys (#503).

Die Ablage liegt als eine Datei je Eintrag (#500); die Tabellen erzeugt
scripts/rechtstexte_uebersicht.py. Eingecheckt wird die Uebersicht nicht; Menschen ohne
Python lesen sie im Wiki, Seite "Rechtstexte Übersicht". Der Workflow
.woodpecker/rechtstexte-wiki.yaml ruft das Skript nach jedem Push auf main auf. Geschrieben
wird nur, wenn sich die Tabellen geaendert haben und der Commit noch der Kopf von main ist:
Laufen zwei Merges parallel, schreibt so nur der neuere, und ein spaeter fertiger aelterer
Lauf ueberschreibt die Seite nicht mit veralteten Tabellen.

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
import urllib.parse

import rechtstexte_uebersicht as uebersicht
from forgejo_api import NETZFEHLER, anfrage, fehler_melden, pflicht

TITEL = "Rechtstexte Übersicht"


def seitenpfad(titel: str) -> str:
    """Pfad der Seite in der Wiki-API, wie Forgejo ihn aus dem Titel bildet
    (services/wiki/wiki_path.go, escapeSegToWeb): Leerzeichen werden zu "-", dann
    URL-kodiert. Ein Titel mit "-" bekaeme die Marke ".-" angehaengt; deshalb keiner."""
    if "-" in titel:
        raise ValueError(f"Titel ohne '-' waehlen: {titel}")
    return urllib.parse.quote(titel.replace(" ", "-"), safe="")


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


def main(env=os.environ) -> int:
    token = env.get("FORGEJO_TOKEN")
    if not token:
        print(
            "FORGEJO_TOKEN ist nicht gesetzt (Secret forgejo_wiki_token): "
            "Wiki-Seite nicht geschrieben.",
            file=sys.stderr,
        )
        return 1
    forge = pflicht(env, "CI_FORGE_URL").rstrip("/")
    repo = f"{pflicht(env, 'CI_REPO_OWNER')}/{pflicht(env, 'CI_REPO_NAME')}"
    commit = pflicht(env, "CI_COMMIT_SHA")
    api = f"{forge}/api/v1/repos/{repo}"
    seite = f"{api}/wiki/page/{seitenpfad(TITEL)}"
    tabellen = uebersicht.seite()

    # Nur der Lauf zum Kopf von main schreibt; ein aelterer, spaet fertiger Lauf nicht.
    try:
        _, antwort = anfrage(f"{api}/branches/main", token)
        kopf_von_main = json.loads(antwort)["commit"]["id"]
    except (*NETZFEHLER, ValueError, KeyError, TypeError) as fehler:
        fehler_melden("Kopf von main lesen", fehler)
        return 1
    if kopf_von_main != commit:
        print(f"{commit[:7]} ist nicht mehr der Kopf von main: Der neuere Lauf schreibt.")
        return 0

    # Gibt es die Seite schon, wird sie ueberschrieben, sonst angelegt.
    try:
        _, antwort = anfrage(seite, token)
        vorhanden = base64.b64decode(json.loads(antwort).get("content_base64") or "")
        methode, ziel = "PATCH", seite
    except urllib.error.HTTPError as fehler:
        if fehler.code != 404:
            fehler_melden(f"Wiki-Seite {TITEL} lesen", fehler)
            return 1
        vorhanden, methode, ziel = b"", "POST", f"{api}/wiki/new"
    except (*NETZFEHLER, ValueError) as fehler:
        fehler_melden(f"Wiki-Seite {TITEL} lesen", fehler)
        return 1
    if vorhanden.decode(errors="replace").endswith(tabellen):
        print(f"Wiki-Seite {TITEL}: Tabellen unveraendert, nichts geschrieben.")
        return 0

    inhalt = kopf(f"{forge}/{repo}/src/commit/{commit}", commit) + tabellen
    daten = {
        "title": TITEL,
        "content_base64": base64.b64encode(inhalt.encode()).decode(),
        "message": f"Rechtstexte Übersicht aus {commit[:7]}",
    }

    try:
        status, _ = anfrage(ziel, token, daten, methode)
    except NETZFEHLER as fehler:
        fehler_melden(f"Wiki-Seite {TITEL} schreiben", fehler)
        return 1
    print(f"Wiki-Seite {TITEL} ({methode}): HTTP {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
