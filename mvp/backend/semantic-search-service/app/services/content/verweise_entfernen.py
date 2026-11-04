"""
Verweise der Aussagen auf einen Beitrag entfernen, bevor er geloescht oder endgueltig
entfernt wird (#294). Beide Loeschwege (Autor, Admin) gehen hier durch, damit ein
Fehler auf beiden gleich geloggt und gemeldet wird.

Erst die Verweise, dann der Beitrag: Scheitert das Entfernen, bleibt der Beitrag
stehen und ein erneuter Versuch raeumt die restlichen Verweise auf. Bricht es mitten
im Lauf ab und versucht es niemand erneut, bleibt ein sichtbarer Beitrag an einem
Teil der Aussagen ohne Verweis; zurueck kommt der nicht (docs/LOESCHKONZEPT.md).
"""

import logging

from repositories.interfaces.moderation_repository import IModerationRepository

logger = logging.getLogger(__name__)


class VerweiseNichtEntfernt(Exception):
    """
    Aussagen verweisen noch auf den Beitrag, der geloescht werden sollte. Er ist
    nicht geloescht; ein erneuter Versuch raeumt die restlichen Verweise auf.
    """


async def verweise_entfernen(
    moderation_repo: IModerationRepository, beitrag_id: str
) -> None:
    """Den Beitrag aus den Antwortvorschlaegen aller Aussagen streichen."""
    try:
        geaendert = await moderation_repo.aus_aussagen_entfernen(beitrag_id)
    except Exception as e:
        logger.error(
            f"Removing reply suggestions for {beitrag_id} failed: {type(e).__name__}",
            exc_info=True,
        )
        raise VerweiseNichtEntfernt(beitrag_id) from e

    logger.info(
        f"Removed {beitrag_id} from reply suggestions of {geaendert} statements"
    )
