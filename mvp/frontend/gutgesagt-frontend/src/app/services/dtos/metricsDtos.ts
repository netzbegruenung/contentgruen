
//TODO: Evaluate usage of camel case and transformation in the backend




// GetMetrics

export interface GetMetricsResponse {
    content_count: number;
    content_count_last_week: number;
    statement_count: number;
    statement_count_last_week: number;
    commentary_count: number;
    commentary_count_last_week: number;
    reference_count: number;
    reference_count_last_week: number;

    requested_commentary_count: number;

    active_users_count: number;
}
