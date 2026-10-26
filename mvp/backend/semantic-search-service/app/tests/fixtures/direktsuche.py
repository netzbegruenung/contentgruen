"""
Direktsuche fuer Router-Tests mit gefakten Diensten.

Der SearchOrchestrator fragt den Suchindex fuer alle Beitragstypen mit einer
Anfrage ab (search_batch, #304). Gefakte Dienste haben kein Repository dahinter;
dieser Ersatz ruft stattdessen je Dienst dessen ``search`` auf, so wie die Suche
vor #304 lief. Damit bleiben die Fakes bei ``service.search = AsyncMock(...)``.
"""

from unittest.mock import patch


async def search_batch_je_dienst(services, query_text, limit):
    return [await service.search(query_text, limit=limit) for service in services]


def direktsuche_ueber_dienste():
    """patch(), das search_batch im SearchOrchestrator ersetzt; start()/stop() oder with."""
    return patch(
        "services.search.search_orchestrator.search_batch",
        side_effect=search_batch_je_dienst,
    )
