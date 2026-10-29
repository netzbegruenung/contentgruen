import { ContentReference } from './commonDtos';
import type { NutzungJeFassung } from '../../shared/fassung';

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
    /** Die Kennung des Autors, nur fuer Admins (#333, #385); sonst null. */
    original_author?: string | null;
    /**
     * Anzeigename des Autors. In Meine Beitraege stehen nur eigene Beitraege, die Karte
     * zeigt "Du".
     */
    autor_name?: string | null;
    /** Ob es der eigene Beitrag ist; vom Server berechnet, in Meine Beitraege immer true. */
    ist_eigener_beitrag?: boolean | null;
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
    /** Davon in den letzten 7 Tagen (#349); fehlt bei aelteren Antworten. */
    nutzung_letzte_7_tage?: number;
    /** Kurz- und Langfassung eines Kommentars (#355). */
    short_text?: string | null;
    long_text?: string | null;
    /** Nur am Kommentar in Meine Beitraege: je vorhandener Fassung (#355). */
    nutzung_je_fassung?: NutzungJeFassung | null;
    /** Herkunftsangaben; Adresse und Beschreibung loest der Endpunkt auf. */
    references?: ContentReference[];
}
