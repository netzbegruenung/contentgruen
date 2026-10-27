"""
Der Autor loescht seinen Beitrag (GLOSSARY.md, "Geloescht"; #250).

Loeschen setzt nur den Zustand "geloescht". Der Beitrag bleibt gespeichert, damit
Verknuepfungen und Stimmen nicht ins Leere zeigen; Suche, Einzelansicht, Listen,
Bestandszaehler und "Meine Beitraege" blenden ihn ueber die vorhandenen Filter der
Repositories aus (AUSGEBLENDET in domain/models/content_status.py). Endgueltig
entfernt wird ein Beitrag nur ueber das Loeschkonzept (docs/LOESCHKONZEPT.md).

Nur die Verweise der Aussagen auf ihn gehen weg (#294): Sonst zaehlte eine Aussage,
deren einziger Beitrag geloescht ist, weiter als beantwortet, etwa im Zaehler auf der
Startseite (StatementRepository.count_curated).
"""

import logging
import uuid
from enum import Enum

from pydantic import ValidationError

from domain.models.content_status import AUSGEBLENDET, ContentStatus
from domain.content_registry import BEITRAGSTYPEN
from repositories.interfaces.base_content_repository import IBaseContentRepository
from repositories.interfaces.moderation_repository import IModerationRepository

logger = logging.getLogger(__name__)


class LoeschErgebnis(Enum):
    GELOESCHT = "geloescht"
    NICHT_DA = "nicht_da"
    """Kein Beitrag unter der ID, oder er ist schon gesperrt oder geloescht."""
    NICHT_AUTOR = "nicht_autor"


class BeitragLoeschenService:
    def __init__(
        self, repository: IBaseContentRepository, aussagen: IModerationRepository
    ):
        self.repository = repository
        self.aussagen = aussagen

    async def loeschen(self, beitrag_id: uuid.UUID, aufrufer: str) -> LoeschErgebnis:
        """
        Den Beitrag in den Zustand "geloescht" setzen, wenn aufrufer sein Autor ist.

        Gesperrte und geloeschte Beitraege sind fuer den Autor nicht da (get()
        blendet sie aus): Eine Sperre bleibt so stehen, und wiederholtes Loeschen
        aendert nichts. Sperrt ein Admin zwischen Lesen und Schreiben, schuetzt
        nicht_aus die Sperre im selben Schreibvorgang. Ein Ausschluss statt eines
        Filters auf den erwarteten Zustand, weil get() Altwerte von vor #214 als sichtbar liest; ein Filter auf
        "visible" traefe den gespeicherten Altwert nicht.

        Ein unlesbarer Datensatz ist ein Fehler, kein "nicht da": ValidationError
        (eine Unterklasse von ValueError) geht weiter.

        Erst die Verweise der Aussagen, dann der Zustand: Scheitert das Entfernen der
        Verweise, geht der Fehler weiter und der Beitrag bleibt sichtbar, sodass ein
        erneuter Versuch aufraeumt. Andersherum faende ein zweiter Versuch den
        geloeschten Beitrag nicht mehr, und die Verweise blieben stehen.
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

        await self.aussagen.aus_aussagen_entfernen(str(beitrag_id))
        await self.repository.update_status(
            beitrag_id, ContentStatus.DELETED, nicht_aus=AUSGEBLENDET
        )
        logger.info(f"Beitrag {beitrag_id} vom Autor geloescht")
        return LoeschErgebnis.GELOESCHT
