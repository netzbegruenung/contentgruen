"""
enrich_with_usage schreibt usage_count in jedes Suchergebnis, egal welcher Typ.

Regression: ImageDbEntry und PostDbEntry kannten das Feld nicht. Sobald ein Bild oder
ein Post im Index lag, warf Pydantic beim Setzen einen ValueError und
/searchByText antwortete mit 500.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models.commentary import Zweck
from domain.models.content_type import ContentType
from domain.models.image import ImageSearchResult
from domain.models.post import PostSearchResult
from dtos.search import PostSearchResult as PostSearchResultDto
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from tests.conftest import create_base_content_fields


def _bild() -> ImageSearchResult:
    return ImageSearchResult(
        **create_base_content_fields(),
        id=uuid.uuid4(),
        content_type=ContentType.IMAGE,
        title="Solaranlage auf dem Dach der Grundschule",
        image_url="https://example.org/dach.jpg",
        text="Seit dem Frühjahr erzeugt die Schule mehr Strom, als sie verbraucht.",
    )


def _post() -> PostSearchResult:
    return PostSearchResult(
        **create_base_content_fields(),
        id=uuid.uuid4(),
        content_type=ContentType.POST,
        title="Unser Solarpark ist am Netz",
        text="Heute ist der Bürgersolarpark ans Netz gegangen.",
        platform="mastodon",
        author="@buergerenergie",
    )


@pytest.mark.unit
def test_enrich_with_usage_bild_und_post_ohne_fehler():
    bild, post = _bild(), _post()
    usage_service = MagicMock()
    usage_service.enrich_content_with_usage.side_effect = lambda eintraege: [
        {**eintrag, "usage_count": 3} for eintrag in eintraege
    ]
    orchestrator = SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(ContentType.IMAGE, None, object, "image_result"),
            ContentTypeSearchSpec(ContentType.POST, None, object, "post_result"),
        ],
        reference_service=None,
        usage_service=usage_service,
        voting_service=None,
    )
    orchestrator.results_for(ContentType.IMAGE).append(
        SimpleNamespace(image_result=bild)
    )
    orchestrator.results_for(ContentType.POST).append(SimpleNamespace(post_result=post))

    orchestrator.enrich_with_usage()

    assert bild.usage_count == 3
    assert post.usage_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_treffer_tragen_die_themen_der_aussage_ueber_die_sie_gefunden_wurden():
    """Grundlage des Themenfilters auf der Ergebnisseite (#363)."""
    aussage_id, kommentar_id = uuid.uuid4(), uuid.uuid4()
    aussage = SimpleNamespace(
        id=aussage_id,
        text="Wärmepumpen sind zu teuer",
        score=0.95,
        replysuggestions=[
            SimpleNamespace(
                id=kommentar_id, content_type=ContentType.POST, relevance=0.9
            )
        ],
    )
    post = _post()
    post_service = MagicMock()
    post_service.get = AsyncMock(return_value=post)
    direkt = _post()
    themen_service = MagicMock()
    themen_service.themen_von.return_value = {
        aussage_id: ["energie-heizen", "soziales"]
    }
    orchestrator = SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(
                ContentType.POST, post_service, PostSearchResultDto, "post_result"
            )
        ],
        reference_service=MagicMock(),
        usage_service=None,
        voting_service=None,
    )
    await orchestrator.collect_statement_based([aussage], 10, {})
    orchestrator.results_for(ContentType.POST).append(
        PostSearchResultDto(
            score=0.6,
            statement_text="",
            statement_similarity_score=0.0,
            reply_relevance=0.0,
            post_result=direkt,
        )
    )

    orchestrator.themen_ergaenzen(themen_service)

    ueber_aussage, direkter_treffer = orchestrator.results_for(ContentType.POST)
    assert ueber_aussage.statement_id == aussage_id
    assert [t.schluessel for t in ueber_aussage.themen] == [
        "energie-heizen",
        "soziales",
    ]
    assert direkter_treffer.themen == []
    themen_service.themen_von.assert_called_once_with([aussage_id])


def _kommentar_treffer(score: float, zweck: Zweck) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        commentary_result=SimpleNamespace(id=uuid.uuid4(), zweck=zweck),
    )


@pytest.mark.unit
def test_kommentarspalten_antworten_stehen_vor_denen_fuer_die_eigenen_leute():
    """Bei Aussagen zeigt die Suche zuerst Kommentarspalten-Antworten (#357)."""
    orchestrator = SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(
                ContentType.COMMENTARY, None, object, "commentary_result"
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )
    eigene_hoch = _kommentar_treffer(0.95, Zweck.EIGENE_LEUTE)
    spalte_mittel = _kommentar_treffer(0.9, Zweck.KOMMENTARSPALTE)
    eigene_mittel = _kommentar_treffer(0.88, Zweck.EIGENE_LEUTE)
    spalte_tief = _kommentar_treffer(0.85, Zweck.KOMMENTARSPALTE)
    weggeschnitten = _kommentar_treffer(0.81, Zweck.KOMMENTARSPALTE)
    orchestrator.results_for(ContentType.COMMENTARY).extend(
        [spalte_tief, eigene_mittel, weggeschnitten, eigene_hoch, spalte_mittel]
    )

    orchestrator.sort_and_truncate(4)

    # Erst nach Score gekuerzt: Die Reihenfolge aendert sich, die Auswahl nicht.
    assert orchestrator.results_for(ContentType.COMMENTARY) == [
        spalte_mittel,
        spalte_tief,
        eigene_hoch,
        eigene_mittel,
    ]
