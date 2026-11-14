"""
Einen gerade gespeicherten Post oder ein Bild als Antwort an seine Aussage haengen
(#619), im selben Aufruf wie das Speichern. Wie bei Kommentar und Hintergrundinfo
(api/v1/generic_text.py): Scheitert das Verknuepfen, bleibt der Beitrag gespeichert,
und die Antwort sagt es.
"""

import logging
import uuid

from domain.models.content_type import ContentType
from dtos.antwort_auf import AntwortAufAnfrage, AntwortAufErgebnis
from dtos.statement import themen_dtos
from services.aussage_themen_service import AussageThemenService, themen_beim_anlegen
from services.content.statement_service import AussageNichtGefunden, StatementService

logger = logging.getLogger(__name__)


async def als_antwort_verknuepfen(
    anfrage: AntwortAufAnfrage,
    beitrag_id: uuid.UUID,
    content_type: ContentType,
    relevance: float,
    author: str,
    statement_service: StatementService,
    themen_service: AussageThemenService,
) -> AntwortAufErgebnis:
    """
    Verknuepft den Beitrag mit der Aussage aus der Anfrage (per ID oder Text). Ohne
    Aussage passiert nichts, und das Ergebnis ist leer mit verknuepft=True.
    """
    if not (anfrage.statement_id or (anfrage.statement_text or "").strip()):
        return AntwortAufErgebnis()
    try:
        # Drei Werte: ID, Text und ob die Aussage eben neu angelegt wurde.
        statement_id, statement_text, _neu = (
            await statement_service.beitrag_als_antwort_verknuepfen(
                beitrag_id=beitrag_id,
                content_type=content_type,
                relevance=relevance,
                author=author,
                statement_id=anfrage.statement_id,
                statement_text=anfrage.statement_text,
            )
        )
    except AussageNichtGefunden:
        # Erwartbar (Aussage geloescht, alter Link): ohne Traceback.
        logger.warning(
            f"{content_type.value} {beitrag_id} saved, but its statement {anfrage.statement_id} no longer exists"
        )
        return AntwortAufErgebnis(verknuepft=False)
    except Exception as e:
        logger.error(
            f"{content_type.value} {beitrag_id} saved, but not linked to its statement: {type(e).__name__}",
            exc_info=True,
        )
        return AntwortAufErgebnis(verknuepft=False)

    themen = []
    # Kam die Aussage per Text, gelten fuer sie die gewaehlten Themen (#455).
    if anfrage.statement_id is None and anfrage.themen:
        themen = await themen_beim_anlegen(themen_service, statement_id, anfrage.themen)
    return AntwortAufErgebnis(
        statement_id=statement_id,
        statement_text=statement_text,
        themen=themen_dtos(themen),
        verknuepft=True,
    )
