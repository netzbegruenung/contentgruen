from __future__ import annotations
from dataclasses import dataclass
from typing import (
    Optional,
    Protocol,
    List,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)
from uuid import UUID
from datetime import datetime

from domain.models.author_entry import AuthorEntry
from domain.models.content_type import ContentType
from domain.models.edit_entry import EditEntry


class BaseContentProtocol(Protocol):
    text: str
    content_type: ContentType


class BaseContentInputProtocol(BaseContentProtocol):
    id: UUID
    created: datetime
    last_modified: datetime
    original_author: str
    last_modified_by: str
    authors: List[AuthorEntry]
    edit_history: List[EditEntry]


class BaseContentResultProtocol(BaseContentInputProtocol):
    score: Optional[float]


# --- Ingestion strategy protocol (Seam 1 of CONTENT_MODEL.md) ---


@dataclass
class ContentInput:
    """Raw input passed to an ingestion strategy."""

    text: str = ""


@dataclass
class DerivedContent:
    """Searchable text produced by an ingestion strategy."""

    text: str


@runtime_checkable
class IngestionStrategy(Protocol):
    """Seam 1 of CONTENT_MODEL.md: how searchable_text is produced from raw input."""

    async def derive_text(self, raw: ContentInput) -> DerivedContent: ...
