"""
Den unbenannten Vektor einer Collection von vor #395 als benannten Vektor fuehren.

Seit #395 legt der Dienst seinen Vektor unter dem Namen EMBEDDING_VEKTOR ab, damit
weitere Modelle daneben einen eigenen Vektor bekommen koennen. Qdrant kann einen
unbenannten Vektor nicht umbenennen; deshalb entsteht eine neue Collection
``<name>_<EMBEDDING_VEKTOR>`` mit denselben Punkten, Payloads, Vektoren und
Payload-Indizes. Die alte wird geloescht und ihr Name zum Alias auf die neue: Dienst,
Backup und Wartungsskripte arbeiten weiter mit dem gewohnten Namen.

Nichts wird neu eingebettet; die Vektoren werden kopiert, die Treffer bleiben gleich.
Ohne ausfuehren=True wird nur gezaehlt. Idempotent: Ist der Vektor schon benannt,
aendert ein Lauf nichts. Brach ein Lauf vor dem Loeschen der alten Collection ab,
ersetzt der naechste die halbe Kopie; brach er danach ab, setzt der naechste nur den
Alias. Den Dienst erst nach dem Lauf neu starten: Fehlt der Name, legt er eine leere
Collection an.

Aufruf: scripts/manual/vektor_benennen.py
"""

from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    CreateAlias,
    CreateAliasOperation,
    PointStruct,
)

from core.config import EMBEDDING_VEKTOR

SEITE = 256

BENANNT = "benannt"
UNBENANNT = "unbenannt"
# Alte Collection schon geloescht, Alias noch nicht gesetzt: Lauf brach dazwischen ab.
KEIN_ALIAS = "kein_alias"


@dataclass
class BenennenBericht:
    """Nur Zaehler und Collection-Namen - keine Texte, keine IDs."""

    ausgefuehrt: bool
    vorher: str
    punkte: int
    kopiert: int = 0
    nachher: Optional[str] = None
    ziel: Optional[str] = None


def ziel_collection(collection: str) -> str:
    """Die neue Collection, auf die der alte Name danach als Alias zeigt."""
    return f"{collection}_{EMBEDDING_VEKTOR}"


def _stand(client: QdrantClient, collection: str) -> str:
    vektoren = client.get_collection(collection).config.params.vectors
    if not isinstance(vektoren, dict):
        return UNBENANNT
    if EMBEDDING_VEKTOR not in vektoren:
        raise ValueError(f"{collection} hat keinen Vektor {EMBEDDING_VEKTOR}")
    return BENANNT


def _anzahl(client: QdrantClient, collection: str) -> int:
    return client.count(collection, exact=True).count


def _alias_setzen(client: QdrantClient, collection: str, ziel: str) -> None:
    client.update_collection_aliases(
        change_aliases_operations=[
            CreateAliasOperation(
                create_alias=CreateAlias(collection_name=ziel, alias_name=collection)
            )
        ]
    )


def benennen(
    client: QdrantClient, collection: str, ausfuehren: bool = False
) -> BenennenBericht:
    ziel = ziel_collection(collection)
    if not client.collection_exists(collection) and client.collection_exists(ziel):
        punkte = _anzahl(client, ziel)
        if ausfuehren:
            _alias_setzen(client, collection, ziel)
        return BenennenBericht(
            ausgefuehrt=ausfuehren,
            vorher=KEIN_ALIAS,
            punkte=punkte,
            nachher=_stand(client, collection) if ausfuehren else KEIN_ALIAS,
            ziel=ziel,
        )

    vorher = _stand(client, collection)
    punkte = _anzahl(client, collection)
    if vorher == BENANNT or not ausfuehren:
        return BenennenBericht(
            ausgefuehrt=ausfuehren, vorher=vorher, punkte=punkte, nachher=vorher
        )

    info = client.get_collection(collection)
    if client.collection_exists(ziel):
        client.delete_collection(ziel)  # Rest eines abgebrochenen Laufs
    client.create_collection(
        ziel,
        vectors_config={EMBEDDING_VEKTOR: info.config.params.vectors},
        on_disk_payload=info.config.params.on_disk_payload,
    )
    for feld, schema in (info.payload_schema or {}).items():
        client.create_payload_index(
            ziel, feld, field_schema=schema.params or schema.data_type, wait=True
        )

    kopiert = 0
    offset = None
    while True:
        seite, offset = client.scroll(
            collection,
            limit=SEITE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if seite:
            client.upsert(
                ziel,
                [
                    PointStruct(
                        id=p.id, vector={EMBEDDING_VEKTOR: p.vector}, payload=p.payload
                    )
                    for p in seite
                ],
                wait=True,
            )
            kopiert += len(seite)
        if offset is None:
            break

    # Kam waehrend der Kopie etwas dazu oder fiel weg, nichts loeschen.
    if _anzahl(client, ziel) != _anzahl(client, collection):
        client.delete_collection(ziel)
        raise RuntimeError(
            "Punkte haben sich waehrend der Kopie geaendert; nichts umgestellt, "
            "erneut laufen lassen"
        )

    client.delete_collection(collection)
    _alias_setzen(client, collection, ziel)
    return BenennenBericht(
        ausgefuehrt=True,
        vorher=vorher,
        punkte=punkte,
        kopiert=kopiert,
        nachher=_stand(client, collection),
        ziel=ziel,
    )
