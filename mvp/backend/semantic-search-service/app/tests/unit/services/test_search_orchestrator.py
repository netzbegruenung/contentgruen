"""
enrich_with_usage schreibt usage_count in jedes Suchergebnis, egal welcher Typ.

Regression: ImageDbEntry und PostDbEntry kannten das Feld nicht. Sobald ein Bild oder
ein Post im Index lag, warf Pydantic beim Setzen einen ValueError und
/searchByText antwortete mit 500.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from domain.models.content_type import ContentType
from domain.models.image import ImageSearchResult
from domain.models.post import PostSearchResult
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
