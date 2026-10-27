"""
Direktsuche fuer Router-Tests mit gefakten Diensten.

Der SearchOrchestrator fragt den Suchindex fuer alle Beitragstypen mit einer
Anfrage ab (BaseContentService.search_batch, #304). Gefakte Dienste haben kein Repository dahinter;
dieser Ersatz ruft stattdessen je Dienst dessen ``search`` auf, so wie die Suche
vor #304 lief. Damit bleiben die Fakes bei ``service.search = AsyncMock(...)``.
"""

from unittest.mock import patch

from services.content.base_content_service import BaseContentService


async def search_batch_je_dienst(services, query_text, limit):
    return [await service.search(query_text, limit=limit) for service in services]


def direktsuche_ueber_dienste():
    """patch(), das BaseContentService.search_batch ersetzt; start()/stop() oder with."""
    return patch.object(BaseContentService, "search_batch", search_batch_je_dienst)
