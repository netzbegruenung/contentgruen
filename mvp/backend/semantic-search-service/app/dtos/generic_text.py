from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from domain.models.generic_text import (
    GenericText,
    GenericTextDbEntry,
    GenericTextSearchResult,
)


### AddGenericText ###

HINTERGRUNDINFO_TEXT_MAX = 2000


class ReferenceInput(BaseModel):
    reference_string: str
    description: Optional[str] = None


class AddGenericTextRequest(BaseModel):
    generictext: GenericText
    references: List[ReferenceInput]
    # Worauf die Hintergrundinfo antwortet: ID einer vorhandenen Aussage oder, wenn
    # keine bekannt ist, ihr Text. Ohne beides steht sie fuer sich.
    statement_id: Optional[UUID] = None
    statement_text: Optional[str] = Field(default=None, max_length=1000)

    # 2000 Zeichen wie im Formular; nur beim Anlegen, damit aeltere, laengere
    # Eintraege lesbar bleiben (wie beim Kommentar).
    @field_validator("generictext")
    @classmethod
    def text_hoechstens_2000_zeichen(cls, generictext: GenericText) -> GenericText:
        if len(generictext.text) > HINTERGRUNDINFO_TEXT_MAX:
            raise ValueError(
                f"Der Text darf hoechstens {HINTERGRUNDINFO_TEXT_MAX} Zeichen lang sein"
            )
        return generictext


class AddGenericTextResponse(BaseModel):
    id: UUID
    # Die Aussage, an der die Hintergrundinfo jetzt haengt; None ohne Aussage oder
    # wenn die Verknuepfung scheiterte.
    statement_id: Optional[UUID] = None
    # False nur, wenn eine Aussage angegeben war und nicht verknuepft werden konnte.
    verknuepft: bool = True


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
