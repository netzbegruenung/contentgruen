#!/usr/bin/env python3
"""
Einmal-Skript: hebt bestehende Inhalte von PENDING_REVIEW auf NEW_CONTENT_STATUS.

Hintergrund: Neue Inhalte wurden mit PENDING_REVIEW angelegt, und die Suche
filtert genau diesen Status heraus (base_repository.search). Selbst eingestellte
Beitraege waren dadurch nie auffindbar. Der Anlage-Status haengt jetzt an
NEW_CONTENT_STATUS (domain/models/content_status.py); die bereits gespeicherten
Punkte muessen einmalig nachgezogen werden.

Kein Migrations-Framework, kein Rollback, keine Idempotenz-Logik - das Skript
laeuft einmal. Es spricht die Qdrant-REST-API direkt an, wie die uebrigen
Skripte in diesem Verzeichnis nur mit `requests`.

    python mvp/scripts/manual/promote_pending_review_content.py
    python mvp/scripts/manual/promote_pending_review_content.py --delete-orphans

Ohne --delete-orphans werden verwaiste Referenzen nur aufgelistet. Loeschen ist
nicht umkehrbar, deshalb muss es ausdruecklich verlangt werden.
"""

import argparse
import sys

import requests

QDRANT_URL = "http://localhost:6333"
COLLECTION = "content_collection"

OLD_STATUS = "pending_review"
NEW_STATUS = "released_internal"

SCROLL_PAGE = 256


def _post(path: str, payload: dict) -> dict:
    response = requests.post(f"{QDRANT_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def _scroll_all(scroll_filter: dict | None) -> list[dict]:
    """Alle Punkte samt Payload holen; Qdrant paginiert ueber next_page_offset."""
    points: list[dict] = []
    offset = None

    while True:
        body = {
            "limit": SCROLL_PAGE,
            "with_payload": True,
            "with_vector": False,
        }
        if scroll_filter is not None:
            body["filter"] = scroll_filter
        if offset is not None:
            body["offset"] = offset

        result = _post(f"/collections/{COLLECTION}/points/scroll", body)["result"]
        points.extend(result["points"])

        offset = result.get("next_page_offset")
        if offset is None:
            return points


def promote_pending_review() -> int:
    """Setzt den Status aller PENDING_REVIEW-Punkte auf den sichtbaren Status."""
    status_filter = {"must": [{"key": "status", "match": {"value": OLD_STATUS}}]}

    pending = _scroll_all(status_filter)
    if not pending:
        print(f"Keine Punkte mit status={OLD_STATUS} gefunden.")
        return 0

    by_type: dict[str, int] = {}
    for point in pending:
        content_type = point["payload"].get("content_type", "(ohne content_type)")
        by_type[content_type] = by_type.get(content_type, 0) + 1

    print(f"{len(pending)} Punkte mit status={OLD_STATUS}:")
    for content_type, count in sorted(by_type.items()):
        print(f"  {content_type}: {count}")

    _post(
        f"/collections/{COLLECTION}/points/payload?wait=true",
        {"payload": {"status": NEW_STATUS}, "filter": status_filter},
    )

    verbleibend = _scroll_all(status_filter)
    print(f"Auf status={NEW_STATUS} gehoben. Verbleibend: {len(verbleibend)}")
    return len(pending)


def find_orphaned_references() -> list[str]:
    """
    Referenzen, auf die kein Inhalt zeigt.

    Sie entstehen, weil das Frontend beim Setzen eines Chips per
    POST /reference/add bereits eine Referenz anlegt, das Backend beim
    Speichern des Beitrags aber ueber den Referenz-String neu aufloest.
    Verknuepft wird nur die vom Backend angelegte Referenz.
    """
    alle_punkte = _scroll_all(None)

    referenz_ids: set[str] = set()
    verwendete_ids: set[str] = set()

    for point in alle_punkte:
        payload = point["payload"]
        if payload.get("content_type") == "reference":
            referenz_ids.add(str(point["id"]))

        for referenz in payload.get("references") or []:
            reference_id = referenz.get("reference_id")
            if reference_id:
                verwendete_ids.add(str(reference_id))

    return sorted(referenz_ids - verwendete_ids)


def delete_points(point_ids: list[str]) -> None:
    _post(
        f"/collections/{COLLECTION}/points/delete?wait=true",
        {"points": point_ids},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help="Verwaiste Referenzen loeschen statt sie nur aufzulisten.",
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

    print("=== Status anheben ===")
    promote_pending_review()

    print("\n=== Verwaiste Referenzen ===")
    orphans = find_orphaned_references()
    if not orphans:
        print("Keine verwaisten Referenzen gefunden.")
        return 0

    print(f"{len(orphans)} Referenzen, auf die kein Inhalt zeigt:")
    for reference_id in orphans:
        print(f"  {reference_id}")

    if not args.delete_orphans:
        print(
            "\nNicht geloescht. Mit --delete-orphans wiederholen, um sie zu entfernen."
        )
        return 0

    delete_points(orphans)
    print(f"\n{len(orphans)} verwaiste Referenzen geloescht.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
