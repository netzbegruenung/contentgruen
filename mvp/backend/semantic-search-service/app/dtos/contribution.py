from pydantic import BaseModel
from typing import List

from domain.models.content import ContentDbEntry


###   Requests   ###


class GetContributionsOfUserResponse(BaseModel):
    results_count: int
    results: List[ContentDbEntry]
    total_records_count: int
