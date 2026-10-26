"""
Der Autor loescht seinen Beitrag (GLOSSARY.md, "Geloescht"; #250).

Loeschen setzt nur den Zustand "geloescht". Der Beitrag bleibt gespeichert, damit
Verknuepfungen und Stimmen nicht ins Leere zeigen; Suche, Einzelansicht, Listen,
Zaehler und "Meine Beitraege" blenden ihn ueber die vorhandenen Filter der
Repositories aus (AUSGEBLENDET in domain/models/content_status.py). Endgueltig
entfernt wird ein Beitrag nur ueber das Loeschkonzept (docs/LOESCHKONZEPT.md).
"""

import logging
import uuid
from enum import Enum

from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from repositories.interfaces.base_content_repository import IBaseContentRepository

logger = logging.getLogger(__name__)

BEITRAGSTYPEN = frozenset(
    {
        ContentType.COMMENTARY,
        ContentType.GENERIC_TEXT,
        ContentType.IMAGE,
        ContentType.POST,
    }
)
"""
Typen, die Beitraege sind (GLOSSARY.md, "Beitrag"). Aussage und Herkunft sind
keine: Sie entstehen nebenbei und gehoeren niemandem zum Loeschen.
"""


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
        aendert nichts.
        """
        try:
            beitrag = await self.repository.get(beitrag_id)
        except ValueError:
            return LoeschErgebnis.NICHT_DA

        if beitrag.content_type not in BEITRAGSTYPEN:
            return LoeschErgebnis.NICHT_DA
        if beitrag.original_author != aufrufer:
            return LoeschErgebnis.NICHT_AUTOR

        await self.repository.update_status(beitrag_id, ContentStatus.DELETED)
        logger.info(f"Beitrag {beitrag_id} vom Autor geloescht")
        return LoeschErgebnis.GELOESCHT
