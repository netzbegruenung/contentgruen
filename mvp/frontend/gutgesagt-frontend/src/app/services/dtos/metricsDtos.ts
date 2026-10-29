
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

/** Ein Muster-Hinweis (#352): zwei Konten, die sich am selben Tag gegenseitig genutzt haben. */
export interface MusterHinweis {
    konto_a: string;
    name_a: string | null;
    konto_b: string;
    name_b: string | null;
    /** Tage mit gegenseitiger Nutzung. */
    tage: number;
    erster_tag: string;
    letzter_tag: string;
}

export interface MusterHinweiseResponse {
    /** Ohne eingeschaltete Punkte entstehen keine Hinweise. */
    aktiv: boolean;
    frist_tage: number;
    hinweise: MusterHinweis[];
}
