"""
Async background worker that processes PENDING_DESCRIPTION images.

The worker polls `image_service.get_by_status(PENDING_DESCRIPTION)` on a fixed
interval, calls the configured IngestionStrategy (AiVisionDescription) to derive a
German caption, then upserts the enriched entry and moves it to PENDING_REVIEW.

On failure it sets DESCRIPTION_FAILED. On OpenAI rate-limit it backs off 60 s and
re-picks up remaining items on the next poll cycle. The loop is idempotent: a hard
restart simply re-processes all PENDING_DESCRIPTION items from scratch.

Known limitation: items in progress are lost on a hard crash. This is acceptable at
current ingestion volume; switch to ARQ/Celery when throughput justifies the cost.
"""

import asyncio
import logging

from domain.models.content_status import ContentStatus
from domain.protocols import ContentInput

logger = logging.getLogger(__name__)


async def _description_worker(
    image_service,
    ingestion_strategy,
    poll_interval_s: int = 60,
) -> None:
    while True:
        try:
            pending = await image_service.get_by_status(
                ContentStatus.PENDING_DESCRIPTION, limit=10
            )
            for entry in pending:
                try:
                    result = await ingestion_strategy.derive_text(
                        ContentInput(image_url=entry.image_url)
                    )
                    if not result.text or not result.text.strip():
                        logger.warning(
                            f"Description worker: empty text for image {entry.id}; "
                            "marking DESCRIPTION_FAILED"
                        )
                        await image_service.update_status(
                            entry.id, ContentStatus.DESCRIPTION_FAILED
                        )
                        continue
                    updated = entry.model_copy(
                        update={
                            "text": result.text,
                            "status": ContentStatus.PENDING_REVIEW,
                            **result.extra,
                        }
                    )
                    await image_service.add(updated)
                    logger.info(
                        f"Description worker: processed image {entry.id} "
                        f"({len(result.text)} chars caption)"
                    )
                except Exception as e:
                    # Import here to avoid hard dependency when openai is not installed.
                    try:
                        from openai import RateLimitError, APIConnectionError, APIStatusError
                        if isinstance(e, RateLimitError):
                            logger.warning(
                                "OpenAI rate limit hit; pausing description worker for 60 s"
                            )
                            await asyncio.sleep(60)
                            break
                        if isinstance(e, APIConnectionError) or (
                            isinstance(e, APIStatusError) and e.status_code >= 500
                        ):
                            logger.warning(
                                f"Description worker: transient API error for {entry.id}: {e}; "
                                "leaving at PENDING_DESCRIPTION for next poll"
                            )
                            continue
                    except ImportError:
                        pass

                    logger.error(
                        f"Description worker: failed to describe image {entry.id}: {e}",
                        exc_info=True,
                    )
                    await image_service.update_status(
                        entry.id, ContentStatus.DESCRIPTION_FAILED
                    )

                await asyncio.sleep(0.5)  # stay within OpenAI RPM limits

        except Exception as e:
            logger.error(f"Description worker: poll error: {e}", exc_info=True)

        await asyncio.sleep(poll_interval_s)


def start_description_worker(image_service, ingestion_strategy) -> None:
    """Schedule the description worker as a background asyncio task."""
    asyncio.create_task(
        _description_worker(image_service, ingestion_strategy),
        name="image_description_worker",
    )
    logger.info("Image description worker started")
