from uuid import UUID
from pydantic import BaseModel
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
    id: UUID
    reference_string: str
    text: str
    created: datetime
    last_modified: datetime
    original_author: str
    usage_count: int = 0


# Note: Check and Add functionality has been merged into AddReference
