from pydantic import BaseModel


###   GetMetrics   ###


class GetMetricsResponse(BaseModel):
    content_count: int
    statement_count: int
    commentary_count: int
    reference_count: int
