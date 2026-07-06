from pydantic import BaseModel
from typing import List


###   GetMetrics   ###


class GetMetricsResponse(BaseModel):
    content_count: int
    content_count_last_week: int
    statement_count: int
    statement_count_last_week: int
    commentary_count: int
    commentary_count_last_week: int
    reference_count: int
    reference_count_last_week: int

    requested_commentary_count: int

    active_users_count: int
