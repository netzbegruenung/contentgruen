"""
Bildbeschreibung und Sperre gegen echtes Qdrant (#251).

Der Hintergrunddienst fuer Bildbeschreibungen braucht Sekunden pro Bild. Sperrt ein
Admin das Bild in dieser Zeit, darf das Ergebnis des Dienstes die Sperre nicht
aufheben. Hier laeuft der echte Worker gegen echtes Qdrant; die Sperre setzt der
echte ModerationService, waehrend die (gemockte) Vision-KI "rechnet". Die Meldungen
(PostgreSQL) sind gemockt, sie pruefen die Service-Tests.
"""

import asyncio
import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.content_registry import REGISTRY, create_content_service
from domain.models.author_entry import AuthorEntry
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import NEW_CONTENT_STATUS, ContentStatus
from domain.models.content_type import ContentType
from domain.models.image import ImageDbEntry
from services.moderation_service import FELD_STATUS_VOR_SPERRE, ModerationService
from services.vision.image_description_worker import _description_worker
from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

UNTERSCHRIFT = "Windräder auf einem Hügel in Niedersachsen bei Sonnenuntergang"


def _wartendes_bild(item_id: uuid.UUID) -> ImageDbEntry:
    now = datetime.datetime.now()
    return ImageDbEntry(
        id=item_id,
        title="Windpark",
        image_url="https://example.com/windpark.jpg",
        text=None,
        content_type=ContentType.IMAGE,
        created=now,
        last_modified=now,
        original_author="autor-1",
        last_modified_by="autor-1",
        authors=[AuthorEntry(name="autor-1")],
        status=ContentStatus.PENDING_DESCRIPTION,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


def _ergebnis(text: str):
    ergebnis = MagicMock()
    ergebnis.text = text
    ergebnis.extra = {"description_model": "gpt-4o"}
    return ergebnis


@pytest.fixture
def image_service(integration_settings, real_repository_factory):
    return create_content_service(
        REGISTRY[ContentType.IMAGE], integration_settings, real_repository_factory
    )


@pytest.fixture
def moderation(real_embeddings_manager):
    with patch(
        "services.moderation_service.get_content_report_repository",
        return_value=MagicMock(),
    ), patch(
        "services.moderation_service.get_embeddings_manager",
        return_value=real_embeddings_manager,
    ):
        yield ModerationService()


async def _ein_durchlauf(image_service, ingestion_strategy):
    """Den Worker genau einen Durchlauf machen lassen (das erste sleep beendet ihn)."""

    async def abbrechen(_sekunden):
        raise asyncio.CancelledError

    with patch("services.vision.image_description_worker.asyncio.sleep", abbrechen):
        with pytest.raises(asyncio.CancelledError):
            await _description_worker(image_service, ingestion_strategy)


def _sperrt_waehrend_beschreibung(moderation, item_id, ergebnis):
    """Vision-KI, die waehrend des Aufrufs einen Admin das Bild sperren laesst."""

    async def beschreiben(_eingabe):
        assert await moderation.sperren(str(item_id), "admin-1")
        if isinstance(ergebnis, Exception):
            raise ergebnis
        return ergebnis

    strategie = MagicMock()
    strategie.derive_text = AsyncMock(side_effect=beschreiben)
    return strategie


async def test_bild_wird_ohne_sperre_mit_unterschrift_sichtbar(
    image_service, real_embeddings_manager
):
    """Gegenprobe: ohne Sperre traegt der Worker die Unterschrift ein und gibt frei."""
    item_id = uuid.uuid4()
    await image_service.add(_wartendes_bild(item_id))
    strategie = MagicMock()
    strategie.derive_text = AsyncMock(return_value=_ergebnis(UNTERSCHRIFT))

    await _ein_durchlauf(image_service, strategie)

    bild = await image_service.get(item_id)
    assert bild.status == NEW_CONTENT_STATUS
    assert bild.text == UNTERSCHRIFT
    assert bild.description_model == "gpt-4o"
    treffer = await image_service.search("Windräder Niedersachsen", limit=5)
    assert any(t.id == item_id for t in treffer)


async def test_waehrend_beschreibung_gesperrtes_bild_bleibt_gesperrt(
    image_service, moderation, real_embeddings_manager
):
    item_id = uuid.uuid4()
    await image_service.add(_wartendes_bild(item_id))
    strategie = _sperrt_waehrend_beschreibung(
        moderation, item_id, _ergebnis(UNTERSCHRIFT)
    )

    await _ein_durchlauf(image_service, strategie)

    payload = await real_embeddings_manager.get_by_id(str(item_id))
    assert payload["status"] == ContentStatus.BLOCKED.value
    assert payload[FELD_STATUS_VOR_SPERRE] == ContentStatus.PENDING_DESCRIPTION.value
    # Die Beschreibung selbst ist eingetragen; nur Zustand und Sperre bleiben.
    assert payload["text"] == UNTERSCHRIFT
    assert payload["description_model"] == "gpt-4o"
    treffer = await image_service.search("Windräder Niedersachsen", limit=5)
    assert all(t.id != item_id for t in treffer)

    # Entsperren stellt den Zustand von vor der Sperre her; der Worker gibt das
    # Bild danach im naechsten Durchlauf frei.
    assert await moderation.entsperren(str(item_id), "admin-1")
    payload = await real_embeddings_manager.get_by_id(str(item_id))
    assert payload["status"] == ContentStatus.PENDING_DESCRIPTION.value


async def test_fehlschlag_waehrend_sperre_hebt_sie_nicht_auf(
    image_service, moderation, real_embeddings_manager
):
    """Auch DESCRIPTION_FAILED darf eine zwischenzeitliche Sperre nicht ueberschreiben."""
    item_id = uuid.uuid4()
    await image_service.add(_wartendes_bild(item_id))
    strategie = _sperrt_waehrend_beschreibung(moderation, item_id, _ergebnis("  "))

    await _ein_durchlauf(image_service, strategie)

    payload = await real_embeddings_manager.get_by_id(str(item_id))
    assert payload["status"] == ContentStatus.BLOCKED.value
    assert payload[FELD_STATUS_VOR_SPERRE] == ContentStatus.PENDING_DESCRIPTION.value


async def test_update_status_nur_aus_laesst_anderen_status_stehen(
    image_service, real_embeddings_manager
):
    """Die bedingte Statusaenderung selbst: greift nur aus dem erwarteten Status."""
    item_id = uuid.uuid4()
    await image_service.add(_wartendes_bild(item_id))

    await image_service.update_status(
        item_id, ContentStatus.DESCRIPTION_FAILED, nur_aus=ContentStatus.APPROVED
    )
    payload = await real_embeddings_manager.get_by_id(str(item_id))
    assert payload["status"] == ContentStatus.PENDING_DESCRIPTION.value

    await image_service.update_status(
        item_id,
        ContentStatus.DESCRIPTION_FAILED,
        nur_aus=ContentStatus.PENDING_DESCRIPTION,
    )
    payload = await real_embeddings_manager.get_by_id(str(item_id))
    assert payload["status"] == ContentStatus.DESCRIPTION_FAILED.value
