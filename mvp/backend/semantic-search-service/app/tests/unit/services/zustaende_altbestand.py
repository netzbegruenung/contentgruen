"""
Altbestand fuer die Tests der Umstellung auf die Zustaende sichtbar, gesperrt,
geloescht (#214): test_zustaende_umstellen.py und test_zustaende_umstellen_skript.py.
"""

import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION = f"test_zustaende_{uuid.uuid4().hex[:8]}"

# Punkt-ID -> Payload vor der Migration.
BESTAND = {
    1: {"status": "released_internal", "visibility": "internal"},
    2: {"status": "approved", "visibility": None},
    3: {"status": "published_external"},
    4: {"status": "draft"},
    5: {"status": "pending_review"},
    6: {"status": "archived"},
    7: {"status": "duplicate"},
    8: {"status": "rejected"},
    9: {"status": "flagged"},
    10: {},  # Altbestand ohne Status
    11: {"status": "blocked", "status_vor_sperre": "released_internal"},
    12: {"status": "blocked", "status_vor_sperre": None},
    13: {"status": "blocked"},
    14: {"status": "pending_description", "visibility": "visible"},
    15: {"status": "description_failed"},
    16: {"status": "visible"},
    17: {"status": "voellig_unbekannt"},
    18: {"status": "blocked", "status_vor_sperre": "pending_description"},
    19: {"status": "blocked", "status_vor_sperre": "voellig_unbekannt"},
}


def punkte_anlegen(client):
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(
                id=i,
                vector=[1.0, 0.0],
                payload={"content_type": "commentary", "text": f"Kommentar {i}", **p},
            )
            for i, p in BESTAND.items()
        ],
    )
