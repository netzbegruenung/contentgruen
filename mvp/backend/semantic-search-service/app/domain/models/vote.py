import datetime
import uuid
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator
from domain.models.model_utils import ModelValidator


class VoteType(str, Enum):
    """Enum for vote types."""

    LIKE = "like"
    DISLIKE = "dislike"


class Vote(BaseModel):
    """
    Model for user votes on content items.

    Attributes:
    -----------
    id: uuid.UUID
        Unique identifier for the vote.
    user_id: str
        Identifier of the user who voted.
    content_id: uuid.UUID
        ID of the content item being voted on.
    vote_type: VoteType
        Type of vote (like or dislike).
    created: datetime
        Timestamp when the vote was created.
    """

    id: uuid.UUID
    user_id: str
    content_id: uuid.UUID
    vote_type: str
    created: datetime.datetime

    @field_validator("id", "content_id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("created", mode="before")
    def parse_datetime(cls, value):
        return ModelValidator.validate_datetime(value)

    @field_validator("vote_type", mode="before")
    def validate_vote_type(cls, value):
        if value not in [VoteType.LIKE.value, VoteType.DISLIKE.value]:
            raise ValueError(f"Invalid vote type: {value}. Must be 'like' or 'dislike'")
        return value


class VoteCreate(BaseModel):
    """Model for creating a new vote."""

    content_id: uuid.UUID
    vote_type: str

    @field_validator("content_id", mode="before")
    def parse_uuid(cls, value):
        return ModelValidator.validate_uuid(value)

    @field_validator("vote_type", mode="before")
    def validate_vote_type(cls, value):
        if value not in [VoteType.LIKE.value, VoteType.DISLIKE.value]:
            raise ValueError(f"Invalid vote type: {value}. Must be 'like' or 'dislike'")
        return value


class VoteResponse(BaseModel):
    """Response model for vote operations."""

    content_id: uuid.UUID
    vote_type: Optional[str] = None
    message: str
