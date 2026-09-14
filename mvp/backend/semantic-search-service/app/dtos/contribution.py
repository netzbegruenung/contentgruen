from pydantic import BaseModel, field_validator
from typing import List, Optional

from domain.models.content import ContentDbEntry


###   Responses   ###


class ContributionEntry(ContentDbEntry):
    """
    Ein Eintrag in "Meine Beitraege", so wie die Beitragskarte ihn braucht.

    ContentDbEntry allein verwirft beim Lesen aus Qdrant alles, was nicht zu den
    gemeinsamen Feldern gehoert - auch Titel und Bildadresse, obwohl sie im Payload
    stehen. Die Nutzung liegt nicht in Qdrant, sondern in PostgreSQL und wird im
    Endpunkt nachgetragen.
    """

    title: Optional[str] = None
    image_url: Optional[str] = None
    usage_count: int = 0

    @field_validator("usage_count", mode="before")
    @classmethod
    def _nutzung_null_als_null(cls, value):
        # Aeltere Payloads tragen usage_count: null. Die echte Zahl kommt ohnehin aus
        # PostgreSQL und wird im Endpunkt nachgetragen; ohne diese Umwandlung
        # scheitert schon das Lesen aus Qdrant und die ganze Liste mit 500.
        return 0 if value is None else value


class GetContributionsOfUserResponse(BaseModel):
    results_count: int
    results: List[ContributionEntry]
    total_records_count: int
