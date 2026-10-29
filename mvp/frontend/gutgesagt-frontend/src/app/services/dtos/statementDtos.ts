import { Thema } from './themenDtos';


//TODO: Evaluate usage of camel case and transformation in the backend

// Content Type enum matching backend
export type ContentType = 'statement' | 'commentary' | 'reference' | 'generic_text' | 'test' | 'default';

// Statement Search
export interface SearchStatementByTextRequest {
    query_text: string;
    limit: number;
    /** Unbeantwortete Suchanfragen weglassen (wie der Aussagen-Zaehler der Startseite). */
    nur_kuratiert?: boolean;
    /** Nur Treffer mit mindestens diesem Aehnlichkeitswert, 0-1. */
    min_similarity?: number;
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

/** Die Antwort auf das Vorab-Anlegen, mit den Themen, die die Aussage jetzt hat. */
export interface AussageVorabResponse extends AddStatementResponse {
    themen: Thema[];
}

// Hier fehlt eine Antwort

/**
 * Eine unbeantwortete Aussage: ohne Kommentar oder mit Suchen ohne Treffer von
 * mindestens zwei Personen. personen_ohne_treffer zaehlt diese Personen wie die
 * Kennzahl (Tagespseudonyme); 0 heisst, die Aussage steht nur wegen des fehlenden
 * Kommentars hier. Wie oft gesucht wurde, sehen nur Admins.
 */
export interface UnbeantworteteAussage {
    statement_id: string;
    statement_text: string;
    personen_ohne_treffer: number;
    /** Hoechstens zwei, in der Reihenfolge der Themenliste. */
    themen: Thema[];
}

export interface UnbeantworteteAussagenResponse {
    aussagen: UnbeantworteteAussage[];
}

export interface AussageVorabRequest {
    text: string;
    /** Optional ein bis zwei Themen-Schluessel. */
    themen?: string[];
}

// GetStatementById

export interface GetStatementByIdResponse {
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
