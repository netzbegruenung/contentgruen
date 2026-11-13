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

Mit ``angelegt_bis`` (Loeschauftrag nach dem Widerruf) nur Beitraege, deren
``created`` nicht spaeter liegt; spaetere bleiben, wie sie sind, und stehen im
Bericht unter ``behalten``. Ein Beitrag ohne lesbares ``created`` zaehlt als frueher.

Aufruf: scripts/manual/beitraege_anonymisieren.py
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    SetPayload,
    SetPayloadOperation,
)

from services.anzeigename_service import (
    EHEMALIGE_PERSON_KENNUNG,
    KENNUNGSFELDER,
    KENNUNGSLISTEN,
    angemeldet,
)

# Platzhalter bis #236; Karten zeigten dazu "Mitglied".
ALTER_PLATZHALTER = "geloeschter-nutzer"

SEITE = 256


@dataclass
class Treffer:
    id: Union[int, str]
    content_type: Optional[str]
    text: Optional[str]


@dataclass
class AnonymisierungBericht:
    ausgefuehrt: bool
    treffer: List[Treffer] = field(default_factory=list)
    # Punkte mit der Kennung, aber nach ``angelegt_bis`` angelegt: unberuehrt
    behalten: List[Union[int, str]] = field(default_factory=list)


def _angelegt(payload: Dict[str, Any]) -> Optional[datetime]:
    wert = payload.get("created")
    if isinstance(wert, datetime):
        zeitpunkt = wert
    elif isinstance(wert, str) and wert:
        try:
            zeitpunkt = datetime.fromisoformat(wert.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    # Gespeichert wird in UTC, aeltere Punkte ohne Zeitzone.
    if zeitpunkt.tzinfo is None:
        zeitpunkt = zeitpunkt.replace(tzinfo=timezone.utc)
    return zeitpunkt


def _spaeter(payload: Dict[str, Any], angelegt_bis: Optional[datetime]) -> bool:
    if angelegt_bis is None:
        return False
    angelegt = _angelegt(payload)
    return angelegt is not None and angelegt > angelegt_bis


def _geaenderte_felder(payload: Dict[str, Any], kennung: str) -> Dict[str, Any]:
    """Nur die Felder, in denen die Kennung vorkommt, mit dem Platzhalter."""
    neu: Dict[str, Any] = {
        feld: EHEMALIGE_PERSON_KENNUNG
        for feld in KENNUNGSFELDER
        if payload.get(feld) == kennung
    }
    for feld, schluessel in KENNUNGSLISTEN:
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
    client: QdrantClient,
    collection: str,
    kennung: str,
    ausfuehren: bool = False,
    angelegt_bis: Optional[datetime] = None,
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

    traegt_kennung = Filter(
        should=[
            FieldCondition(key=k, match=MatchValue(value=kennung))
            for k in (*KENNUNGSFELDER, *(f"{f}[].{s}" for f, s in KENNUNGSLISTEN))
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
            scroll_filter=traegt_kennung,
            limit=SEITE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for punkt in punkte:
            payload = punkt.payload or {}
            neu = _geaenderte_felder(payload, kennung)
            if not neu:
                continue
            if _spaeter(payload, angelegt_bis):
                bericht.behalten.append(punkt.id)
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
