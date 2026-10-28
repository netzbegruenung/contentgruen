import { ContentReference } from './commonDtos';

//TODO: Evaluate usage of camel case and transformation in the backend




// GetContributionsOfUser

export interface GetContributionsOfUserResponse {
    results_count: number
    results: ContentResult[];
    total_records_count: number;
}

export interface ContentResult {
    id: string;
    created: string;
    /** Nur /getContributionsOfUser; getById liefert ihn nicht (#333). */
    last_modified?: string;
    /** Die eigene Kennung in Meine Beitraege; beim Einzelabruf nur fuer Admins (#333). */
    original_author?: string | null;
    /**
     * Anzeigename zu original_author. /getContributionsOfUser liefert ihn nicht - dort stehen
     * nur eigene Beitraege, die Karte zeigt "Du".
     */
    autor_name?: string | null;
    /** Nur beim Einzelabruf (getById, #333): ob es der eigene Beitrag ist. */
    ist_eigener_beitrag?: boolean | null;
    /** Nur /getContributionsOfUser (eigene Beitraege); getById liefert sie nicht (#333). */
    last_modified_by?: string;
    edit_history?: object;
    /** Leer bei Bildern ohne Bildunterschrift. */
    text: string | null;
    content_type: string;
    score: number;
    /** Titel des Beitrags; fehlt nur bei Altbestand ohne Titel im Payload. */
    title?: string | null;
    /** Nur bei Bildern gesetzt. */
    image_url?: string | null;
    /** Aus PostgreSQL nachgetragen, 0 ohne Nutzung. */
    usage_count: number;
    /** Herkunftsangaben; Adresse und Beschreibung loest der Endpunkt auf. */
    references?: ContentReference[];
}
