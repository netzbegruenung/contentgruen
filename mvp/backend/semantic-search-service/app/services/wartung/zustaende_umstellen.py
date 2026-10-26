"""
Bestehende Beitraege auf die drei Zustaende sichtbar, gesperrt, geloescht umstellen
(#214).

Bis dahin kannte der Status zwoelf Werte eines generischen CMS. Die Suche blendete
davon nur ``pending_review``, ``blocked`` und die beiden Bild-Vorstufen aus; alles
andere, auch Punkte ganz ohne Status, war auffindbar. Genau das bildet die
Umstellung ab:

- bisher auffindbar und ``pending_review`` (ALT_SICHTBAR in
  domain/models/content_status.py) -> ``visible``
- ``blocked`` bleibt; ``status_vor_sperre`` wird genauso umgestellt, fehlt er oder
  ist er leer, gilt ``visible``. Sonst braechte Entsperren einen entfernten Wert
  zurueck.
- Die Bild-Vorstufen ``pending_description`` und ``description_failed`` bleiben.
- Das Feld ``visibility`` (Markierung aus #5, ohne Wirkung seit #213) entfaellt,
  auch mit leerem Wert.

Unbekannte Werte bleiben stehen und stehen im Bericht; der Mensch entscheidet.
Idempotent: Ein zweiter Lauf findet nichts mehr. Ohne ausfuehren=True wird nur
gezaehlt. Die Altwerte kennt nur noch der Uebergang in
domain/models/content_status.py, der nach dieser Umstellung entfaellt.

Aufruf: scripts/manual/zustaende_umstellen.py
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from qdrant_client import QdrantClient
from qdrant_client.models import (
    DeletePayload,
    DeletePayloadOperation,
    SetPayload,
    SetPayloadOperation,
)

from domain.models.content_status import ContentStatus, zustand_aus_altwert
from repositories.implementations.qdrant.moderation_repository import (
    FELD_STATUS_VOR_SPERRE,
)

FELD_VISIBILITY = "visibility"
OHNE_STATUS = "(ohne)"

SEITE = 256

SICHTBAR = ContentStatus.VISIBLE.value

BLEIBEN = frozenset(status.value for status in ContentStatus)
"""Werte, die schon dem neuen Modell entsprechen."""


def neuer_zustand(alt: Optional[str]) -> Optional[str]:
    """Neuer Wert fuer einen gespeicherten Status; None, wenn er unbekannt ist."""
    neu = zustand_aus_altwert(alt)
    return neu if neu in BLEIBEN else None


@dataclass
class UmstellungBericht:
    ausgefuehrt: bool
    status: Counter = field(default_factory=Counter)
    """Punkte je gespeichertem Status vor der Umstellung."""
    unbekannt: Dict[str, int] = field(default_factory=dict)
    visibility_entfernt: int = 0
    status_vor_sperre_umgestellt: int = 0
    zu_aendern: int = 0


def _aenderung(
    payload: Dict[str, Any], bericht: UmstellungBericht
) -> Tuple[Dict[str, Any], List[str]]:
    """Zu setzende und zu entfernende Felder eines Punkts."""
    setzen: Dict[str, Any] = {}
    entfernen: List[str] = []

    alt = payload.get("status")
    bericht.status[OHNE_STATUS if alt is None else alt] += 1
    neu = neuer_zustand(alt)
    if neu is None:
        bericht.unbekannt[alt] = bericht.unbekannt.get(alt, 0) + 1
    elif neu != alt:
        setzen["status"] = neu

    if neu == ContentStatus.BLOCKED.value:
        vorher = payload.get(FELD_STATUS_VOR_SPERRE)
        vorher_neu = neuer_zustand(vorher)
        # Eine Sperre ist kein Zustand vor einer Sperre.
        if vorher_neu in (None, ContentStatus.BLOCKED.value):
            vorher_neu = SICHTBAR
        if FELD_STATUS_VOR_SPERRE not in payload or vorher_neu != vorher:
            setzen[FELD_STATUS_VOR_SPERRE] = vorher_neu
            bericht.status_vor_sperre_umgestellt += 1

    if FELD_VISIBILITY in payload:
        entfernen.append(FELD_VISIBILITY)
        bericht.visibility_entfernt += 1

    return setzen, entfernen


def zustaende_umstellen(
    client: QdrantClient, collection: str, ausfuehren: bool = False
) -> UmstellungBericht:
    bericht = UmstellungBericht(ausgefuehrt=ausfuehren)
    aenderungen: List[Tuple[Union[int, str], Dict[str, Any], List[str]]] = []

    # Erst alles lesen, dann schreiben: so aendert sich nichts unter dem Scroll.
    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            limit=SEITE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for punkt in punkte:
            setzen, entfernen = _aenderung(punkt.payload or {}, bericht)
            if setzen or entfernen:
                aenderungen.append((punkt.id, setzen, entfernen))
        if offset is None:
            break
    bericht.zu_aendern = len(aenderungen)

    if ausfuehren:
        for start in range(0, len(aenderungen), SEITE):
            operationen: List[Any] = []
            for punkt_id, setzen, entfernen in aenderungen[start : start + SEITE]:
                if setzen:
                    operationen.append(
                        SetPayloadOperation(
                            set_payload=SetPayload(payload=setzen, points=[punkt_id])
                        )
                    )
                if entfernen:
                    operationen.append(
                        DeletePayloadOperation(
                            delete_payload=DeletePayload(
                                keys=entfernen, points=[punkt_id]
                            )
                        )
                    )
            client.batch_update_points(
                collection_name=collection, update_operations=operationen, wait=True
            )
    return bericht
