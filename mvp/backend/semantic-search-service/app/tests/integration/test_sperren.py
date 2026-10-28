"""
Sperren und Entsperren gegen echtes Qdrant.

Die Unit-Tests pruefen die Filter als Objekte; hier zeigt sich, dass Qdrant sie so
auswertet wie gedacht: Ein gesperrter Beitrag fehlt in Suche, Einzelansicht, Zaehlern und
Antwortvorschlaegen und ist nach dem Entsperren wieder da. Die Meldungen
(PostgreSQL) sind gemockt, sie pruefen die Service-Tests.
"""

import json
import uuid
from unittest.mock import MagicMock

import pytest

from domain.content_registry import (
    BEITRAGSTYPEN_WERTE,
    REGISTRY,
    create_content_service,
)
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.moderation_service import ModerationService
from tests.integration.conftest import requires_qdrant
from tests.integration.beitrag_helfer import TEXT, antwortvorschlaege, post_beitrag

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


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


async def test_gesperrter_beitrag_fehlt_ueberall(post_service, moderation):
    post_id = uuid.uuid4()
    await post_service._upsert(post_beitrag(post_id))
    vorher = await post_service.count()

    assert await moderation.sperren(str(post_id), gesperrt_von="admin-1") is True

    assert await post_service.count() == vorher - 1

    with pytest.raises(ValueError):
        await post_service.get(post_id)
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id not in [t.id for t in treffer]
    assert post_id not in [b.id for b in await post_service.get_all(limit=10, offset=0)]
    assert await antwortvorschlaege(post_service, post_id) == []
    # Fuer die Moderation bleibt er auffindbar, auch ohne Meldung.
    assert await moderation.content_exists(str(post_id)) is True
    gesperrte = [b["id"] for b in await moderation.gesperrte_beitraege()]
    assert str(post_id) in gesperrte


async def test_entsperrter_beitrag_ist_wieder_da(post_service, moderation):
    post_id = uuid.uuid4()
    await post_service._upsert(post_beitrag(post_id))
    await moderation.sperren(str(post_id), gesperrt_von="admin-1")

    assert await moderation.entsperren(str(post_id)) is True

    beitrag = await post_service.get(post_id)
    assert beitrag.status == ContentStatus.VISIBLE
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id in [t.id for t in treffer]
    assert await antwortvorschlaege(post_service, post_id) == [post_id]


@pytest.mark.parametrize("typ", BEITRAGSTYPEN_WERTE)
async def test_loeschen_entfernt_verweis_aus_aussage(
    real_embeddings_manager, moderation, typ
):
    """
    Fuer jeden Beitragstyp, etwa eine Hintergrundinfo, nicht nur fuer Kommentare (#294).
    Die Kaskade schreibt nur die Antwortvorschlaege; der Vektor der Aussage bleibt.
    Ein upsert ohne Vektor lehnt Qdrant ab.
    """
    from qdrant_client.models import PointStruct

    beitrag_id, aussage_id, andere = (str(uuid.uuid4()) for _ in range(3))
    sammlung = await real_embeddings_manager.async_client.get_collection(
        real_embeddings_manager.collection_name
    )
    groesse = sammlung.config.params.vectors.size
    # Verschiedene Vektoren: Ueberschriebe die Kaskade die Aussage mit dem Vektor des
    # Beitrags, fiele das sonst nicht auf.
    await real_embeddings_manager.async_client.upsert(
        collection_name=real_embeddings_manager.collection_name,
        points=[
            PointStruct(
                id=beitrag_id,
                vector=[0.1] * groesse,
                payload={"content_type": typ, "text": TEXT},
            ),
            PointStruct(
                id=aussage_id,
                vector=[0.1, 0.9] * (groesse // 2) + [0.1] * (groesse % 2),
                payload={
                    "content_type": ContentType.STATEMENT.value,
                    "text": "Bringt ein Tempolimit etwas?",
                    "replysuggestions": json.dumps(
                        [{"id": beitrag_id}, {"id": andere}]
                    ),
                    "replysuggestions_count": 2,
                },
            ),
        ],
        wait=True,
    )
    [vorher] = await real_embeddings_manager.async_client.retrieve(
        collection_name=real_embeddings_manager.collection_name,
        ids=[aussage_id],
        with_vectors=True,
    )

    assert await moderation.delete_content(beitrag_id, typ, deleted_by="admin-1")

    assert await real_embeddings_manager.get_by_id(beitrag_id) is None
    [aussage] = await real_embeddings_manager.async_client.retrieve(
        collection_name=real_embeddings_manager.collection_name,
        ids=[aussage_id],
        with_payload=True,
        with_vectors=True,
    )
    assert json.loads(aussage.payload["replysuggestions"]) == [{"id": andere}]
    assert aussage.payload["replysuggestions_count"] == 1
    assert aussage.vector == vorher.vector
