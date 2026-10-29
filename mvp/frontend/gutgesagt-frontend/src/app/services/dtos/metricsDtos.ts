
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


// Bilanz (nur Admins, #467): Kennzahlen je Kalenderwoche, ohne Zielwerte.
// null heisst unbekannt, nicht 0.

export interface BilanzWoche {
    /** Montag der Woche (UTC), JJJJ-MM-TT. */
    woche_ab: string;
    /** Tage der Woche bis heute; unter 7 nur in der laufenden. */
    tage: number;
    suchen: number;
    /** K1, Wochenmittel. */
    personen_pro_tag: number;
    /** K2. */
    nutzungen: number | null;
    /** K3, in Prozent. */
    anteil_ohne_treffer: number | null;
    /** H. */
    nutzungen_je_suche: number | null;
}

export interface BilanzResponse {
    wochen: number;
    /** Die laufende Woche zuerst. */
    woechentlich: BilanzWoche[];
}
