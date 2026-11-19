import type { VorhandenDto } from './dubletteDtos';
import type { Thema } from './themenDtos';

import type { Stil, Zweck } from '../../shared/zweck-stil';

//TODO: Evaluate usage of camel case and transformation in the backend




// AddCommentary

export interface ReferenceInput {
    reference_string: string;
    description?: string;
}

export interface AddCommentaryRequest {
    commentary: Commentary
    references: ReferenceInput[];
    /** Worauf der Kommentar antwortet: ID einer vorhandenen Aussage ... */
    statement_id?: string;
    /** ... oder, ohne ID, ihr Text; das Backend sucht oder legt sie an. */
    statement_text?: string;
    /** Mit Text: die Themen der Aussage (#455); eine vorhandene mit Themen behaelt ihre. */
    themen?: string[];
    /** Die Person hat diesen vorhandenen Kommentar (ID) gesehen und speichert trotzdem. */
    trotz_dublette_von?: string;
    /** Die Person nimmt diesen eigenen vorhandenen Kommentar (ID): er haengt dann an der Aussage. */
    vorhanden_nehmen?: string;
    /** "Als Vorlage nehmen" (#356): der Beitrag (ID), auf dem der neue beruht. */
    beruht_auf?: string;
}

export interface Commentary {
    text: string;
    title: string;
    /** Die Fassungen Lang und Kurz (#355), optional; Mittel ist `text`. */
    long_text?: string;
    short_text?: string;
    /** Zweck und Stil (#357): ohne Zweck gilt Kommentarspalte, Stil optional. */
    zweck?: Zweck;
    style?: Stil;
    references: CommentaryReference[];
}

export interface CommentaryReference {
    reference_id: string;
    created: string;
}

export interface AddCommentaryResponse {
    id: string;
    /** Die Aussage, an der der Kommentar jetzt haengt; null ohne Aussage. */
    statement_id?: string | null;
    /** Text der tatsaechlich verknuepften Aussage (kann eine vorhandene, aehnliche sein). */
    statement_text?: string | null;
    /** true: Die Aussage kam per Text und wurde eben neu angelegt (Marke "neu" auf "Gespeichert", #617). */
    aussage_neu?: boolean;
    /** Kam die Aussage per Text mit Themen: die Themen, die sie jetzt hat (#455); sonst leer. */
    themen?: Thema[];
    /**
     * Ohne Dublette false: Aussage angegeben, aber nicht verknuepft - der Kommentar steht trotzdem.
     * Bei einer Dublette true nur, wenn der genommene vorhandene jetzt an der Aussage haengt; sonst false.
     */
    verknuepft?: boolean;
    /** Gesetzt: Es gibt schon einen sehr aehnlichen Beitrag (id: dessen ID), nichts angelegt; Titel und ob er von derselben Person ist. */
    vorhanden?: VorhandenDto | null;
}



// SearchCommentary
