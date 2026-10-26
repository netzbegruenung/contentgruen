#!/usr/bin/env python3
"""
Stellt bestehende Beitraege in Qdrant auf die Zustaende sichtbar, gesperrt,
geloescht um und entfernt das Feld visibility (#214).

Die Logik liegt im Dienst (services/wartung/zustaende_umstellen.py); das Skript
laeuft deshalb im semantic-search-Container, per stdin, mit dessen Code und Umgebung
(SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION). Gegen einen
Container mit aelterem Stand bricht es mit ModuleNotFoundError ab, ohne zu schreiben.

Erst nach dem Ausrollen der Version laufen lassen, die die neuen Zustaende kennt, und
vorher einen Qdrant-Snapshot ziehen (docs/DEPLOYMENT.md). Auf Test/Prod liegt kein
Repo-Checkout - Skript herunterladen, dann ausfuehren:

    curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/zustaende_umstellen.py

    # 1. Zaehlen - aendert nichts
    docker exec -i gutgesagt-semantic-search python - < zustaende_umstellen.py

    # 2. Umstellen
    docker exec -i gutgesagt-semantic-search python - --ausfuehren \\
        < zustaende_umstellen.py

Ausgabe: Punkte je bisherigem Status, die umgestellten status_vor_sperre, die
entfernten visibility-Felder und unbekannte Status (bleiben stehen). Wiederholbar:
ein zweiter Lauf findet nichts mehr.
"""

import argparse
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402

from services.wartung.zustaende_umstellen import zustaende_umstellen  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren", action="store_true", help="wirklich schreiben (sonst nur zaehlen)"
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection")
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)

    bericht = zustaende_umstellen(client, collection, ausfuehren=args.ausfuehren)
    for status, anzahl in sorted(bericht.status.items()):
        print(f"status {status}: {anzahl}")
    print(f"status_vor_sperre umzustellen: {bericht.status_vor_sperre_umgestellt}")
    print(f"visibility zu entfernen: {bericht.visibility_entfernt}")
    for status, anzahl in sorted(bericht.unbekannt.items()):
        print(f"UNBEKANNT, bleibt stehen: {status}: {anzahl}")
    wort = "umgestellt" if bericht.ausgefuehrt else "umzustellen"
    print(f"{wort}: {bericht.zu_aendern}")
    return 1 if bericht.unbekannt else 0


if __name__ == "__main__":
    sys.exit(main())
