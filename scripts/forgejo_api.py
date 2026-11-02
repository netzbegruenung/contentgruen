"""Gemeinsame Helfer der CI-Skripte fuer die Forgejo-API: scripts/ci_bericht.py und
scripts/rechtstexte_wiki.py. Nur Standardbibliothek, damit beide ohne venv laufen.

Fehler melden nur den HTTP-Status, nie den Antworttext: Forgejo gibt bei ungueltigem
Token den Token zurueck.
"""

import http.client
import json
import sys
import urllib.error
import urllib.request
from typing import Optional

ZEITLIMIT_S = 30

# OSError umfasst URLError, Zeitueberschreitung und abgerissene Verbindungen beim Lesen
# der Antwort, HTTPException etwa IncompleteRead
NETZFEHLER = (OSError, http.client.HTTPException)


def pflicht(env, name: str) -> str:
    wert = env.get(name)
    if not wert:
        raise SystemExit(f"{name} ist nicht gesetzt")
    return wert


def anfrage(
    url: str,
    token: str,
    daten: Optional[dict] = None,
    methode: Optional[str] = None,
) -> tuple[int, bytes]:
    """GET (ohne ``daten``) oder POST an die Forgejo-API, ``methode`` ueberschreibt das
    (etwa PATCH); wirft wie urlopen."""
    aufruf = urllib.request.Request(
        url,
        data=None if daten is None else json.dumps(daten).encode(),
        method=methode or ("GET" if daten is None else "POST"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(aufruf, timeout=ZEITLIMIT_S) as antwort:
        return antwort.status, antwort.read()


def fehler_melden(was: str, fehler: Exception) -> None:
    """Nur den Status melden, nie den Antworttext."""
    if isinstance(fehler, urllib.error.HTTPError):
        print(f"{was}: HTTP {fehler.code}", file=sys.stderr)
    else:
        grund = getattr(fehler, "reason", fehler)
        print(f"{was}: fehlgeschlagen ({type(grund).__name__})", file=sys.stderr)
