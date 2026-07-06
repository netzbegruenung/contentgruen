from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional

from domain.models.generic_text import (
    GenericText,
    GenericTextDbEntry,
    GenericTextSearchResult,
)


### AddGenericText ###


class ReferenceInput(BaseModel):
    reference_string: str
    description: Optional[str] = None


class AddGenericTextRequest(BaseModel):
    generictext: GenericText
    references: List[ReferenceInput]


class AddGenericTextResponse(BaseModel):
    id: UUID


### GetAll ###


class GenericTextGetAllResponse(BaseModel):
    results_count: int
    results: List[GenericTextDbEntry]
    total_records_count: int


### SearchGenericText ###


class SearchGenericTextByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, commentary, etc.)
    # TODO: Add a field to specify minimum score


class GenericTextSearchResponse(BaseModel):
    results: List[GenericTextSearchResult]
