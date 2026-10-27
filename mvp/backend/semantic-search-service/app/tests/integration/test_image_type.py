"""
Image content type end-to-end gate against REAL Qdrant.

Mirrors the structure of test_post_type.py (rung-1 step-6 gate) for the
rung-2 Image type. Verifies:

* test_image_roundtrip_mit_unterschrift -- Unterschrift given at creation time:
  entry stored as VISIBLE, all Image-specific fields survive the round-trip,
  and the image is semantically searchable.

* test_image_altbestand_ohne_unterschrift -- an entry without Unterschrift from
  before #281 (PENDING_DESCRIPTION, text=None) can still be stored and read by
  the model, but readers never see it: not by id, not in lists, not in search.
  New ones are no longer created (ADR 0003).

All tests auto-skip when Qdrant is not reachable.
"""

import datetime
import uuid

import pytest

from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.image import ImageDbEntry
from domain.models.author_entry import AuthorEntry
from domain.content_registry import REGISTRY, create_content_service

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


def _make_image_entry(
    item_id: uuid.UUID,
    *,
    title: str = "Klimademo Berlin",
    image_url: str = "https://example.com/demo.jpg",
    text: str | None = "Tausende Menschen demonstrieren für Klimaschutz in Berlin",
    description_model: str | None = None,
    status: ContentStatus = ContentStatus.VISIBLE,
) -> ImageDbEntry:
    now = datetime.datetime.now()
    return ImageDbEntry(
        id=item_id,
        title=title,
        image_url=image_url,
        text=text,
        description_model=description_model,
        content_type=ContentType.IMAGE,
        created=now,
        last_modified=now,
        original_author="integration_tester",
        last_modified_by="integration_tester",
        authors=[AuthorEntry(name="integration_tester")],
        status=status,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


async def test_image_roundtrip_mit_unterschrift(
    integration_settings, real_repository_factory
):
    """Mit Unterschrift: gespeichert, auffindbar, Felder bleiben erhalten."""
    spec = REGISTRY[ContentType.IMAGE]
    service = create_content_service(
        spec, integration_settings, real_repository_factory
    )

    item_id = uuid.uuid4()
    entry = _make_image_entry(
        item_id,
        title="Windkraft Niedersachsen",
        image_url="https://example.com/wind.jpg",
        text="Windräder auf einer grünen Wiese in Niedersachsen bei Sonnenuntergang",
        status=ContentStatus.VISIBLE,
    )

    stored_id = await service._upsert(entry)
    assert stored_id == item_id

    fetched = await service.get(item_id)
    assert fetched.id == item_id
    assert fetched.content_type == ContentType.IMAGE
    assert fetched.title == "Windkraft Niedersachsen"
    assert fetched.image_url == "https://example.com/wind.jpg"
    assert (
        fetched.text
        == "Windräder auf einer grünen Wiese in Niedersachsen bei Sonnenuntergang"
    )
    assert fetched.description_model is None
    assert fetched.status == ContentStatus.VISIBLE

    hits = await service.search("Windräder Niedersachsen", limit=5)
    assert any(h.id == item_id for h in hits)


async def test_image_altbestand_ohne_unterschrift(
    integration_settings, real_repository_factory
):
    """Altbestand von vor #281: ohne Unterschrift fuer Leser nicht da."""
    spec = REGISTRY[ContentType.IMAGE]
    service = create_content_service(
        spec, integration_settings, real_repository_factory
    )

    item_id = uuid.uuid4()
    entry = _make_image_entry(
        item_id,
        title="Unbekannte Klimademo",
        image_url="https://example.com/unknown.jpg",
        text=None,
        status=ContentStatus.PENDING_DESCRIPTION,
    )

    stored_id = await service._upsert(entry)
    assert stored_id == item_id

    with pytest.raises(ValueError, match="ausgeblendet"):
        await service.get(item_id)

    liste = await service.get_all(limit=100, offset=0)
    assert not any(e.id == item_id for e in liste)

    hits = await service.search("Unbekannte Klimademo", limit=10)
    assert not any(h.id == item_id for h in hits)
