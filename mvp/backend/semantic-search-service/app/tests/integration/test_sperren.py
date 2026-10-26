"""
Sperren und Entsperren gegen echtes Qdrant.

Die Unit-Tests pruefen die Filter als Objekte; hier zeigt sich, dass Qdrant sie so
auswertet wie gedacht: Ein gesperrter Beitrag fehlt in Suche, Einzelansicht, Zaehlern und
Antwortvorschlaegen und ist nach dem Entsperren wieder da. Die Meldungen
(PostgreSQL) sind gemockt, sie pruefen die Service-Tests.
"""

import datetime
import uuid
from unittest.mock import MagicMock

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.post import PostDbEntry
from dtos.search import PostSearchResult as PostSearchResultWrapper
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.moderation_service import ModerationService
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from tests.integration.conftest import requires_qdrant
from tests.integration.test_post_type import _FakeReply, _FakeStatement

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

TEXT = "Tempolimit auf Autobahnen spart sofort CO2"


def _post(item_id: uuid.UUID) -> PostDbEntry:
    now = datetime.datetime.now()
    return PostDbEntry(
        text=TEXT,
        id=item_id,
        created=now,
        last_modified=now,
        original_author="autor-1",
        last_modified_by="autor-1",
        title="Tempolimit",
        platform="mastodon",
        author="@gruen",
        url="https://social.example/posts/2",
        engagement=1,
        status=ContentStatus.APPROVED,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


@pytest.fixture
def post_service(integration_settings, real_repository_factory):
    return create_content_service(
        REGISTRY[ContentType.POST], integration_settings, real_repository_factory
    )


@pytest.fixture
def moderation(real_embeddings_manager):
    return ModerationService(
        report_repo=MagicMock(),
        moderation_repo=QdrantModerationRepository(
            embeddings_manager=real_embeddings_manager
        ),
    )


async def _antwortvorschlaege(post_service, post_id):
    orchestrator = SearchOrchestrator(
        [
            ContentTypeSearchSpec(
                content_type=ContentType.POST,
                service=post_service,
                result_cls=PostSearchResultWrapper,
                result_field="post_result",
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )
    aussage = _FakeStatement(
        stmt_id=uuid.uuid4(),
        text="Bringt ein Tempolimit etwas?",
        score=1.0,
        replysuggestions=[_FakeReply(post_id, ContentType.POST, relevance=1.0)],
    )
    await orchestrator.collect_statement_based([aussage], limit=5, polarity_metadata={})
    return [r.post_result.id for r in orchestrator.results_for(ContentType.POST)]


async def test_gesperrter_beitrag_fehlt_ueberall(post_service, moderation):
    post_id = uuid.uuid4()
    await post_service._upsert(_post(post_id))
    vorher = await post_service.count()

    assert await moderation.sperren(str(post_id), gesperrt_von="admin-1") is True

    assert await post_service.count() == vorher - 1

    with pytest.raises(ValueError):
        await post_service.get(post_id)
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id not in [t.id for t in treffer]
    assert post_id not in [b.id for b in await post_service.get_all(limit=10, offset=0)]
    assert await _antwortvorschlaege(post_service, post_id) == []
    # Fuer die Moderation bleibt er auffindbar, auch ohne Meldung.
    assert await moderation.content_exists(str(post_id)) is True
    gesperrte = [b["id"] for b in await moderation.gesperrte_beitraege()]
    assert str(post_id) in gesperrte


async def test_entsperrter_beitrag_ist_wieder_da(post_service, moderation):
    post_id = uuid.uuid4()
    await post_service._upsert(_post(post_id))
    await moderation.sperren(str(post_id), gesperrt_von="admin-1")

    assert await moderation.entsperren(str(post_id), entsperrt_von="admin-1") is True

    beitrag = await post_service.get(post_id)
    assert beitrag.status == ContentStatus.APPROVED
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id in [t.id for t in treffer]
    assert await _antwortvorschlaege(post_service, post_id) == [post_id]
