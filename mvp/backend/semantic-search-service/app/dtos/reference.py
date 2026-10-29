from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime

from domain.models.reference import ReferenceSearchResult


### Search References ###


class SearchReferencesRequest(BaseModel):
    query_text: str
    limit: int = 10


class ReferenceSearchItem(BaseModel):
    id: UUID
    reference_string: str
    text: str
    created: datetime
    usage_count: int = 0
    score: Optional[float] = None


class SearchReferencesResponse(BaseModel):
    results: List[ReferenceSearchItem]
    has_exact_match: bool = False
    exact_match_id: Optional[UUID] = None


### Add Reference ###


class AddReferenceRequest(BaseModel):
    reference_string: str
    text: str


class AddReferenceResponse(BaseModel):
    id: UUID
    was_new: bool
    message: Optional[str] = None


### Get Reference ###


class GetReferenceResponse(BaseModel):
    """
    Eine Herkunft mit Personenbezug wie an Beitraegen (#385): ``original_author``
    ist nur unterwegs belegt, ``fuer_aufrufer`` (``HERKUNFT``) setzt daraus
    Anzeigename und ``ist_eigene_herkunft`` und leert es fuer alle ausser Admins.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_string: str
    text: str
    created: datetime
    last_modified: datetime
    usage_count: int = 0
    # Anzeigename zu original_author; nur fuer angemeldete Aufrufer, sonst None.
    autor_name: Optional[str] = None
    # Ob die aufrufende Person die Herkunft angelegt hat; nur angemeldet, sonst None.
    ist_eigene_herkunft: Optional[bool] = None
    # Die Kennung der Person, die die Herkunft angelegt hat, nur fuer Admins.
    original_author: Optional[str] = None

    @field_validator("usage_count", mode="before")
    @classmethod
    def _nutzung_null_als_null(cls, value):
        return 0 if value is None else value


# Note: Check and Add functionality has been merged into AddReference
