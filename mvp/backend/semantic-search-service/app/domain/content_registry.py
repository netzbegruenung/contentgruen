"""
Declarative content-type registry (rung-1 Step 5).

Replaces the per-type ``Service`` subclass tower with one declarative ``ContentTypeSpec``
per type, from which a generic ``BaseContentService`` is instantiated. See
``docs/CONTENT_MODEL.md`` ("A content-type registry replaces the per-type class tower")
and ``docs/RUNG_1_PLAN.md`` Step 5.

This is the *minimal* introduction: each spec reuses the existing repository via the
``IRepositoryFactory`` (so persistence/search behavior is byte-for-byte unchanged), and
carries the per-type model classes (Seam 2). Type-specific *input* handling (Seam 1,
ingestion) and real per-type behavior (e.g. ``StatementService`` dedup) remain in their
own classes for now; the registry does not flatten those.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Type

from core.config import Settings, settings as _settings
from domain.models.content_type import ContentType
from domain.models.base_content import BaseContentDbEntry, BaseContentSearchResult
from domain.models.commentary import CommentaryDbEntry, CommentarySearchResult
from domain.models.generic_text import GenericTextDbEntry, GenericTextSearchResult
from domain.models.post import PostDbEntry, PostSearchResult
from domain.models.image import ImageDbEntry, ImageSearchResult
from domain.ingestion_strategies import DirectText, AiVisionDescription
from domain.protocols import IngestionStrategy
from repositories.interfaces.base_content_repository import IBaseContentRepository
from repositories.interfaces.repository_factory import IRepositoryFactory
from services.content.base_content_service import BaseContentService


@dataclass(frozen=True)
class ContentTypeSpec:
    """Everything needed to stand up a content type's storage/search service.

    ``create_repository`` is the per-type seam onto the existing repository tower; it
    keeps Step 5 behavior-preserving while the empty interface/factory layers are retired
    incrementally (see CONTENT_MODEL.md migration plan).

    ``ingestion`` is Seam 1 (CONTENT_MODEL.md): how searchable_text is produced from
    raw input. Defaults to DirectText (user-supplied text = searchable text).
    """

    content_type: ContentType
    index_name: str
    db_entry_model: Type[BaseContentDbEntry]
    search_result_model: Type[BaseContentSearchResult]
    create_repository: Callable[[IRepositoryFactory, Settings], IBaseContentRepository]
    ingestion: IngestionStrategy = field(default_factory=DirectText)


class _RegistryContentService(
    BaseContentService[IBaseContentRepository, BaseContentDbEntry, BaseContentSearchResult]
):
    """Concrete, behavior-free ``BaseContentService`` built from a spec.

    All real per-type behavior lives in dedicated subclasses (``StatementService``); this
    class exists only so the generic base can be instantiated directly from a spec.
    """


REGISTRY: Dict[ContentType, ContentTypeSpec] = {
    ContentType.COMMENTARY: ContentTypeSpec(
        content_type=ContentType.COMMENTARY,
        index_name="commentary",
        db_entry_model=CommentaryDbEntry,
        search_result_model=CommentarySearchResult,
        create_repository=lambda factory, settings: factory.create_commentary_repository(
            settings
        ),
    ),
    ContentType.GENERIC_TEXT: ContentTypeSpec(
        content_type=ContentType.GENERIC_TEXT,
        index_name="generic_text",
        db_entry_model=GenericTextDbEntry,
        search_result_model=GenericTextSearchResult,
        create_repository=lambda factory, settings: factory.create_generic_text_repository(
            settings
        ),
    ),
    ContentType.POST: ContentTypeSpec(
        content_type=ContentType.POST,
        index_name="post",
        db_entry_model=PostDbEntry,
        search_result_model=PostSearchResult,
        create_repository=lambda factory, settings: factory.create_registry_repository(
            settings,
            "post",
            ContentType.POST.value,
            PostDbEntry,
            PostSearchResult,
        ),
    ),
    ContentType.IMAGE: ContentTypeSpec(
        content_type=ContentType.IMAGE,
        index_name="image",
        db_entry_model=ImageDbEntry,
        search_result_model=ImageSearchResult,
        create_repository=lambda factory, settings: factory.create_registry_repository(
            settings,
            "image",
            ContentType.IMAGE.value,
            ImageDbEntry,
            ImageSearchResult,
        ),
        ingestion=AiVisionDescription(
            # The module is imported lazily (via __import__) to avoid pulling openai
            # at module load when OPENAI_API_KEY is not configured (e.g. in test envs).
            # The IIFE runs once at registry-import time, not on first service request.
            (lambda: __import__(
                "services.vision.caption_suggestion_service",
                fromlist=["CaptionSuggestionService"]
            ).CaptionSuggestionService(
                api_key=_settings.openai_api_key or "",
                model=_settings.openai_vision_model,
            ))()
        ) if _settings.openai_api_key else DirectText(),
    ),
}


def create_content_service(
    spec: ContentTypeSpec,
    settings: Settings,
    repository_factory: IRepositoryFactory,
) -> BaseContentService:
    """Instantiate the generic content service for ``spec`` -- no per-type subclass."""
    repository = spec.create_repository(repository_factory, settings)
    content_repository = repository_factory.create_content_repository(settings)
    return _RegistryContentService(
        settings,
        repository,
        content_repository,
        spec.db_entry_model,
        spec.search_result_model,
    )
