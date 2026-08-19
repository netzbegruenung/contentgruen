#!/usr/bin/env python3
"""
Einmal-Skript: stellt bestehende Suchanfrage-Statements auf SEARCH_QUERY um
und loest den Personenbezug.

Hintergrund: Suchanfragen landen als Statement im Index - das bleibt so, es ist
das Rohmaterial dafuer, wonach gesucht wird und wo Inhalt fehlt. Bis jetzt waren
sie aber mit origin=manually_created und der suchenden Person als Autor
gespeichert, also weder vom kuratierten Material zu unterscheiden noch frei von
Personenbezug. Neu angelegte Statements aus der Suche tragen
origin=search_query und SEARCH_QUERY_AUTHOR (domain/models/content_origin.py);
der Altbestand muss einmalig nachgezogen werden.

    origin            -> search_query
    original_author   -> system:suchanfrage
    last_modified_by  -> system:suchanfrage
    authors           -> [{"name": "system:suchanfrage", "role": null}]

ERKENNUNGSKRITERIUM - bitte vor dem Lauf lesen:

Es gibt kein Feld, an dem sich eine Suchanfrage sicher von einem von Hand
angelegten Statement unterscheiden laesst. Beide Wege haben bisher
origin=manually_created geschrieben, beide tragen einen echten Benutzernamen.
Das Skript kann daher nur eine Kandidatenmenge bilden:

    content_type=statement
    origin=manually_created            (schliesst das Seeding aus, initial_data)
    replysuggestions_count=0           (schliesst alles Beantwortete aus)

Diese Menge enthaelt neben Suchanfragen auch abgebrochene Beitragsversuche: das
Eingabefeld "Aussage" in den Formularen legt schon waehrend des Tippens ein
Statement an (debounced), und wer danach abbricht, hinterlaesst ebenfalls ein
unbeantwortetes Statement. Ein echtes, absichtlich angelegtes und noch
unbeantwortetes Statement steckt genauso darin.

Deshalb schreibt das Skript nichts ohne ausdrueckliche Freigabe:

    # 1. Ansehen, was in Frage kaeme - aendert nichts
    python mvp/scripts/manual/relabel_search_query_statements.py

    # 2. Auf Dev, wo die Kandidatenmenge nachweislich nur Suchanfragen enthaelt
    python mvp/scripts/manual/relabel_search_query_statements.py --apply

    # 3. Auf Test: erst die Liste durchgehen, dann gezielt die IDs uebergeben
    python mvp/scripts/manual/relabel_search_query_statements.py \
        --apply --only-ids 33e65c43-... fa7ce8a7-...

Auf Test ist --only-ids der vorgesehene Weg. Suchanfragen lesen sich wie
Stichworte ("Klimaschutz", "Landwirtschaft Status Quo Insekten"), kuratierte
Aussagen wie Behauptungen ("Die Gruenen sind eine Verbotspartei!") - diese
Unterscheidung trifft ein Mensch, nicht das Skript.

Bereits beantwortete Statements bleiben ausdruecklich unberuehrt, auch wenn sie
urspruenglich aus einer Suche stammen: an ihnen haengt inzwischen kuratierter
Inhalt, und ein Fehlgriff waere dort teurer als der verbliebene Personenbezug.

Kein Migrations-Framework, kein Rollback. Es spricht die Qdrant-REST-API direkt
an, wie die uebrigen Skripte in diesem Verzeichnis nur mit `requests`.
"""

import argparse
import sys

import requests

QDRANT_URL = "http://localhost:6333"
COLLECTION = "content_collection"

SCROLL_PAGE = 256

ALTE_HERKUNFT = "manually_created"
NEUE_HERKUNFT = "search_query"
SYSTEM_AUTOR = "system:suchanfrage"

KANDIDATEN_FILTER = {
    "must": [
        {"key": "content_type", "match": {"value": "statement"}},
        {"key": "origin", "match": {"value": ALTE_HERKUNFT}},
        {"key": "replysuggestions_count", "match": {"value": 0}},
    ]
}


