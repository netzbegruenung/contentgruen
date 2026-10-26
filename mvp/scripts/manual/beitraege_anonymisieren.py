#!/usr/bin/env python3
"""
Anonymisiert die Beitraege einer Person in Qdrant (Loeschkonzept Schritt 3).

Ablauf und Reihenfolge: docs/LOESCHKONZEPT.md. Die Kennung wird in allen vier
Feldern durch den Platzhalter ehemalige-person ersetzt; Karten zeigen dazu
"ehemalige Person".

Einmalig auch fuer den Bestand: Mit der Kennung geloeschter-nutzer stellt es
Beitraege um, die vor dem neuen Platzhalter anonymisiert wurden.

Die Logik liegt im Dienst (services/wartung/beitraege_anonymisieren.py); das Skript
laeuft deshalb im semantic-search-Container, per stdin, mit dessen Code und Umgebung
(SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION). Gegen einen
Container mit aelterem Stand bricht es mit ModuleNotFoundError ab, ohne zu schreiben.

Auf Test/Prod liegt kein Repo-Checkout - Skript herunterladen, dann ausfuehren:

    curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/beitraege_anonymisieren.py

    # 1. Treffer zeigen - aendert nichts
    docker exec -i gutgesagt-semantic-search python - "$KENNUNG" \
        < beitraege_anonymisieren.py

    # 2. Anonymisieren
    docker exec -i gutgesagt-semantic-search python - "$KENNUNG" --ausfuehren \
        < beitraege_anonymisieren.py

Ausgabe: je Treffer ID, Typ und Textanfang - fuer die Einzelfallpruefung, ob ein
Text die Person selbst erkennbar macht -, zuletzt die Anzahl. Wiederholbar: ein
zweiter Lauf findet nichts mehr.
"""

import argparse
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402

from services.wartung.beitraege_anonymisieren import (  # noqa: E402
    ALTER_PLATZHALTER,
    anonymisieren,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("kennung", help=f"X-User-Kennung der Person (oder {ALTER_PLATZHALTER})")
    parser.add_argument(
        "--ausfuehren", action="store_true", help="wirklich schreiben (sonst nur zeigen)"
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection")
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)

    bericht = anonymisieren(client, collection, args.kennung, ausfuehren=args.ausfuehren)
    for punkt in bericht.treffer:
        print(punkt.id, punkt.content_type, repr(punkt.text)[:80])
    wort = "anonymisiert" if bericht.ausgefuehrt else "zu anonymisieren"
    print(f"{wort}: {len(bericht.treffer)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
