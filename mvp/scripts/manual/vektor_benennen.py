#!/usr/bin/env python3
"""
Fuehrt den Vektor der Collection als benannten Vektor (Named Vector, #395).

Kopiert alle Punkte samt Vektoren in eine neue Collection mit dem benannten Vektor
und macht den alten Namen zum Alias darauf; nichts wird neu eingebettet. Die Logik
liegt im Dienst (services/wartung/vektor_benennen.py); das Skript laeuft deshalb im
semantic-search-Container, per stdin, mit dessen Code und Umgebung
(SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION). Gegen einen
Container mit aelterem Stand bricht es mit ModuleNotFoundError ab, ohne zu schreiben.

Vorher ein Backup ziehen (mvp/scripts/backup/backup.sh). Auf Test/Prod liegt kein
Repo-Checkout - Skript herunterladen, dann ausfuehren:

    curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/vektor_benennen.py

    # 1. Zaehlen - aendert nichts
    docker exec -i gutgesagt-semantic-search python - < vektor_benennen.py

    # 2. Umstellen, danach den Dienst neu starten
    docker exec -i gutgesagt-semantic-search python - --ausfuehren < vektor_benennen.py
    docker restart gutgesagt-semantic-search

Idempotent: ein zweiter Lauf meldet "vorher": "benannt" und aendert nichts. Die
Ausgabe enthaelt nur Zaehler und Collection-Namen, keine Texte und keine IDs.
"""

import argparse
import json
import os
import sys

# Beim Lauf per stdin ist das Arbeitsverzeichnis des Containers (/app) der Paketstamm.
sys.path.insert(0, os.getcwd())

from qdrant_client import QdrantClient  # noqa: E402

from services.wartung.vektor_benennen import benennen  # noqa: E402

NEUSTART = (
    "Umgestellt. Jetzt den Dienst neu starten, sonst sucht er weiter ohne "
    "Vektornamen: docker restart gutgesagt-semantic-search"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren", action="store_true", help="wirklich umstellen (sonst nur zaehlen)"
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection")
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)

    bericht = benennen(client, collection, ausfuehren=args.ausfuehren)
    json.dump(vars(bericht), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    if bericht.kopiert:
        print(NEUSTART)
    return 0


if __name__ == "__main__":
    sys.exit(main())
