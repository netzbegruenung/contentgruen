"""
Laedt den Seed (Testbestand) in die Sammlung aus SEMANTIC_SEARCH_QDRANT_COLLECTION, ohne
den Dienst zu starten: derselbe SeedingService wie /api/v1/seeding/start, aber im
Vordergrund. Fuer den naechtlichen Lauf (#391), der das Suchtestset gegen ein leeres
Qdrant misst; nie gegen Test oder Produktion (mvp/data/seed/README.md).

    cd mvp/backend/semantic-search-service/app
    SEMANTIC_SEARCH_QDRANT_COLLECTION=nachtlauf ../venv/bin/python -m tests.regression.seed_laden

Bricht ab (Exit 1), wenn die Sammlung schon Inhalte hat: So landet der Seed nie in einem
gepflegten Bestand, und ein zweiter Aufruf misst nicht gegen einen doppelten Seed.
"""

import asyncio
import sys
import tempfile
from typing import Optional, Sequence


async def seed_laden(metadaten_pfad: str) -> int:
    """Laedt den Seed, gibt die Zahl der Eintraege in der Sammlung danach zurueck."""
    from core.config import settings
    from services.embeddings.qdrant_embeddings_manager import (
        get_qdrant_embeddings_manager,
    )
    from services.seeding.seeding_service import SeedingService
    from services.seeding.seeding_status import SeedingStatus

    manager = get_qdrant_embeddings_manager(settings)
    await manager.start()
    try:
        vorher = await manager.count()
        if vorher:
            raise RuntimeError(
                f"Sammlung {settings.qdrant_collection} hat schon {vorher} Eintraege"
            )
        dienst = SeedingService(settings, manager, metadaten_pfad)
        await dienst.start_seeding()
        stand = await dienst.get_progress()
        if stand.status is not SeedingStatus.COMPLETED:
            raise RuntimeError(f"Seeding endete mit {stand.status.value}")
        return await manager.count()
    finally:
        await manager.shutdown()


def main(argv: Optional[Sequence[str]] = None) -> int:
    from core.logging import LoggingConfig, initialize_logging

    initialize_logging(LoggingConfig(level="WARNING", enable_console_utf8=False))
    with tempfile.TemporaryDirectory() as metadaten:
        try:
            anzahl = asyncio.run(seed_laden(metadaten))
        except RuntimeError as fehler:
            print(f"Seed nicht geladen: {fehler}", file=sys.stderr)
            return 1
    print(f"Seed geladen: {anzahl} Eintraege")
    return 0


if __name__ == "__main__":
    sys.exit(main())
