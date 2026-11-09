#!/usr/bin/env python3
"""
Traegt das Payload-Feld antwort_ids fuer bestehende Aussagen nach und legt den
Keyword-Index an (#603). Grundlage der Rueckwaertssuche Beitrag -> Aussage auf der
Beitragsseite (utils/antwort_ids.py): Ohne Feld zeigt die Seite zu aelteren
Beitraegen keine Aussage und keine weiteren Antworten.

Erst NACH dem Ausrollen der Version laufen lassen, die das Feld schreibt - sonst
kommen in der Zwischenzeit wieder Eintraege ohne Feld dazu. Die Logik liegt im
Dienst (services/wartung/antwort_ids_nachtrag.py); das Skript laeuft deshalb
im semantic-search-Container, per stdin, mit dessen Code und Umgebung
(SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION). Gegen einen
Container mit aelterem Stand bricht es mit ModuleNotFoundError ab, ohne zu schreiben.

Auf Test/Prod liegt kein Repo-Checkout - Skript herunterladen, dann ausfuehren:

    curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/antwort_ids_nachtragen.py

    # 1. Zaehlen, was nachzutragen waere - aendert nichts
    docker exec -i gutgesagt-semantic-search python - < antwort_ids_nachtragen.py

    # 2. Nachtragen
    docker exec -i gutgesagt-semantic-search python - --ausfuehren \
        < antwort_ids_nachtragen.py

In ruhiger Zeit laufen lassen und danach einmal wiederholen: Kommt waehrend des
Laufs eine Antwort dazu, kann der erste Lauf ihr Feld mit dem alten Stand schreiben;
der zweite repariert das. Idempotent: ein zweiter Lauf mit --ausfuehren meldet
sonst nachzutragen = 0. Geschrieben
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

from services.wartung.antwort_ids_nachtrag import nachtragen  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--ausfuehren",
        action="store_true",
        help="wirklich schreiben (sonst nur zaehlen)",
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get(
        "SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection"
    )
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)

    bericht = nachtragen(client, collection, ausfuehren=args.ausfuehren)
    json.dump(vars(bericht), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
