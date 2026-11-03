"""
Varianten (Glossar "Variante", #356): "Als Vorlage nehmen" legt einen neuen Beitrag
mit eigenem Autor an, der auf dem Original "beruht". Gespeichert wird er wie jeder
andere ueber das Formular seines Typs, mit Dublettenpruefung; erst ein neu angelegter
Beitrag wird mit dem Original verknuepft (beruht_auf_festhalten). Am Original zeigt
die Karte "N Varianten" (varianten_ergaenzen).

Die Verknuepfung liegt in PostgreSQL (repositories/varianten_repository.py), die
Beitraege im Suchindex. Scheitert eines davon, bleibt der Beitrag gespeichert bzw.
die Liste nutzbar, nur ohne Verknuepfung oder Zahl.
"""

import logging
import uuid
from typing import Awaitable, Callable, Optional, Sequence

from dtos.beitrag import BeitragResponse
from repositories.varianten_repository import VariantenRepository

logger = logging.getLogger(__name__)


async def beruht_auf_festhalten(
    repository: VariantenRepository,
    variante_id: uuid.UUID,
    original_id: uuid.UUID,
    original_laden: Callable[[uuid.UUID], Awaitable[Optional[object]]],
) -> bool:
    """
    Die neue Variante beruht auf dem Original, wenn es sichtbar ist.

    ``original_laden`` ist ``get`` des Dienstes vom Typ der Variante: Eine Variante
    beruht auf einem Beitrag desselben Typs, und ``get`` liefert gesperrte,
    geloeschte und fehlende Beitraege nicht (None oder ValueError). Dann bleibt die
    Variante ein Beitrag fuer sich.

    True, wenn verknuepft; scheitert etwas, False und ein Eintrag im Log, der
    Beitrag bleibt gespeichert.
    """
    try:
        original = await original_laden(original_id)
    except ValueError:
        original = None
    except Exception as e:
        logger.error(
            f"Variant {variante_id} saved, original not readable: {type(e).__name__}",
            exc_info=True,
        )
        return False
    if original is None:
        logger.warning(
            f"Variant {variante_id} saved without link: original {original_id} is not available"
        )
        return False
    try:
        repository.festhalten(variante_id, original_id)
    except Exception as e:
        logger.error(
            f"Variant {variante_id} saved, but not linked to its original: {type(e).__name__}",
            exc_info=True,
        )
        return False
    return True


def varianten_ergaenzen(
    beitraege: Sequence[BeitragResponse], repository: VariantenRepository
) -> None:
    """
    Setzt an jedem Kommentar und jeder Hintergrundinfo ``varianten``, aus einer
    Abfrage fuer alle. Ist PostgreSQL nicht erreichbar, bleibt es bei 0: Die Karten
    kommen trotzdem.
    """
    # Varianten gibt es nur von Typen mit Formular zum Vorbelegen (Kommentar,
    # Hintergrundinfo); nur ihre Responses haben das Feld.
    beitraege = [b for b in beitraege if "varianten" in type(b).model_fields]
    if not beitraege:
        return
    try:
        anzahl = repository.anzahl_je_original([beitrag.id for beitrag in beitraege])
    except Exception as e:
        logger.warning(f"Variant counts not readable: {type(e).__name__}")
        return
    for beitrag in beitraege:
        beitrag.varianten = anzahl.get(beitrag.id, 0)
