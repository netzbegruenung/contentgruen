"""
Die Zahl "N Antworten" einer Aussage (replysuggestions_count, #631): wie viele ihrer
Antwortvorschlaege auf einen Beitrag zeigen, den die Suche findet. Gesperrte,
geloeschte und nicht mehr vorhandene Beitraege zaehlen nicht mit; ihr Verweis
bleibt trotzdem stehen, damit Entsperren nichts wiederherstellen muss.

Gezaehlt wird beim Schreiben (Verknuepfen, Sperren, Entsperren, Loeschen), nicht
beim Ausliefern: Die Suche filtert in Qdrant auf das Feld
(statement_repository.py) und braucht so keine Zusatzabfrage.
"""

import logging
import uuid
from typing import Iterable, List

from domain.models.content_status import ALT_AUFFINDBAR, ContentStatus

logger = logging.getLogger(__name__)


def findet_die_suche(status) -> bool:
    """
    Ob die Suche einen Beitrag mit diesem gespeicherten Status findet: dasselbe
    Kriterium wie nur_sichtbar_bedingungen (base_repository.py) - sichtbar, ein
    Altwert aus ALT_AUFFINDBAR oder ohne Status.
    """
    return status is None or status in ALT_AUFFINDBAR | {ContentStatus.VISIBLE.value}


def _gueltige_ids(ids: Iterable) -> List[str]:
    """Die IDs als Text, ohne Doppelte und ohne solche, die keine UUID sind."""
    gueltig = []
    for beitrag_id in ids:
        try:
            gueltig.append(str(uuid.UUID(str(beitrag_id))))
        except ValueError:
            logger.warning("Skipping reply suggestion without a valid id")
    return list(dict.fromkeys(gueltig))


async def sichtbare_antworten_zaehlen(client, collection: str, ids: Iterable) -> int:
    """Wie viele der Beitraege zu diesen IDs die Suche findet; eine Abfrage, nur der Status."""
    gueltig = _gueltige_ids(ids)
    if not gueltig:
        return 0
    punkte = await client.retrieve(
        collection_name=collection,
        ids=gueltig,
        with_payload=["status"],
        with_vectors=False,
    )
    return sum(
        1 for punkt in punkte if findet_die_suche((punkt.payload or {}).get("status"))
    )
