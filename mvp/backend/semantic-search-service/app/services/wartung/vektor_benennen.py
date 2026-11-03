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

Rueckweg: Ein Restore ueber den Alias legt den unbenannten Vektor in die Collection
hinter dem Alias, meist ``<name>_<EMBEDDING_VEKTOR>`` selbst. Ein neuer Lauf kopiert
dann in eine andere Collection (``ziel_collection(name, belegt=...)``), setzt den Alias
in einem Schritt um und loescht erst danach die alte; der Name fehlt dabei nie.

Aufruf: scripts/manual/vektor_benennen.py
"""

from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    CreateAlias,
    CreateAliasOperation,
    DeleteAlias,
    DeleteAliasOperation,
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


def ziel_collection(collection: str, belegt: Optional[str] = None) -> str:
    """
    Die neue Collection, auf die der alte Name danach als Alias zeigt.

    belegt: die Collection, aus der kopiert wird; liegt die Quelle schon unter dem
    ueblichen Namen (nach einem Restore ueber den Alias), weicht das Ziel aus.
    """
    ziel = f"{collection}_{EMBEDDING_VEKTOR}"
    return f"{ziel}_2" if ziel == belegt else ziel


def _hinter_alias(client: QdrantClient, collection: str) -> Optional[str]:
    """Die Collection, auf die collection als Alias zeigt; None, wenn kein Alias."""
    for alias in client.get_aliases().aliases:
        if alias.alias_name == collection:
            return alias.collection_name
    return None


def _stand(client: QdrantClient, collection: str) -> str:
    vektoren = client.get_collection(collection).config.params.vectors
    if not isinstance(vektoren, dict):
        return UNBENANNT
    if EMBEDDING_VEKTOR not in vektoren:
        raise ValueError(f"{collection} hat keinen Vektor {EMBEDDING_VEKTOR}")
    return BENANNT


def _anzahl(client: QdrantClient, collection: str) -> int:
    return client.count(collection, exact=True).count


def _alias_setzen(
    client: QdrantClient, collection: str, ziel: str, umsetzen: bool = False
) -> None:
    """Alias collection -> ziel; umsetzen: einen bestehenden Alias in einem Schritt."""
    neu = CreateAliasOperation(
        create_alias=CreateAlias(collection_name=ziel, alias_name=collection)
    )
    alt = DeleteAliasOperation(delete_alias=DeleteAlias(alias_name=collection))
    client.update_collection_aliases(
        change_aliases_operations=[alt, neu] if umsetzen else [neu]
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

    # Nach einem Restore ueber den Alias liegt die Quelle hinter dem Alias, oft unter
    # dem ueblichen Zielnamen: dann nicht als Rest loeschen, sondern ausweichen.
    quelle = _hinter_alias(client, collection)
    ziel = ziel_collection(collection, belegt=quelle)
    info = client.get_collection(collection)
    if client.collection_exists(ziel):
        client.delete_collection(ziel)  # Rest eines abgebrochenen Laufs, nie die Quelle
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

    if quelle is None:
        client.delete_collection(collection)
        _alias_setzen(client, collection, ziel)
    else:
        _alias_setzen(client, collection, ziel, umsetzen=True)
        client.delete_collection(quelle)
    return BenennenBericht(
        ausgefuehrt=True,
        vorher=vorher,
        punkte=punkte,
        kopiert=kopiert,
        nachher=_stand(client, collection),
        ziel=ziel,
    )
