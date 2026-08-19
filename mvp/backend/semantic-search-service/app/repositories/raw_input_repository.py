"""
Repository fuer den Fangkorb (Rohinput).

Datenzugriff auf ``raw_inputs``. Bewusst schmal: anlegen, auflisten, zaehlen.
Zuweisung, Statuswechsel und Verknuepfung mit fertigen Beitraegen gehoeren zur
Bearbeitungs-Queue, die es noch nicht gibt (siehe docs/ROHINPUT.md).
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from domain.models.raw_input import RawInputSource, RawInputStatus
from infrastructure.database.connection import get_app_database
from infrastructure.database.models import RawInput

logger = logging.getLogger(__name__)


class RawInputRepository:
    """Repository fuer Einwuerfe im Fangkorb."""

    def __init__(self):
        self.db = get_app_database()

    @staticmethod
    def _to_dict(raw_input: RawInput) -> Dict[str, Any]:
        """In ein Dict uebersetzen, solange die Session noch offen ist."""
        return {
            "id": str(raw_input.id),
            "content": raw_input.content,
            "url": raw_input.url,
            "image_url": raw_input.image_url,
            "submitted_by": raw_input.submitted_by,
            "source_channel": raw_input.source_channel,
            "status": raw_input.status,
            "created_at": raw_input.created_at,
        }

    def create(
        self,
        content: Optional[str] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        submitted_by: Optional[str] = None,
        source_channel: str = RawInputSource.WEB.value,
    ) -> Dict[str, Any]:
        """
        Einen Einwurf anlegen.

        Args:
            content: Freitext - der eine Satz oder die Notiz zum Link
            url: Link auf den Beitrag draussen
            image_url: Bild-URL (kein Upload, siehe docs/ROHINPUT.md)
            submitted_by: Wer eingeworfen hat; None fuer Kanaele ohne Sitzung
            source_channel: Herkunftskanal, heute immer "web"

        Returns:
            Dict[str, Any]: der angelegte Einwurf
        """
        try:
            with self.db.get_session() as session:
                raw_input = RawInput(
                    content=content,
                    url=url,
                    image_url=image_url,
                    submitted_by=submitted_by,
                    source_channel=source_channel,
                    status=RawInputStatus.OPEN.value,
                )
                session.add(raw_input)
                session.commit()
                session.refresh(raw_input)
                logger.info(
                    f"Rohinput {raw_input.id} angelegt "
                    f"(Kanal: {source_channel}, von: {submitted_by or 'ohne Kennung'})"
                )
                return self._to_dict(raw_input)
        except Exception as e:
            logger.error(f"Fehler beim Anlegen eines Rohinputs: {e}", exc_info=True)
            raise

    def get_all(
        self, limit: int = 20, offset: int = 0, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Einwuerfe auflisten, neueste zuerst.

        Absichtlich ohne Filter auf die einwerfende Person: der Fangkorb ist ein
        gemeinsamer Vorrat, nicht die eigene Ablage.

        Args:
            limit: maximale Anzahl
            offset: zu ueberspringende Eintraege
            status: optionaler Filter auf einen Bearbeitungsstand

        Returns:
            List[Dict[str, Any]]: die Einwuerfe
        """
        try:
            with self.db.get_session() as session:
                query = session.query(RawInput)
                if status is not None:
                    query = query.filter(RawInput.status == status)

                rows = (
                    query.order_by(desc(RawInput.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                return [self._to_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Rohinputs: {e}", exc_info=True)
            raise

    def count(self, status: Optional[str] = None) -> int:
        """Anzahl der Einwuerfe, optional auf einen Bearbeitungsstand gefiltert."""
        try:
            with self.db.get_session() as session:
                query = session.query(RawInput)
                if status is not None:
                    query = query.filter(RawInput.status == status)
                return query.count()
        except Exception as e:
            logger.error(f"Fehler beim Zaehlen der Rohinputs: {e}", exc_info=True)
            raise


# Globale Repository-Instanz
_raw_input_repository: Optional[RawInputRepository] = None


def get_raw_input_repository() -> RawInputRepository:
    """Die globale RawInputRepository-Instanz holen oder anlegen."""
    global _raw_input_repository
    if _raw_input_repository is None:
        _raw_input_repository = RawInputRepository()
    return _raw_input_repository
