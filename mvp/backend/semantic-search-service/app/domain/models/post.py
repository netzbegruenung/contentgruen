from typing import Optional
from pydantic import Field

from domain.models.content_type import ContentType
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class Post(BaseContent):
    """
    A social-media post captured as searchable political content.

    The 'text' field inherited from BaseContent holds the post body used for
    semantic search. The fields below carry the post-specific provenance and
    engagement metadata that make a Post distinct from generic text.

    Attributes:
    -----------
    title: str
        Short title/headline for the post.
    platform: str
        Source platform of the post (e.g. "mastodon", "bluesky", "x").
    author: str
        Handle/name of the post's original author on the source platform
        (distinct from the Gut gesagt user who imported it).
    url: Optional[str]
        Permalink to the original post.
    engagement: int
        Aggregate engagement count (likes/boosts/replies) at import time.
    """

    content_type: ContentType = ContentType.POST

    title: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description=(
            "Title/headline of the post. Generous upper bound because the title may "
            "be derived from the post body when no explicit title is supplied "
            "(common short-form platform bodies run up to ~500 chars)."
        ),
    )
    platform: str = Field(..., description="Source platform of the post")
    author: str = Field(..., description="Original author handle on the platform")
    url: Optional[str] = None
    engagement: int = 0


class PostDbEntry(Post, BaseContentDbEntry):
    """
    Representing a post with additional metadata for indexing.
    """


class PostSearchResult(PostDbEntry, BaseContentSearchResult):
    """
    Representing a post entry with score and additional result metadata.
    """
