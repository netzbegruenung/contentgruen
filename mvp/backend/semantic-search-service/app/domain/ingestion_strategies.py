"""
Concrete ingestion strategies (Seam 1 of CONTENT_MODEL.md, rung-2 Phase B).

DirectText  — identity strategy used by all existing types (text = user input).
AiVisionDescription — calls the OpenAI vision API to derive a German caption for an image.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.protocols import ContentInput, DerivedContent

if TYPE_CHECKING:
    from services.vision.caption_suggestion_service import CaptionSuggestionService


class DirectText:
    """Identity ingestion: the user-provided text is the searchable text."""

    async def derive_text(self, raw: ContentInput) -> DerivedContent:
        return DerivedContent(text=raw.text)


class AiVisionDescription:
    """
    AI ingestion: call the vision API to generate a German caption for an image.
    Reuses CaptionSuggestionService from Phase A — no new AI integration code.
    The model name is recorded in DerivedContent.extra so the worker can persist it.
    """

    def __init__(self, caption_service: CaptionSuggestionService) -> None:
        self._service = caption_service

    async def derive_text(self, raw: ContentInput) -> DerivedContent:
        description = await self._service.suggest_caption(raw.image_url)
        return DerivedContent(
            text=description,
            extra={"description_model": self._service.model},
        )
