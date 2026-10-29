"""
Zweck und Stil am Kommentar (#357), gegen echtes Qdrant.

* Zweck und Stil kommen nach dem Speichern so wieder an.
* Bei Aussagen stehen Kommentare fuer die Kommentarspalte vor denen fuer die eigenen Leute,
  auch wenn diese besser bewertet sind.
"""

import uuid

import pytest

from domain.models.commentary import Commentary, Stil, Zweck, fuer_eigene_leute
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from dtos.search import CommentarySearchResult as KommentarTrefferWrapper
from services.content.commentary_service import CommentaryService
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from tests.integration.conftest import requires_qdrant
from tests.integration.test_post_type import _FakeReply, _FakeStatement

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


async def _speichern(service, text, **angaben) -> uuid.UUID:
    _, kommentar_id, _ = await service.add_commentary(
        Commentary(
            text=text,
            title="Die Waermepumpe gewinnt beim Rechnen",
            references=[],
            **angaben,
        ),
        author="tester",
        status=ContentStatus.VISIBLE,
        origin=ContentOrigin.MANUALLY_CREATED,
    )
    return kommentar_id


async def test_zweck_und_stil_ueberstehen_das_speichern(
    integration_settings, real_repository_factory
):
    service = CommentaryService(integration_settings, real_repository_factory)
    text = f"Wer die Heizoelrechnung kennt, rechnet gern nach. {uuid.uuid4()}"

    kommentar_id = await _speichern(
        service, text, zweck=Zweck.EIGENE_LEUTE, style=Stil.BISSIG
    )

    gelesen = await service.get(kommentar_id)
    assert (gelesen.zweck, gelesen.style) == (Zweck.EIGENE_LEUTE, Stil.BISSIG)


async def test_kommentare_fuer_die_kommentarspalte_zuerst(
    integration_settings, real_repository_factory
):
    service = CommentaryService(integration_settings, real_repository_factory)
    eigene_id = await _speichern(
        service,
        f"Unter uns: Die Pumpe rechnet sich, und das Oel nicht. {uuid.uuid4()}",
        zweck=Zweck.EIGENE_LEUTE,
        style=Stil.HUMORVOLL,
    )
    spalte_id = await _speichern(
        service,
        f"Mit Foerderung rechnet sich die Pumpe nach wenigen Jahren. {uuid.uuid4()}",
        style=Stil.SACHLICH,
    )
    orchestrator = SearchOrchestrator(
        [
            ContentTypeSearchSpec(
                content_type=ContentType.COMMENTARY,
                service=service,
                result_cls=KommentarTrefferWrapper,
                result_field="commentary_result",
                nachrangig=fuer_eigene_leute,
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )
    aussage = _FakeStatement(
        stmt_id=uuid.uuid4(),
        text="Waermepumpen sind zu teuer",
        score=1.0,
        replysuggestions=[
            _FakeReply(eigene_id, ContentType.COMMENTARY, relevance=1.0),
            _FakeReply(spalte_id, ContentType.COMMENTARY, relevance=0.9),
        ],
    )

    await orchestrator.collect_statement_based([aussage], limit=5, polarity_metadata={})
    orchestrator.sort_and_truncate(5)

    treffer = orchestrator.results_for(ContentType.COMMENTARY)
    assert [t.commentary_result.id for t in treffer] == [spalte_id, eigene_id]
    assert treffer[0].score < treffer[1].score
