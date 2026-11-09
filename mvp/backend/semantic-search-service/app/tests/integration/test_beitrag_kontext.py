"""
Rueckwaertssuche Beitrag -> Aussage gegen echtes Qdrant (#603).

Das Payload-Feld antwort_ids muss bei jedem Schreiben der Antwortvorschlaege
mitgehen (Verknuepfen, endgueltig Entfernen) und mit dem Keyword-Index filterbar
sein; der Nachtrag fuellt es fuer den Altbestand. Ob Qdrant ueber eine Liste von
Texten mit MatchValue filtert, zeigt erst dieser Test.
"""

import uuid

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.statement import Statement
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.beitrag_kontext import kontext_laden
from services.content.statement_service import StatementService
from services.wartung.antwort_ids_nachtrag import nachtragen
from tests.integration.beitrag_helfer import post_beitrag
from tests.integration.conftest import requires_qdrant
from utils.antwort_ids import FELD_ANTWORT_IDS

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


@pytest.fixture
def statement_service(integration_settings, real_repository_factory):
    return StatementService(
        integration_settings, repository_factory=real_repository_factory
    )


@pytest.fixture
def post_service(integration_settings, real_repository_factory):
    return create_content_service(
        REGISTRY[ContentType.POST], integration_settings, real_repository_factory
    )


async def _aussage(service, text):
    _, statement_id, _ = await service.add_statement(
        Statement(text=text, replysuggestions=[]),
        "person-1",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )
    return statement_id


async def _post(post_service):
    post_id = uuid.uuid4()
    await post_service._upsert(post_beitrag(post_id))
    return post_id


async def _verknuepfen(service, beitrag_id, statement_id, relevanz=1.0):
    await service.beitrag_als_antwort_verknuepfen(
        beitrag_id, ContentType.POST, relevanz, "person-1", statement_id
    )


async def test_verknuepfen_schreibt_antwort_ids_und_findet_die_aussage(
    statement_service, post_service, real_embeddings_manager
):
    statement_id = await _aussage(statement_service, "Ein Tempolimit bringt nichts")
    andere = await _aussage(statement_service, "Windräder töten Vögel")
    beitrag = await _post(post_service)

    await _verknuepfen(statement_service, beitrag, statement_id)

    punkt = await real_embeddings_manager.get_by_id(str(statement_id))
    assert punkt[FELD_ANTWORT_IDS] == [str(beitrag)]
    gefunden = await statement_service.zu_antwort(beitrag)
    assert [a.id for a in gefunden] == [statement_id]
    assert andere not in [a.id for a in gefunden]


async def test_kontext_mit_weiteren_sichtbaren_antworten(
    statement_service, post_service
):
    statement_id = await _aussage(statement_service, "Tempo 130 reicht völlig")
    beitrag, weitere, gesperrt = (
        await _post(post_service),
        await _post(post_service),
        await _post(post_service),
    )
    for b in (beitrag, weitere, gesperrt):
        await _verknuepfen(statement_service, b, statement_id)
    await post_service._repository.update_status(gesperrt, ContentStatus.BLOCKED)

    kontext = await kontext_laden(beitrag, statement_service)

    assert kontext.aussage.id == statement_id
    assert kontext.aussage.text == "Tempo 130 reicht völlig"
    assert [w.id for w in kontext.weitere_antworten] == [weitere]
    assert kontext.weitere_antworten[0].content_type is ContentType.POST
    assert kontext.weitere_antworten[0].titel == "Tempolimit"


async def test_gesperrte_aussage_wird_nicht_gezeigt(statement_service, post_service):
    statement_id = await _aussage(statement_service, "Elektroautos brennen ständig")
    beitrag = await _post(post_service)
    await _verknuepfen(statement_service, beitrag, statement_id)
    await statement_service._repository.update_status(
        statement_id, ContentStatus.BLOCKED
    )

    assert await statement_service.zu_antwort(beitrag) == []


async def test_endgueltig_entfernen_nimmt_die_id_mit(
    statement_service, post_service, real_embeddings_manager
):
    statement_id = await _aussage(statement_service, "Heizungsgesetz verbietet alles")
    beitrag, bleibt = await _post(post_service), await _post(post_service)
    await _verknuepfen(statement_service, beitrag, statement_id)
    await _verknuepfen(statement_service, bleibt, statement_id)

    await QdrantModerationRepository(
        embeddings_manager=real_embeddings_manager
    ).aus_aussagen_entfernen(str(beitrag))

    punkt = await real_embeddings_manager.get_by_id(str(statement_id))
    assert punkt[FELD_ANTWORT_IDS] == [str(bleibt)]
    assert await statement_service.zu_antwort(beitrag) == []


async def test_nachtrag_fuellt_altbestand_und_ist_idempotent(
    statement_service, post_service, real_embeddings_manager, integration_settings
):
    statement_id = await _aussage(statement_service, "Bahnfahren ist immer teurer")
    beitrag = await _post(post_service)
    await _verknuepfen(statement_service, beitrag, statement_id)
    # Altbestand nachstellen: Aussage ohne das Feld.
    client = real_embeddings_manager.client
    collection = integration_settings.qdrant_collection
    client.delete_payload(
        collection_name=collection, keys=[FELD_ANTWORT_IDS], points=[str(statement_id)]
    )
    assert await statement_service.zu_antwort(beitrag) == []

    trocken = nachtragen(client, collection)
    assert trocken.nachzutragen >= 1 and trocken.nachgetragen == 0
    assert await statement_service.zu_antwort(beitrag) == []

    bericht = nachtragen(client, collection, ausfuehren=True)
    assert bericht.nachgetragen == bericht.nachzutragen >= 1
    assert bericht.index_nachher
    assert [a.id for a in await statement_service.zu_antwort(beitrag)] == [statement_id]

    assert nachtragen(client, collection, ausfuehren=True).nachzutragen == 0


async def test_index_auf_antwort_ids_liegt_an(
    real_embeddings_manager, integration_settings
):
    schema = (
        real_embeddings_manager.client.get_collection(
            integration_settings.qdrant_collection
        ).payload_schema
        or {}
    )
    assert FELD_ANTWORT_IDS in schema
