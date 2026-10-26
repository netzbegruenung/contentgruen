"""
Der Autor loescht seinen Beitrag, gegen echtes Qdrant (#250).

Die Unit-Tests pruefen den Service gegen den Speicher-Modus; hier zeigt sich, dass die
vorhandenen Filter der Repositories einen geloeschten Beitrag ueberall ausblenden: in
Suche, Einzelansicht, Listen, Zaehlern, "Meine Beitraege" und Antwortvorschlaegen.
Gespeichert bleibt er trotzdem.
"""

import uuid

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from services.content.beitrag_loeschen_service import (
    BeitragLoeschenService,
    LoeschErgebnis,
)
from tests.integration.conftest import requires_qdrant
from tests.integration.test_sperren import _antwortvorschlaege, _post

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
def loeschen(inhalte):
    return BeitragLoeschenService(inhalte)


async def test_geloeschter_beitrag_fehlt_ueberall(
    post_service, inhalte, loeschen, real_embeddings_manager
):
    post_id = uuid.uuid4()
    await post_service._upsert(_post(post_id))
    vorher = await post_service.count()

    assert await loeschen.loeschen(post_id, AUTOR) is LoeschErgebnis.GELOESCHT

    assert await post_service.count() == vorher - 1
    with pytest.raises(ValueError):
        await post_service.get(post_id)
    treffer = await post_service.search("Tempolimit Autobahn", limit=5)
    assert post_id not in [t.id for t in treffer]
    assert post_id not in [b.id for b in await post_service.get_all(limit=10, offset=0)]
    assert await _antwortvorschlaege(post_service, post_id) == []
    assert await inhalte.getByAuthor(user_id=AUTOR, limit=10, offset=0) == []
    assert await inhalte.getCountByAuthor(user_id=AUTOR) == 0
    # Gespeichert bleibt er: Verknuepfungen und Stimmen zeigen nicht ins Leere.
    punkt = await real_embeddings_manager.get_by_id(str(post_id))
    assert punkt["status"] == ContentStatus.DELETED.value
    assert punkt["text"] == _post(post_id).text


async def test_fremder_beitrag_bleibt_sichtbar(post_service, loeschen):
    post_id = uuid.uuid4()
    await post_service._upsert(_post(post_id))

    assert await loeschen.loeschen(post_id, "andere") is LoeschErgebnis.NICHT_AUTOR

    assert (await post_service.get(post_id)).status == ContentStatus.VISIBLE
