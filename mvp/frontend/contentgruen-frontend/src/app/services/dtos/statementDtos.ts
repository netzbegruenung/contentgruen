
//TODO: Evaluate usage of camel case and transformation in the backend

// Content Type enum matching backend
export type ContentType = 'statement' | 'commentary' | 'reference' | 'generic_text' | 'test' | 'default';

// Statement Search
export interface SearchStatementByTextRequest {
    query_text: string;
    limit: number;
}

export interface StatementSearchResult {
    id: string;
    text: string;
    replysuggestions_count: number;
    score: number;
    // Add other fields as needed
}

export interface StatementSearchResponse {
    results: StatementSearchResult[];
}

// AddStatement

/**
 * Aus welcher Situation heraus ein Statement angelegt wird.
 *
 * 'search_query': jemand hat gesucht - das Statement entsteht nebenbei und
 * bekommt im Backend einen Systemautor, keine Person.
 * 'manually_created': jemand benennt in "Beitrag ergaenzen" ausdruecklich eine
 * Aussage, zu der er antworten will - hier bleibt die Person als Autorin.
 */
export type StatementSource = 'search_query' | 'manually_created';

export interface AddStatementRequest {
    statement: {
        text: string;
        replysuggestions: any[];
    };
    source: StatementSource;
}

export interface AddStatementResponse {
    statement_was_new: boolean;
    statement_id: string;
    statement_text: string;
}

// AddCommentaryToStatement

export interface AddReplysuggestionToStatementRequest {
    statement_id: string;
    replysuggestion_id: string;
    content_type: ContentType;
    relevance: number;
}

export interface AddReplysuggestionToStatementResponse {
    success: boolean;
}
