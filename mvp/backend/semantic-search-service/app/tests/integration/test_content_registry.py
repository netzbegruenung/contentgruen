"""
Step 5 gate: content-type registry parity against REAL Qdrant.

Proves that a generic ``BaseContentService`` instantiated purely from a declarative
``ContentTypeSpec`` behaves identically to the hand-written per-type service it
replaces -- the exact property the mocked unit suite cannot show, because it never
touches real collection wiring. See ``docs/RUNG_1_PLAN.md`` Step 5 + requirement 5.

Each test seeds content through the existing concrete service (the pre-refactor path)
and reads it back through the registry-built generic service (the new path), asserting
the two agree. When the registry is correct, "new type = a spec, no new branch" holds.
"""

import uuid

import pytest

from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.commentary import Commentary
from domain.models.generic_text import GenericText
from services.content.commentary_service import CommentaryService
from services.content.generic_text_service import GenericTextService

# The module under construction (red until Step 5 lands).
from domain.content_registry import REGISTRY, create_content_service

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


@requires_qdrant
async def test_registry_has_specs_for_existing_types():
    """The registry declares the two shipped types with their model classes."""
    for content_type in (ContentType.COMMENTARY, ContentType.GENERIC_TEXT):
        spec = REGISTRY[content_type]
        assert spec.content_type == content_type
        assert spec.db_entry_model is not None
        assert spec.search_result_model is not None


async def test_commentary_roundtrip_parity(integration_settings, real_repository_factory):
    """A commentary written via CommentaryService is readable via the registry service."""
    concrete = CommentaryService(integration_settings, real_repository_factory)
    item_id = uuid.uuid4()
    ok, returned_id, _ = await concrete.add_commentary(
        Commentary(text="Klimaschutz ist sozial gerecht", title="Klima", references=[]),
        author="tester",
        status=ContentStatus.APPROVED,
        origin=ContentOrigin.MANUALLY_CREATED,
        id=item_id,
    )
    assert ok and returned_id == item_id

    spec = REGISTRY[ContentType.COMMENTARY]
    generic = create_content_service(spec, integration_settings, real_repository_factory)

    fetched = await generic.get(item_id)
    assert fetched is not None
    assert fetched.id == item_id
    assert fetched.title == "Klima"
    assert fetched.content_type == ContentType.COMMENTARY

    hits = await generic.search("soziale Gerechtigkeit", limit=5)
    assert any(h.id == item_id for h in hits)


async def test_generic_text_roundtrip_parity(integration_settings, real_repository_factory):
    """A generic_text written via GenericTextService is readable via the registry service."""
    concrete = GenericTextService(integration_settings, real_repository_factory)
    item_id = uuid.uuid4()
    ok, returned_id, _ = await concrete.add_generic_text(
        GenericText(text="Verkehrswende jetzt", title="Verkehr", references=[]),
        author="tester",
        status=ContentStatus.APPROVED,
        origin=ContentOrigin.MANUALLY_CREATED,
        id=item_id,
    )
    assert ok and returned_id == item_id

    spec = REGISTRY[ContentType.GENERIC_TEXT]
    generic = create_content_service(spec, integration_settings, real_repository_factory)

    fetched = await generic.get(item_id)
    assert fetched is not None
    assert fetched.id == item_id
    assert fetched.title == "Verkehr"
    assert fetched.content_type == ContentType.GENERIC_TEXT
