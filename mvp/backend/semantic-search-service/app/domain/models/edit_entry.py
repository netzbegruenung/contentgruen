import datetime
from domain.models.zeit import UtcZeit
from typing import Optional
from pydantic import BaseModel, field_validator

from domain.models.model_utils import ModelValidator


class EditEntry(BaseModel):
    """
    Represents an edit entry with metadata.

    Attributes:
    -----------
    editor: str
        Name or identifier of the editor.
    timestamp: datetime
        Timestamp of the edit.
    action: Optional[str]
        Type of action performed (e.g., "edit", "review").
    """

    editor: str
    timestamp: UtcZeit
    action: Optional[str] = None

    @field_validator("timestamp", mode="before")
    def parse_timestamp(cls, value):
        return ModelValidator.validate_datetime(value)
