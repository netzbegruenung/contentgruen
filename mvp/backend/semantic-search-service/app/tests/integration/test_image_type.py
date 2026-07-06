"""
Image content type end-to-end gate against REAL Qdrant.

Mirrors the structure of test_post_type.py (rung-1 step-6 gate) for the
rung-2 Image type. Verifies:

* test_image_roundtrip_phase_a -- caption provided at creation time (Phase A):
  entry stored as APPROVED, all Image-specific fields survive the round-trip,
  and the image is semantically searchable.

* test_image_roundtrip_phase_b -- no caption (Phase B): entry stored as
  PENDING_DESCRIPTION with text=None; the item is retrievable by id even before
  the AI description worker fills it.

* test_image_phase_b_to_phase_a_update -- updating an existing Phase-B entry
  with a caption (simulating the background worker result) makes the image
  searchable.

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
    status: ContentStatus = ContentStatus.APPROVED,
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


async def test_image_roundtrip_phase_a(integration_settings, real_repository_factory):
    """Phase A: caption provided — entry stored, searchable, fields preserved."""
    spec = REGISTRY[ContentType.IMAGE]
    service = create_content_service(spec, integration_settings, real_repository_factory)

    item_id = uuid.uuid4()
    entry = _make_image_entry(
        item_id,
        title="Windkraft Niedersachsen",
        image_url="https://example.com/wind.jpg",
        text="Windräder auf einer grünen Wiese in Niedersachsen bei Sonnenuntergang",
        status=ContentStatus.APPROVED,
    )

    stored_id = await service._upsert(entry)
    assert stored_id == item_id

    fetched = await service.get(item_id)
    assert fetched.id == item_id
    assert fetched.content_type == ContentType.IMAGE
    assert fetched.title == "Windkraft Niedersachsen"
    assert fetched.image_url == "https://example.com/wind.jpg"
    assert fetched.text == "Windräder auf einer grünen Wiese in Niedersachsen bei Sonnenuntergang"
    assert fetched.description_model is None
    assert fetched.status == ContentStatus.APPROVED

    hits = await service.search("Windräder Niedersachsen", limit=5)
    assert any(h.id == item_id for h in hits)


async def test_image_roundtrip_phase_b(integration_settings, real_repository_factory):
    """Phase B: no caption — entry stored as PENDING_DESCRIPTION, retrievable by id."""
    spec = REGISTRY[ContentType.IMAGE]
    service = create_content_service(spec, integration_settings, real_repository_factory)

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

    fetched = await service.get(item_id)
    assert fetched.id == item_id
    assert fetched.content_type == ContentType.IMAGE
    assert fetched.title == "Unbekannte Klimademo"
    assert fetched.image_url == "https://example.com/unknown.jpg"
    assert fetched.text is None
    assert fetched.status == ContentStatus.PENDING_DESCRIPTION

    # PENDING_DESCRIPTION items must never appear in search results (status filter gate)
    hits = await service.search("Unbekannte Klimademo", limit=10)
    assert not any(h.id == item_id for h in hits)


async def test_image_phase_b_to_phase_a_update(
    integration_settings, real_repository_factory
):
    """Simulates the AI worker filling in a caption for a PENDING_DESCRIPTION image."""
    spec = REGISTRY[ContentType.IMAGE]
    service = create_content_service(spec, integration_settings, real_repository_factory)

    item_id = uuid.uuid4()
    phase_b_entry = _make_image_entry(
        item_id,
        title="Solaranlage Dachfläche",
        image_url="https://example.com/solar.jpg",
        text=None,
        status=ContentStatus.PENDING_DESCRIPTION,
    )
    await service._upsert(phase_b_entry)

    # Simulate worker: fill caption and promote to PENDING_REVIEW
    now = datetime.datetime.now()
    phase_a_entry = ImageDbEntry(
        **{
            **phase_b_entry.model_dump(),
            "text": "Solarmodule auf dem Dach eines Gemeindezentrums in Bayern",
            "description_model": "gpt-4o",
            "status": ContentStatus.APPROVED,
            "last_modified": now,
        }
    )
    await service._upsert(phase_a_entry)

    fetched = await service.get(item_id)
    assert fetched.text == "Solarmodule auf dem Dach eines Gemeindezentrums in Bayern"
    assert fetched.description_model == "gpt-4o"
    assert fetched.status == ContentStatus.APPROVED

    hits = await service.search("Solarmodule Gemeindezentrum", limit=5)
    assert any(h.id == item_id for h in hits)
