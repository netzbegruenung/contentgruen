"""
Einen Beitrag ueber das aggregierte Repository lesen, fuer Nutzung und Stimmen.

"Nicht da" (gesperrt, geloescht, nie vorhanden) und "kaputt" (der Datensatz ist da,
validiert aber nicht) sind verschiedene Faelle: Das erste ist erwartbar, etwa bei
einem alten Link; das zweite ist ein Fehler im Bestand und wird geloggt.
"""

import logging
import uuid
from typing import Awaitable, Callable, Optional

from pydantic import ValidationError

from domain.models.content import ContentDbEntry
from repositories.interfaces.content_repository import IContentRepository

logger = logging.getLogger(__name__)


class BeitragUnlesbar(Exception):
    """
    Der Datensatz ist da, aber er laesst sich nicht lesen. Das ist kaputt, nicht
    abwesend - also kein 404, und Nutzung oder Stimme zaehlen trotzdem.
    """


# Was die Endpunkte per Depends(get_beitrag_laden) bekommen: beitrag_laden mit
# dem aggregierten Repository schon eingesetzt.
BeitragLader = Callable[[uuid.UUID], Awaitable[Optional[ContentDbEntry]]]


async def beitrag_laden(
    content_id: uuid.UUID, repository: IContentRepository
) -> Optional[ContentDbEntry]:
    """
    Den Beitrag zu dieser ID aus ``repository`` (dem aggregierten
    Content-Repository), oder None, wenn es ihn nicht gibt.

    Gesperrt, geloescht oder nie vorhanden heisst "nicht da". Gebraucht von der
    Nutzung (Existenz und Vergleich mit der zaehlenden Person, api/v1/usage.py) und
    von den Stimmen (api/v1/voting.py), beide ueber ``get_beitrag_laden`` in
    dependencies.py.

    Raises:
    - BeitragUnlesbar, wenn der Datensatz existiert, aber nicht validiert.
    """
    try:
        return await repository.get(content_id)
    except ValidationError as fehler:
        # Vor ValueError, denn Pydantics ValidationError ist einer. Ohne diesen
        # Zweig gaelte ein kaputter Datensatz als "nicht vorhanden": Der Aufruf
        # bekaeme 404, die Kopie fiele unter den Tisch und niemand erfuehre, dass
        # da etwas im Bestand nicht stimmt.
        logger.error(
            f"Content {content_id} is not readable: {type(fehler).__name__}",
            exc_info=True,
        )
        raise BeitragUnlesbar(str(content_id)) from fehler
    except ValueError:
        # Nicht vorhanden - erwartbar bei einem alten Link, kein Fehlerfall.
        return None
