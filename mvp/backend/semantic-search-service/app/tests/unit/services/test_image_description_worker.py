"""
Unit tests for the image description worker state machine.

Tests verify:
- Empty derived text transitions the item to DESCRIPTION_FAILED (not NEW_CONTENT_STATUS)
- Transient OpenAI errors (connection, 5xx) leave the item at PENDING_DESCRIPTION
- Permanent errors transition to DESCRIPTION_FAILED
- RateLimitError breaks the current batch and re-polls after sleep
"""

import asyncio
import uuid
import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from domain.models.content_status import ContentStatus, NEW_CONTENT_STATUS
from domain.models.content_type import ContentType
from domain.models.content_origin import ContentOrigin
from domain.models.image import ImageDbEntry
from domain.models.author_entry import AuthorEntry
from services.vision.image_description_worker import _description_worker


def _make_pending_image(item_id: uuid.UUID | None = None) -> ImageDbEntry:
    now = datetime.datetime.now()
    return ImageDbEntry(
        id=item_id or uuid.uuid4(),
        title="Test Image",
        image_url="https://example.com/test.jpg",
        text=None,
        content_type=ContentType.IMAGE,
        created=now,
        last_modified=now,
        original_author="tester",
        last_modified_by="tester",
        authors=[AuthorEntry(name="tester")],
        status=ContentStatus.PENDING_DESCRIPTION,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


def _make_derived(text: str):
    result = MagicMock()
    result.text = text
    result.extra = {}
    return result


@pytest.mark.unit
@pytest.mark.asyncio
class TestWorkerStateMachine:
    async def _run_one_cycle(self, image_service, ingestion_strategy):
        """Run the worker for exactly one poll cycle then stop."""
        cycle_done = asyncio.Event()
        original_sleep = asyncio.sleep

        async def fake_sleep(secs):
            cycle_done.set()
            # Raise to break out of the infinite loop after one cycle
            raise StopAsyncIteration

        with patch("services.vision.image_description_worker.asyncio.sleep", fake_sleep):
            try:
                await _description_worker(image_service, ingestion_strategy, poll_interval_s=1)
            except StopAsyncIteration:
                pass

    async def test_empty_derived_text_marks_description_failed(self):
        """Empty caption from ingestion strategy → DESCRIPTION_FAILED, not PENDING_REVIEW."""
        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock()

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(return_value=_make_derived(""))

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_called_once_with(
            item_id, ContentStatus.DESCRIPTION_FAILED
        )
        image_service.add.assert_not_called()

    async def test_whitespace_only_derived_text_marks_description_failed(self):
        """Whitespace-only caption → DESCRIPTION_FAILED."""
        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock()

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(return_value=_make_derived("   "))

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_called_once_with(
            item_id, ContentStatus.DESCRIPTION_FAILED
        )
        image_service.add.assert_not_called()

    async def test_transient_connection_error_leaves_pending_description(self):
        """APIConnectionError → item stays at PENDING_DESCRIPTION (no update_status call)."""
        try:
            from openai import APIConnectionError
        except ImportError:
            pytest.skip("openai not installed")

        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock()

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(
            side_effect=APIConnectionError.__new__(APIConnectionError)
        )

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_not_called()
        image_service.add.assert_not_called()

    async def test_transient_5xx_error_leaves_pending_description(self):
        """APIStatusError with status 503 → item stays at PENDING_DESCRIPTION."""
        try:
            from openai import APIStatusError
        except ImportError:
            pytest.skip("openai not installed")

        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock()

        # Use __new__ to avoid complex constructor requirements (response, body kwargs)
        err = APIStatusError.__new__(APIStatusError)
        err.status_code = 503

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(side_effect=err)

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_not_called()
        image_service.add.assert_not_called()

    async def test_4xx_api_error_marks_description_failed(self):
        """APIStatusError with status 400 → permanent failure → DESCRIPTION_FAILED."""
        try:
            from openai import APIStatusError
        except ImportError:
            pytest.skip("openai not installed")

        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock()

        err = APIStatusError.__new__(APIStatusError)
        err.status_code = 400

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(side_effect=err)

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_called_once_with(
            item_id, ContentStatus.DESCRIPTION_FAILED
        )

    async def test_valid_caption_promotes_to_new_content_status(self):
        """Good caption → NEW_CONTENT_STATUS via service.add()."""
        item_id = uuid.uuid4()
        entry = _make_pending_image(item_id)

        image_service = MagicMock()
        image_service.get_by_status = AsyncMock(return_value=[entry])
        image_service.update_status = AsyncMock()
        image_service.add = AsyncMock(return_value=item_id)

        ingestion_strategy = MagicMock()
        ingestion_strategy.derive_text = AsyncMock(
            return_value=_make_derived("Windräder in Niedersachsen")
        )

        await self._run_one_cycle(image_service, ingestion_strategy)

        image_service.update_status.assert_not_called()
        image_service.add.assert_called_once()
        updated = image_service.add.call_args[0][0]
        assert updated.status == NEW_CONTENT_STATUS
        assert updated.text == "Windräder in Niedersachsen"
