"""
Nachtrag des Payload-Felds text_normalisiert fuer den Bestand.

Neue und geaenderte Aussagen und Kommentare bekommen das Feld beim Schreiben
(QdrantBaseRepository.upsert). Was vorher geschrieben wurde, hat es nicht; die
Dublettenpruefung findet solche Eintraege dann nur noch ueber die Vektortreffer.

Idempotent: Geschrieben wird nur, wo das Feld fehlt oder nicht zur aktuellen
Normalisierung passt - ein zweiter Lauf schreibt nichts. set_payload aendert nur
dieses eine Feld; Antworten, Status und Vektoren bleiben unberuehrt. Ohne
ausfuehren=True wird nur gezaehlt.

Aufruf: scripts/manual/text_normalisiert_nachtragen.py
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    SetPayload,
    SetPayloadOperation,
)

from utils.text_normalisierung import (
    FELD_TEXT_NORMALISIERT,
    TYPEN_MIT_TEXT_NORMALISIERT,
    text_normalisiert,
)

SEITE = 256


@dataclass
class NachtragBericht:
    """Nur Zaehler - keine Texte, keine IDs."""

    ausgefuehrt: bool
    index_vorher: bool
    index_nachher: bool
    geprueft: Dict[str, int] = field(default_factory=dict)
    aktuell: Dict[str, int] = field(default_factory=dict)
    nachzutragen: Dict[str, int] = field(default_factory=dict)
    nachgetragen: Dict[str, int] = field(default_factory=dict)


def _index_vorhanden(client: QdrantClient, collection: str) -> bool:
    schema = client.get_collection(collection).payload_schema or {}
    return FELD_TEXT_NORMALISIERT in schema


def nachtragen(
    client: QdrantClient, collection: str, ausfuehren: bool = False
) -> NachtragBericht:
    index_vorher = _index_vorhanden(client, collection)
    if ausfuehren and not index_vorher:
        client.create_payload_index(
            collection_name=collection,
            field_name=FELD_TEXT_NORMALISIERT,
            field_schema="keyword",
            wait=True,
        )

    geprueft, aktuell, nachzutragen, nachgetragen = (
        Counter(),
        Counter(),
        Counter(),
        Counter(),
    )
    typ_filter = Filter(
        must=[
            FieldCondition(
                key="content_type",
                match=MatchAny(any=sorted(TYPEN_MIT_TEXT_NORMALISIERT)),
            )
        ]
    )

    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            scroll_filter=typ_filter,
            limit=SEITE,
            offset=offset,
            with_payload=["content_type", "text", FELD_TEXT_NORMALISIERT],
            with_vectors=False,
        )
        operationen = []
        for punkt in punkte:
            payload = punkt.payload or {}
            typ = payload.get("content_type")
            geprueft[typ] += 1
            soll = text_normalisiert(payload.get("text") or "")
            if payload.get(FELD_TEXT_NORMALISIERT) == soll:
                aktuell[typ] += 1
                continue
            nachzutragen[typ] += 1
            if ausfuehren:
                operationen.append(
                    SetPayloadOperation(
                        set_payload=SetPayload(
                            payload={FELD_TEXT_NORMALISIERT: soll}, points=[punkt.id]
                        )
                    )
                )
                nachgetragen[typ] += 1
        if operationen:
            client.batch_update_points(
                collection_name=collection, update_operations=operationen, wait=True
            )
        if offset is None:
            break

    return NachtragBericht(
        ausgefuehrt=ausfuehren,
        index_vorher=index_vorher,
        index_nachher=_index_vorhanden(client, collection),
        geprueft=dict(geprueft),
        aktuell=dict(aktuell),
        nachzutragen=dict(nachzutragen),
        nachgetragen=dict(nachgetragen),
    )
