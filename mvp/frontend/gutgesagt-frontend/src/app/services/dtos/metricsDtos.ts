
//TODO: Evaluate usage of camel case and transformation in the backend




// GetMetrics

export interface GetMetricsResponse {
    content_count: number;
    statement_count: number;
    commentary_count: number;
    reference_count: number;
}


// Suchen ohne Treffer (nur Admins)

// Text der Aussage, auf der die Suchanfragen gelandet sind; bewusst ohne ID.
export interface SucheOhneTreffer {
    text: string;
    anzahl: number;
}

export interface SuchenOhneTrefferResponse {
    wochen: number;
    /** Verschiedene Personen, ab denen eine Aussage erscheint (nicht Suchen). */
    mindestanzahl: number;
    suchanfragen: SucheOhneTreffer[];
}
