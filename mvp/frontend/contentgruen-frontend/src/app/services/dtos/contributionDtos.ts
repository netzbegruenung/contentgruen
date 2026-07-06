
//TODO: Evaluate usage of camel case and transformation in the backend




// GetContributionsOfUser

export interface GetContributionsOfUserResponse {
    results_count: number
    results: ContentResult[];
    total_records_count: number;
}

export interface ContentResult {
    id: string;
    created: string;
    last_modified: string;
    original_author: string;
    last_modified_by: string;
    edit_history: object;
    text: string;
    content_type: string;
    score: number;
    usage_count?: number;
}
