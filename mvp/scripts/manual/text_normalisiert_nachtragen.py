#!/usr/bin/env python3
"""
Traegt das Payload-Feld text_normalisiert fuer bestehende Aussagen und Kommentare
nach und legt den Keyword-Index an. Grundlage des exakten Textabgleichs in der
Dublettenpruefung (utils/text_normalisierung.py).

Erst NACH dem Ausrollen der Version laufen lassen, die das Feld schreibt - sonst
kommen in der Zwischenzeit wieder Eintraege ohne Feld dazu. Die Logik liegt im
Dienst (services/wartung/text_normalisiert_nachtrag.py); das Skript laeuft deshalb
im semantic-search-Container, per stdin, mit dessen Umgebung
(SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION).

    # 1. Zaehlen, was nachzutragen waere - aendert nichts
    docker exec -i contentgruen-semantic-search python - \
        < mvp/scripts/manual/text_normalisiert_nachtragen.py

    # 2. Nachtragen
    docker exec -i contentgruen-semantic-search python - --ausfuehren \
        < mvp/scripts/manual/text_normalisiert_nachtragen.py

Idempotent: ein zweiter Lauf mit --ausfuehren meldet nachzutragen = 0. Geschrieben
wird mit set_payload nur dieses eine Feld. Die Ausgabe enthaelt nur Zaehler, keine
Texte und keine IDs.
"""

import argparse
import json
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402

from services.wartung.text_normalisiert_nachtrag import nachtragen  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren", action="store_true", help="wirklich schreiben (sonst nur zaehlen)"
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection")
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)

    bericht = nachtragen(client, collection, ausfuehren=args.ausfuehren)
    json.dump(vars(bericht), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