def _post(path: str, payload: dict) -> dict:
    response = requests.post(f"{QDRANT_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def _scroll_all(scroll_filter: dict) -> list[dict]:
    """Alle passenden Punkte samt Payload holen; Qdrant paginiert ueber next_page_offset."""
    points: list[dict] = []
    offset = None

    while True:
        body = {
            "limit": SCROLL_PAGE,
            "with_payload": True,
            "with_vector": False,
            "filter": scroll_filter,
        }
        if offset is not None:
            body["offset"] = offset

        result = _post(f"/collections/{COLLECTION}/points/scroll", body)["result"]
        points.extend(result["points"])

        offset = result.get("next_page_offset")
        if offset is None:
            return points


def kandidaten(nur_ids: list[str] | None) -> list[dict]:
    gefunden = _scroll_all(KANDIDATEN_FILTER)
    if nur_ids is None:
        return gefunden

    gewuenscht = set(nur_ids)
    passend = [p for p in gefunden if str(p["id"]) in gewuenscht]

    unbekannt = gewuenscht - {str(p["id"]) for p in passend}
    if unbekannt:
        print(
            "Diese IDs stehen nicht in der Kandidatenmenge und werden "
            "uebergangen:",
            file=sys.stderr,
        )
        for punkt_id in sorted(unbekannt):
            print(f"  {punkt_id}", file=sys.stderr)

    return passend


def auflisten(punkte: list[dict]) -> None:
    print(f"{len(punkte)} Statement(s) in der Kandidatenmenge:\n")
    for punkt in punkte:
        payload = punkt["payload"]
        print(f"  {punkt['id']}")
        print(f"    Text:      {payload.get('text', '')}")
        print(f"    Autor:     {payload.get('original_author')}")
        print(f"    Angelegt:  {payload.get('created')}")
        print()


def umstellen(punkte: list[dict]) -> None:
    """Herkunft und Autor setzen - punktweise, damit --only-ids greifen kann."""
    _post(
        f"/collections/{COLLECTION}/points/payload?wait=true",
        {
            "payload": {
                "origin": NEUE_HERKUNFT,
                "original_author": SYSTEM_AUTOR,
                "last_modified_by": SYSTEM_AUTOR,
                "authors": [{"name": SYSTEM_AUTOR, "role": None}],
            },
            "points": [punkt["id"] for punkt in punkte],
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Tatsaechlich schreiben. Ohne diese Angabe wird nur aufgelistet.",
    )
    parser.add_argument(
        "--only-ids",
        nargs="+",
        metavar="ID",
        help=(
            "Nur diese Punkt-IDs umstellen, statt der ganzen Kandidatenmenge. "
            "Auf Test der vorgesehene Weg."
        ),
    )
    args = parser.parse_args()

    try:
        requests.get(
            f"{QDRANT_URL}/collections/{COLLECTION}", timeout=10
        ).raise_for_status()
    except requests.RequestException as e:
        print(f"Qdrant unter {QDRANT_URL} nicht erreichbar: {e}", file=sys.stderr)
        print("Erst die Dienste starten (mvp/run-local.sh up).", file=sys.stderr)
        return 1

    punkte = kandidaten(args.only_ids)
    if not punkte:
        print("Nichts umzustellen.")
        return 0

    auflisten(punkte)

    if not args.apply:
        print(
            "Nichts geaendert. Die Liste enthaelt neben Suchanfragen auch\n"
            "abgebrochene Beitragsversuche und echte unbeantwortete Aussagen -\n"
            "bitte durchgehen und mit --apply (Dev) oder --apply --only-ids\n"
            "(Test) wiederholen."
        )
        return 0

    umstellen(punkte)

    verbleibend = _scroll_all(KANDIDATEN_FILTER)
    print(
        f"{len(punkte)} Statement(s) auf origin={NEUE_HERKUNFT} umgestellt und "
        f"vom Autor geloest.\n"
        f"Verbleibende Kandidaten: {len(verbleibend)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
