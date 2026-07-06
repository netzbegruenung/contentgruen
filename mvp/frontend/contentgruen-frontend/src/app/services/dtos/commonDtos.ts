import { ContentOrigin } from "./content-origin-enum";
import { ContentStatus } from "./content-status-enum";
import { ContentVisibility } from "./content-visibility-enum";

export interface AuthorEntry {
    name: string;
    role: string;
}

export interface EditEntry {
    editor: string;
    timestamp: string;
    action: string;
}

/**
 * A reference/source linked to a content item, as returned in search results.
 * Structurally identical for every content type, so it lives here once.
 */
export interface ContentReference {
    reference_id: string;
    created: string;
    reference_text?: string;  // The URL
    reference_description?: string;  // The description
}

/**
 * Fields shared by every content-type search result (the mechanism, written once).
 * Per-type results extend this with only their extra fields (Seam 2 of CONTENT_MODEL.md).
 * The wire format is snake_case end-to-end (see CONTENT_MODEL.md "Decisions").
 */
export interface BaseContentResult {
    text: string;
    content_type: string;
    id: string;
    created: string;
    last_modified: string;
    original_author: string;
    last_modified_by: string;
    authors: AuthorEntry[];
    edit_history: EditEntry[];
    status: ContentStatus;
    origin: ContentOrigin;
    most_similar_similarity_score: number;
    most_similar_content_id: string;
    report_count: number;
    is_archived: boolean;
    report_flagged: boolean;
    rejection_reason: string;
    block_reason: string;
    visibility: ContentVisibility;
    title: string;
    references: ContentReference[];
    references_count: number;
    usage_count?: number;
    score: number;
}

/**
 * Fields shared by every per-type search-result wrapper (statement-relative scoring
 * + the user's vote). The concrete per-type wrapper adds its nested `*_result`.
 */
export interface BaseSearchResult {
    score: number;
    statement_text: string | null;
    statement_similarity_score: number | null;
    reply_relevance: number | null;
    user_vote?: string;  // "like", "dislike", or undefined
}
