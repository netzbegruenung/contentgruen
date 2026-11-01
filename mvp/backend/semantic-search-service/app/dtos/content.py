from pydantic import BaseModel
from typing import List

from dtos.beitrag import BeitragResponse


### GetAll ###


class ContentGetAllResponse(BaseModel):
    results_count: int
    results: List[BeitragResponse]
    total_records_count: int
