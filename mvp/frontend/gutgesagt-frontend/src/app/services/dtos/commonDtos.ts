import { ContentStatus } from "./content-status-enum";

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
    /** Kennung des Autors, nur fuer Admins; sonst null (#333). */
    original_author?: string | null;
    /** Anzeigename des Autors ("Anna B."); nur fuer Angemeldete, sonst null. */
    autor_name?: string | null;
    /** Ob die angemeldete Person den Beitrag gespeichert hat; ohne Anmeldung null. */
    ist_eigener_beitrag?: boolean | null;
    status: ContentStatus;
    title: string;
    references: ContentReference[];
    references_count: number;
    usage_count?: number;
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
