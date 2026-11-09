"""
Nachtrag des Payload-Felds antwort_ids fuer bestehende Aussagen (#603).

Neue und geaenderte Aussagen bekommen das Feld beim Schreiben
(QdrantBaseRepository.upsert, aus_aussagen_entfernen). Was vorher geschrieben
wurde, hat es nicht; die Beitragsseite zeigt dort keine Aussage und keine weiteren
Antworten, bis es nachgetragen ist.

Idempotent: Geschrieben wird nur, wo das Feld fehlt oder nicht zu replysuggestions
passt - ein zweiter Lauf schreibt nichts. set_payload aendert nur dieses eine Feld;
Antworten, Status und Vektoren bleiben unberuehrt. Ohne ausfuehren=True wird nur
gezaehlt.

Aufruf: scripts/manual/antwort_ids_nachtragen.py
"""

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    SetPayload,
    SetPayloadOperation,
)

from domain.models.content_type import ContentType
from utils.antwort_ids import FELD_ANTWORT_IDS, antwort_ids

SEITE = 256


@dataclass
class NachtragBericht:
    """Nur Zaehler - keine Texte, keine IDs."""

    ausgefuehrt: bool
    index_vorher: bool
    index_nachher: bool
    geprueft: int = 0
    aktuell: int = 0
    nachzutragen: int = 0
    nachgetragen: int = 0


def _index_vorhanden(client: QdrantClient, collection: str) -> bool:
    schema = client.get_collection(collection).payload_schema or {}
    return FELD_ANTWORT_IDS in schema


def nachtragen(
    client: QdrantClient, collection: str, ausfuehren: bool = False
) -> NachtragBericht:
    index_vorher = _index_vorhanden(client, collection)
    if ausfuehren and not index_vorher:
        client.create_payload_index(
            collection_name=collection,
            field_name=FELD_ANTWORT_IDS,
            field_schema="keyword",
            wait=True,
        )

    bericht = NachtragBericht(
        ausgefuehrt=ausfuehren, index_vorher=index_vorher, index_nachher=False
    )
    nur_aussagen = Filter(
        must=[
            FieldCondition(
                key="content_type", match=MatchValue(value=ContentType.STATEMENT.value)
            )
        ]
    )

    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            scroll_filter=nur_aussagen,
            limit=SEITE,
            offset=offset,
            with_payload=["replysuggestions", FELD_ANTWORT_IDS],
            with_vectors=False,
        )
        operationen = []
        for punkt in punkte:
            payload = punkt.payload or {}
            bericht.geprueft += 1
            soll = antwort_ids(payload.get("replysuggestions"))
            if payload.get(FELD_ANTWORT_IDS) == soll:
                bericht.aktuell += 1
                continue
            bericht.nachzutragen += 1
            if ausfuehren:
                operationen.append(
                    SetPayloadOperation(
                        set_payload=SetPayload(
                            payload={FELD_ANTWORT_IDS: soll}, points=[punkt.id]
                        )
                    )
                )
                bericht.nachgetragen += 1
        if operationen:
            client.batch_update_points(
                collection_name=collection, update_operations=operationen, wait=True
            )
        if offset is None:
            break

    bericht.index_nachher = _index_vorhanden(client, collection)
    return bericht
