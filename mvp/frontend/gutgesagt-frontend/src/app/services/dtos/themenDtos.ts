/** Ein Thema aus der festen Liste (domain/themen.json im Backend). */
export interface Thema {
    /** Was an der Aussage gespeichert wird. */
    schluessel: string;
    /** Die Anzeige. */
    name: string;
}

export interface ThemenResponse {
    themen: Thema[];
}

export interface ThemenZuordnenRequest {
    statement_id: string;
    themen: string[];
}

export interface ThemenZuordnenResponse {
    statement_id: string;
    themen: Thema[];
}

export interface AussageMitThemen {
    statement_id: string;
    statement_text: string;
    themen: Thema[];
}

export interface AussagenMitThemenResponse {
    aussagen: AussageMitThemen[];
}

/** Eine Zeile des Testsets, ohne Autor, Kennung und Zeitpunkt. */
export interface ThemenZuordnung {
    statement_id: string;
    text: string;
    themen: string[];
    quelle: string;
}

export interface ThemenTestsetResponse {
    zuordnungen: ThemenZuordnung[];
}
