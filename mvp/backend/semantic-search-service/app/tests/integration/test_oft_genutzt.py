"""
"Diese Woche oft genutzt" (#364) gegen echtes Qdrant: Der Lader liefert sichtbare
Beitraege mit allen Feldern ihres Typs und laesst gesperrte und unbekannte weg.
Die Nutzungsabfrage (PostgreSQL) steht als Liste daneben; ihre Auswahl pruefen die
Unit-Tests des Service.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_type import ContentType
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.content.reference_service import ReferenceService
from services.moderation_service import ModerationService
from services.oft_genutzt_service import OftGenutztService, sichtbaren_beitrag_laden
from tests.integration.beitrag_helfer import TEXT, post_beitrag
from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


class _Nutzung:
    def __init__(self, ids):
        self.ids = ids

    def get_trending_content(self, limit=10, hours=24):
        return [
            {"content_id": str(i), "recent_uses": 5, "total_uses": 5} for i in self.ids
        ]


@pytest.fixture
def post_service(integration_settings, real_repository_factory):
    return create_content_service(
        REGISTRY[ContentType.POST], integration_settings, real_repository_factory
    )


async def test_oft_genutzt_zeigt_sichtbare_ohne_gesperrte(
    post_service,
    integration_settings,
    real_repository_factory,
    real_embeddings_manager,
):
    sichtbar = [uuid.uuid4() for _ in range(3)]
    gesperrt = uuid.uuid4()
    for beitrag_id in [*sichtbar, gesperrt]:
        await post_service._upsert(post_beitrag(beitrag_id))
    moderation = ModerationService(
        report_repo=MagicMock(),
        moderation_repo=QdrantModerationRepository(
            embeddings_manager=real_embeddings_manager
        ),
    )
    assert await moderation.sperren(str(gesperrt), gesperrt_von="admin-1") is True

    service = OftGenutztService(
        _Nutzung([sichtbar[0], gesperrt, uuid.uuid4(), *sichtbar[1:]]),
        sichtbaren_beitrag_laden(
            integration_settings,
            real_repository_factory,
            ReferenceService(integration_settings, real_repository_factory),
        ),
    )
    beitraege = await service.beitraege()

    assert [b["id"] for b in beitraege] == sichtbar
    assert {b["result_type"] for b in beitraege} == {"post"}
    # Felder des Typs, nicht nur die gemeinsamen: Die Karte braucht den Link des Posts.
    assert beitraege[0]["text"] == TEXT
    assert beitraege[0]["url"] == "https://social.example/posts/2"
