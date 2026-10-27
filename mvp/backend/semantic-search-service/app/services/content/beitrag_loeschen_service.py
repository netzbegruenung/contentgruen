"""
Der Autor loescht seinen Beitrag (GLOSSARY.md, "Geloescht"; #250).

Loeschen setzt nur den Zustand "geloescht". Der Beitrag bleibt gespeichert, damit
Verknuepfungen und Stimmen nicht ins Leere zeigen; Suche, Einzelansicht, Listen,
Bestandszaehler und "Meine Beitraege" blenden ihn ueber die vorhandenen Filter der
Repositories aus (AUSGEBLENDET in domain/models/content_status.py). Endgueltig
entfernt wird ein Beitrag nur ueber das Loeschkonzept (docs/LOESCHKONZEPT.md).
"""

import logging
import uuid
from enum import Enum

from pydantic import ValidationError

from domain.models.content_status import AUSGEBLENDET, ContentStatus
from domain.content_registry import BEITRAGSTYPEN
from repositories.interfaces.base_content_repository import IBaseContentRepository

logger = logging.getLogger(__name__)


class LoeschErgebnis(Enum):
    GELOESCHT = "geloescht"
    NICHT_DA = "nicht_da"
    """Kein Beitrag unter der ID, oder er ist schon gesperrt oder geloescht."""
    NICHT_AUTOR = "nicht_autor"


class BeitragLoeschenService:
    def __init__(self, repository: IBaseContentRepository):
        self.repository = repository

    async def loeschen(self, beitrag_id: uuid.UUID, aufrufer: str) -> LoeschErgebnis:
        """
        Den Beitrag in den Zustand "geloescht" setzen, wenn aufrufer sein Autor ist.

        Gesperrte und geloeschte Beitraege sind fuer den Autor nicht da (get()
        blendet sie aus): Eine Sperre bleibt so stehen, und wiederholtes Loeschen
        aendert nichts. Sperrt ein Admin zwischen Lesen und Schreiben, schuetzt
        nicht_aus die Sperre im selben Schreibvorgang. Ein Ausschluss statt nur_aus,
        weil get() Altwerte von vor #214 als sichtbar liest; ein Filter auf
        "visible" traefe den gespeicherten Altwert nicht.

        Ein unlesbarer Datensatz ist ein Fehler, kein "nicht da": ValidationError
        (eine Unterklasse von ValueError) geht weiter.
        """
        try:
            beitrag = await self.repository.get(beitrag_id)
        except ValidationError:
            raise
        except ValueError:
            return LoeschErgebnis.NICHT_DA

        if beitrag.content_type not in BEITRAGSTYPEN:
            return LoeschErgebnis.NICHT_DA
        if beitrag.original_author != aufrufer:
            return LoeschErgebnis.NICHT_AUTOR

        await self.repository.update_status(
            beitrag_id, ContentStatus.DELETED, nicht_aus=AUSGEBLENDET
        )
        logger.info(f"Beitrag {beitrag_id} vom Autor geloescht")
        return LoeschErgebnis.GELOESCHT
