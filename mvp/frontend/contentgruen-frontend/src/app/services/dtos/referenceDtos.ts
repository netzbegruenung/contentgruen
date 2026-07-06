// Reference DTOs

// Search References
export interface SearchReferencesRequest {
    query_text: string;
    limit: number;
}

export interface ReferenceSearchItem {
    id: string;
    reference_string: string;
    text: string;
    created: string;
    usage_count: number;
    score?: number;
}

export interface SearchReferencesResponse {
    results: ReferenceSearchItem[];
    has_exact_match: boolean;
    exact_match_id?: string;
}

// Add Reference
export interface AddReferenceRequest {
    reference_string: string;
    text: string;
}

export interface AddReferenceResponse {
    id: string;
    was_new: boolean;
    message?: string;
}

// Get Reference
export interface GetReferenceResponse {
    id: string;
    reference_string: string;
    text: string;
    created: string;
    last_modified: string;
    original_author: string;
    usage_count: number;
}
