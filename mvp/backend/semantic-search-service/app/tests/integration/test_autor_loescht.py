"""
Der Autor loescht seinen Beitrag, gegen echtes Qdrant (#250).

Die Unit-Tests pruefen den Service gegen den Speicher-Modus; hier zeigt sich, dass die
vorhandenen Filter der Repositories einen geloeschten Beitrag ueberall ausblenden: in
Suche, Einzelansicht, Listen, Zaehlern, "Meine Beitraege" und Antwortvorschlaegen.
Gespeichert bleibt er trotzdem. Nur die Verweise der Aussagen auf ihn gehen weg (#294).
"""

import json
import uuid

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_status import AUSGEBLENDET, ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.content_type import ContentType
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.content.beitrag_loeschen_service import (
    BeitragLoeschenService,
    LoeschErgebnis,
)
from tests.integration.conftest import requires_qdrant
from tests.integration.beitrag_helfer import antwortvorschlaege, post_beitrag

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

AUTOR = "autor-1"


@pytest.fixture
def post_service(integration_settings, real_repository_factory):
    return create_content_service(
        REGISTRY[ContentType.POST], integration_settings, real_repository_factory
    )


@pytest.fixture
def inhalte(integration_settings, real_repository_factory):
    """Das aggregierte Repository, aus dem "Meine Beitraege" liest."""
    return real_repository_factory.create_content_repository(integration_settings)


@pytest.fixture
def loeschen(inhalte, real_embeddings_manager):
    return BeitragLoeschenService(
        inhalte, QdrantModerationRepository(embeddings_manager=real_embeddings_manager)
    )


async def test_loeschen_beitrag_fehlt_ueberall_bleibt_gespeichert(
    post_service, inhalte, loeschen, real_embeddings_manager
):
    post_id = uuid.uuid4()
    await post_service._upsert(post_beitrag(post_id))
    vorher = await post_service.count()

    assert await loeschen.loeschen(post_id, AUTOR) is LoeschErgebnis.GELOESCHT

    assert await post_service.count() == vorher - 1
    with pytest.raises(ValueError):
        await post_service.get(post_id)
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id not in [t.id for t in treffer]
    assert post_id not in [b.id for b in await post_service.get_all(limit=10, offset=0)]
    assert await antwortvorschlaege(post_service, post_id) == []
    assert await inhalte.getByAuthor(user_id=AUTOR, limit=10, offset=0) == []
    assert await inhalte.getCountByAuthor(user_id=AUTOR) == 0
    # Gespeichert bleibt er: Verknuepfungen und Stimmen zeigen nicht ins Leere.
    punkt = await real_embeddings_manager.get_by_id(str(post_id))
    assert punkt["status"] == ContentStatus.DELETED.value
    assert punkt["text"] == post_beitrag(post_id).text


async def test_loeschen_fremder_beitrag_bleibt_sichtbar(post_service, loeschen):
    post_id = uuid.uuid4()
    await post_service._upsert(post_beitrag(post_id))

    assert await loeschen.loeschen(post_id, "andere") is LoeschErgebnis.NICHT_AUTOR

    assert (await post_service.get(post_id)).status == ContentStatus.VISIBLE


async def test_update_status_nicht_aus_laesst_sperre_stehen(
    post_service, inhalte, real_embeddings_manager
):
    """Der Ausschluss, mit dem das Loeschen eine Sperre zwischen Lesen und Schreiben
    schuetzt, wertet Qdrant im selben Schreibvorgang aus."""
    gesperrt, sichtbar = uuid.uuid4(), uuid.uuid4()
    await post_service._upsert(post_beitrag(gesperrt))
    await post_service._upsert(post_beitrag(sichtbar))
    await inhalte.update_status(gesperrt, ContentStatus.BLOCKED)

    for item_id in (gesperrt, sichtbar):
        await inhalte.update_status(
            item_id, ContentStatus.DELETED, nicht_aus=AUSGEBLENDET
        )

    async def status(item_id):
        return (await real_embeddings_manager.get_by_id(str(item_id)))["status"]

    assert await status(gesperrt) == ContentStatus.BLOCKED.value
    assert await status(sichtbar) == ContentStatus.DELETED.value


async def test_loeschen_einziger_beitrag_aussage_zaehlt_nicht_mehr_als_beantwortet(
    post_service,
    loeschen,
    integration_settings,
    real_repository_factory,
    real_embeddings_manager,
):
    """
    Startseitenzaehler (statement_count, count_curated): Eine Aussage aus einer
    Suchanfrage zaehlt nur mit, solange sie einen Beitrag hat (#294).
    """
    from qdrant_client.models import PointStruct

    manager = real_embeddings_manager
    aussagen = real_repository_factory.create_statement_repository(integration_settings)
    post_id, aussage_id = uuid.uuid4(), str(uuid.uuid4())
    await post_service._upsert(post_beitrag(post_id))
    sammlung = await manager.async_client.get_collection(manager.collection_name)
    await manager.async_client.upsert(
        collection_name=manager.collection_name,
        points=[
            PointStruct(
                id=aussage_id,
                vector=[0.1] * sammlung.config.params.vectors.size,
                payload={
                    "content_type": ContentType.STATEMENT.value,
                    "text": "Bringt ein Tempolimit etwas?",
                    "origin": ContentOrigin.SEARCH_QUERY.value,
                    "status": ContentStatus.VISIBLE.value,
                    "replysuggestions": json.dumps([{"id": str(post_id)}]),
                    "replysuggestions_count": 1,
                },
            )
        ],
        wait=True,
    )
    vorher = await aussagen.count_curated()

    assert await loeschen.loeschen(post_id, AUTOR) is LoeschErgebnis.GELOESCHT

    assert await aussagen.count_curated() == vorher - 1
    aussage = await manager.get_by_id(aussage_id)
    assert json.loads(aussage["replysuggestions"]) == []
