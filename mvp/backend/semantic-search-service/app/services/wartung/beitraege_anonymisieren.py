"""
Beitraege einer Person anonymisieren: Schritt 3 des Loeschkonzepts
(docs/LOESCHKONZEPT.md).

Beitraege bleiben stehen, nur die Kennung geht: In ``original_author``,
``last_modified_by``, ``authors[].name`` und ``edit_history[].editor`` tritt der
Platzhalter ``ehemalige-person`` an ihre Stelle, und die Karten zeigen dazu
"ehemalige Person" (services/anzeigename_service.py). Fremde Kennungen am selben
Beitrag bleiben, ebenso alles andere im Payload.

Derselbe Lauf mit der Kennung ``geloeschter-nutzer`` stellt den Bestand um, der vor
#236 mit dem alten Platzhalter anonymisiert wurde.

Idempotent: Ein zweiter Lauf findet nichts mehr, was die Kennung traegt. Ohne
ausfuehren=True wird nur gesucht. Der Bericht nennt Typ und Text jedes Treffers -
fuer die Einzelfallpruefung, ob ein Text die Person selbst erkennbar macht.

Aufruf: scripts/manual/beitraege_anonymisieren.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    SetPayload,
    SetPayloadOperation,
)

from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG, angemeldet

# Platzhalter bis #236; Karten zeigten dazu "Mitglied".
ALTER_PLATZHALTER = "geloeschter-nutzer"

SEITE = 256
_FELDER = ("original_author", "last_modified_by")
_LISTEN = (("authors", "name"), ("edit_history", "editor"))


@dataclass
class Treffer:
    id: Union[int, str]
    content_type: Optional[str]
    text: Optional[str]


@dataclass
class AnonymisierungBericht:
    ausgefuehrt: bool
    treffer: List[Treffer] = field(default_factory=list)


def _ersetzt(payload: Dict[str, Any], kennung: str) -> Dict[str, Any]:
    """Nur die Felder, in denen die Kennung vorkommt, mit dem Platzhalter."""
    neu: Dict[str, Any] = {
        feld: EHEMALIGE_PERSON_KENNUNG
        for feld in _FELDER
        if payload.get(feld) == kennung
    }
    for feld, schluessel in _LISTEN:
        eintraege = payload.get(feld) or []
        if any(e.get(schluessel) == kennung for e in eintraege):
            neu[feld] = [
                (
                    {**e, schluessel: EHEMALIGE_PERSON_KENNUNG}
                    if e.get(schluessel) == kennung
                    else e
                )
                for e in eintraege
            ]
    return neu


def anonymisieren(
    client: QdrantClient, collection: str, kennung: str, ausfuehren: bool = False
) -> AnonymisierungBericht:
    # Eine leere Kennung oder der Platzhalter selbst bezeichnet niemanden; ein
    # Tippfehler im Aufruf soll nicht still alle anonymen Felder umschreiben oder
    # mit Leerzeichen am Rand nichts finden und "0" melden.
    if (
        not angemeldet(kennung)
        or kennung != kennung.strip()
        or kennung == EHEMALIGE_PERSON_KENNUNG
    ):
        raise ValueError("keine Kennung einer Person")

    filt = Filter(
        should=[
            FieldCondition(key=k, match=MatchValue(value=kennung))
            for k in (*_FELDER, *(f"{f}[].{s}" for f, s in _LISTEN))
        ]
    )
    bericht = AnonymisierungBericht(ausgefuehrt=ausfuehren)
    # Erst alle Treffer sammeln, dann schreiben: Ein Scroll ueber den Filter, waehrend
    # die Treffer aus ihm herausfallen, koennte Seiten ueberspringen.
    offset = None
    neu_je_punkt = []
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            scroll_filter=filt,
            limit=SEITE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for punkt in punkte:
            payload = punkt.payload or {}
            neu = _ersetzt(payload, kennung)
            if not neu:
                continue
            bericht.treffer.append(
                Treffer(punkt.id, payload.get("content_type"), payload.get("text"))
            )
            neu_je_punkt.append((punkt.id, neu))
        if offset is None:
            break

    if ausfuehren:
        for start in range(0, len(neu_je_punkt), SEITE):
            client.batch_update_points(
                collection_name=collection,
                update_operations=[
                    SetPayloadOperation(
                        set_payload=SetPayload(payload=neu, points=[punkt_id])
                    )
                    for punkt_id, neu in neu_je_punkt[start : start + SEITE]
                ],
                wait=True,
            )
    return bericht
