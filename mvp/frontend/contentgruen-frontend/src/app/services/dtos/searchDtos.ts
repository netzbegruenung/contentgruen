// Wire format is snake_case end-to-end (see CONTENT_MODEL.md "Decisions").

import { BaseContentResult, BaseSearchResult, ContentReference } from "./commonDtos";

// Request DTOs

export interface SearchByTextRequest {
    query_text: string;
    limit: number;
}


// Response DTOs

export interface SearchResponse {
    query_was_newly_added_as_statement: boolean;
    statement_id: string;
    statement_text: string;
    commentary_search_results_count: number;
    commentary_search_results: CommentarySearchResult[];
    generictext_search_results_count: number;
    generictext_search_results: GenerictextSearchResult[];
    post_search_results_count?: number;
    post_search_results?: PostSearchResult[];
    image_search_results_count?: number;
    image_search_results?: ImageSearchResult[];
}

export interface CommentarySearchResult extends BaseSearchResult {
    commentary_result: CommentaryResult;
}

export interface CommentaryResult extends BaseContentResult {
    long_text: string;
    short_text: string;
    style?: string;
}

export interface GenerictextSearchResult extends BaseSearchResult {
    generictext_result: GenerictextResult;
}

export type GenerictextResult = BaseContentResult;

export interface PostSearchResult extends BaseSearchResult {
    post_result: PostResult;
}

export interface PostResult extends BaseContentResult {
    platform: string;
    author: string;
    url?: string;
    engagement: number;
}

export interface ImageSearchResult extends BaseSearchResult {
    image_result: ImageResult;
}

export interface ImageResult extends BaseContentResult {
    image_url: string;
    description_model?: string | null;
}

// Backwards-compatible aliases: references are structurally identical across types,
// so both now resolve to the shared ContentReference (see commonDtos.ts).
export type CommentaryReference = ContentReference;
export type GenericTextReference = ContentReference;
