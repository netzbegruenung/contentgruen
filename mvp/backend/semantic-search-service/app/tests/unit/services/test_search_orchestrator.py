"""
enrich_with_usage schreibt usage_count in jedes Suchergebnis, egal welcher Typ.

Regression: ImageDbEntry und PostDbEntry kannten das Feld nicht. Sobald ein Bild oder
ein Post im Index lag, warf Pydantic beim Setzen einen ValueError und
/searchByText antwortete mit 500.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.models.commentary import Zweck, fuer_eigene_leute
from domain.models.content_type import ContentType
from domain.models.image import ImageSearchResult
from domain.models.post import PostSearchResult
from dtos.search import PostSearchResult as PostSearchResultDto
from services.polarity_filter_service import PolarityFilterResult
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
@pytest.mark.parametrize(
    "schwelle, erwartet",
    [(None, ["ueber"]), (0.7, ["ueber", "darunter"])],
    ids=["schwelle-der-suche", "schwelle-des-suchtestsets"],
)
async def test_schwelle_entscheidet_ueber_die_aufnahme(schwelle, erwartet):
    """
    Ohne Angabe gilt MINIMUM_SCORE_THRESHOLD wie in der Suche; das Suchtestset
    misst auch andere Schwellen (#346). Beide Wege, ueber die Aussage
    (kombinierter Score) und direkt (Rohscore), pruefen dieselbe Schwelle.
    """
    post = _post()
    service = MagicMock()
    service.get = AsyncMock(return_value=post)
    aussage = SimpleNamespace(
        id=uuid.uuid4(),
        text="Solarparks verschandeln die Landschaft",
        score=0.75,
        replysuggestions=[
            SimpleNamespace(id=post.id, content_type=ContentType.POST, relevance=0.75)
        ],
    )
    kwargs = {} if schwelle is None else {"schwelle": schwelle}
    orchestrator = SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(
                ContentType.POST, service, PostSearchResultDto, "post_result"
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
        **kwargs,
    )
    direkt_ueber, direkt_darunter = _post(), _post()
    direkt_ueber.title, direkt_darunter.title = "ueber", "darunter"
    direkt_ueber.score, direkt_darunter.score = 0.85, 0.75

    await orchestrator.collect_statement_based([aussage], 10, {})
    with patch(
        "services.search.search_orchestrator.BaseContentService.search_batch",
        AsyncMock(return_value=[[direkt_ueber, direkt_darunter]]),
    ):
        await orchestrator.collect_direct("Solarpark", 10)

    treffer = orchestrator.results_for(ContentType.POST)
    ueber_aussage = [t for t in treffer if t.statement_id is not None]
    assert len(ueber_aussage) == (0 if schwelle is None else 1)
    assert [t.post_result.title for t in treffer if t.statement_id is None] == erwartet


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ausschliessen, erwartet",
    [(False, ["antwort", "fremd"]), (True, ["fremd"])],
    ids=["ohne-widerspruch", "widerspruch-nach-nli"],
)
async def test_antworten_einer_widersprechenden_aussage_kommen_nicht_direkt(
    ausschliessen, erwartet
):
    """
    #574: Straft das NLI-Modell eine Aussage als Gegenteil der Suchanfrage, kommen
    ihre Antworten auch nicht ueber den direkten Weg zurueck; andere direkte Treffer
    bleiben.
    """
    antwort, fremd = _post(), _post()
    antwort.title, fremd.title = "antwort", "fremd"
    antwort.score, fremd.score = 0.9, 0.88
    service = MagicMock()
    service.get = AsyncMock(return_value=antwort)
    aussage = SimpleNamespace(
        id=uuid.uuid4(),
        text="Windräder töten Vögel",
        score=0.3,  # gestraft: ueber die Aussage faellt die Antwort weg
        replysuggestions=[
            SimpleNamespace(id=antwort.id, content_type=ContentType.POST, relevance=1)
        ],
    )
    polaritaet = {
        aussage.id: PolarityFilterResult(
            original_score=0.95,
            adjusted_score=0.3,
            polarity_penalty_applied=0.32,
            polarity_mismatch_detected=True,
            query_polarity="nli",
            result_polarity="widerspruch",
            explanation="",
            antworten_ausschliessen=ausschliessen,
        )
    }
    orchestrator = SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(
                ContentType.POST, service, PostSearchResultDto, "post_result"
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )

    await orchestrator.collect_statement_based([aussage], 10, polaritaet)
    with patch(
        "services.search.search_orchestrator.BaseContentService.search_batch",
        AsyncMock(return_value=[[antwort, fremd]]),
    ):
        await orchestrator.collect_direct("Windräder schützen Vögel", 10)

    treffer = orchestrator.results_for(ContentType.POST)
    assert [t.post_result.title for t in treffer] == erwartet


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


def _kommentar_treffer(score: float, zweck: Zweck, aussage=None) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        statement_id=aussage,
        commentary_result=SimpleNamespace(id=uuid.uuid4(), zweck=zweck),
    )


def _kommentar_orchestrator() -> SearchOrchestrator:
    return SearchOrchestrator(
        specs=[
            ContentTypeSearchSpec(
                ContentType.COMMENTARY,
                None,
                object,
                "commentary_result",
                nachrangig=fuer_eigene_leute,
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )


@pytest.mark.unit
def test_je_aussage_stehen_kommentarspalten_antworten_vor_denen_fuer_die_eigenen_leute():
    """
    Entscheidung zu #357 (Variante B): Umsortiert wird nur innerhalb derselben
    Aussage. Ihre Kommentare fuer die eigenen Leute ruecken direkt hinter ihre
    Kommentare fuer die Kommentarspalte; Treffer anderer Aussagen und Direkttreffer bleiben
    auf ihrem Platz in der Score-Reihenfolge.
    """
    a, b = uuid.uuid4(), uuid.uuid4()
    a_eigene_hoch = _kommentar_treffer(0.97, Zweck.EIGENE_LEUTE, a)
    b_spalte = _kommentar_treffer(0.95, Zweck.KOMMENTARSPALTE, b)
    a_spalte_mittel = _kommentar_treffer(0.93, Zweck.KOMMENTARSPALTE, a)
    a_eigene_mittel = _kommentar_treffer(0.92, Zweck.EIGENE_LEUTE, a)
    b_eigene = _kommentar_treffer(0.91, Zweck.EIGENE_LEUTE, b)
    a_spalte_tief = _kommentar_treffer(0.9, Zweck.KOMMENTARSPALTE, a)
    direkt_eigene = _kommentar_treffer(0.62, Zweck.EIGENE_LEUTE)
    direkt_spalte = _kommentar_treffer(0.61, Zweck.KOMMENTARSPALTE)
    weggeschnitten = _kommentar_treffer(0.5, Zweck.KOMMENTARSPALTE, a)
    orchestrator = _kommentar_orchestrator()
    orchestrator.results_for(ContentType.COMMENTARY).extend(
        [
            direkt_spalte,
            a_spalte_tief,
            weggeschnitten,
            b_eigene,
            a_eigene_hoch,
            direkt_eigene,
            a_spalte_mittel,
            b_spalte,
            a_eigene_mittel,
        ]
    )

    orchestrator.sort_and_truncate(8)

    # Erst nach Score gekuerzt: Die Auswahl bleibt, nur die Reihenfolge je Aussage
    # aendert sich. Aussage A belegt die Plaetze 1, 3, 4 und 6.
    assert orchestrator.results_for(ContentType.COMMENTARY) == [
        a_spalte_mittel,
        b_spalte,
        a_spalte_tief,
        a_eigene_hoch,
        b_eigene,
        a_eigene_mittel,
        direkt_eigene,
        direkt_spalte,
    ]


@pytest.mark.unit
def test_gleicher_score_haelt_die_kommentarspalten_antwort_vorn():
    aussage = uuid.uuid4()
    eigene = _kommentar_treffer(0.9, Zweck.EIGENE_LEUTE, aussage)
    spalte = _kommentar_treffer(0.9, Zweck.KOMMENTARSPALTE, aussage)
    orchestrator = _kommentar_orchestrator()
    orchestrator.results_for(ContentType.COMMENTARY).extend([eigene, spalte])

    orchestrator.sort_and_truncate(5)

    assert orchestrator.results_for(ContentType.COMMENTARY) == [spalte, eigene]
