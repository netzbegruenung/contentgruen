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
    usage_count: number;
    /** Anzeigename der Person, die die Herkunft angelegt hat; nur angemeldet. */
    autor_name?: string | null;
    /** Ob die anfragende Person sie angelegt hat; vom Server berechnet (#385). */
    ist_eigene_herkunft?: boolean | null;
    /** Die Kennung, nur fuer Admins; sonst null. */
    original_author?: string | null;
}
