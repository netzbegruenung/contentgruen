import type { VorhandenDto } from './dubletteDtos';
import type { Thema } from './themenDtos';

//TODO: Evaluate usage of camel case and transformation in the backend




// AddGenericText

export interface ReferenceInput {
    reference_string: string;
    description?: string;
}

export interface AddGenericTextRequest {
    generictext: GenericText;
    references: ReferenceInput[];
    /** Worauf die Hintergrundinfo antwortet: ID einer vorhandenen Aussage ... */
    statement_id?: string;
    /** ... oder, ohne ID, ihr Text; das Backend sucht oder legt sie an. */
    statement_text?: string;
    /** Mit Text: die Themen der Aussage (#455); eine vorhandene mit Themen behaelt ihre. */
    themen?: string[];
    /** Die Person hat diese vorhandene Hintergrundinfo (ID) gesehen und speichert trotzdem. */
    trotz_dublette_von?: string;
    /** Die Person nimmt diese eigene vorhandene Hintergrundinfo (ID): sie haengt dann an der Aussage. */
    vorhanden_nehmen?: string;
    /** "Als Vorlage nehmen" (#356): der Beitrag (ID), auf dem der neue beruht. */
    beruht_auf?: string;
}

export interface GenericText {
    text: string;
    title: string;
}

export interface GenericTextReference {
    reference_id: string;
    created: string;
    reference_text?: string;
    reference_description?: string;
}

export interface AddGenericTextResponse {
    id: string;
    /** Die Aussage, an der die Hintergrundinfo jetzt haengt; null ohne Aussage. */
    statement_id?: string | null;
    /** Text der tatsaechlich verknuepften Aussage (kann eine vorhandene, aehnliche sein). */
    statement_text?: string | null;
    /** true: Die Aussage kam per Text und wurde eben neu angelegt (Marke "neu" auf "Gespeichert", #617). */
    aussage_neu?: boolean;
    /** Kam die Aussage per Text mit Themen: die Themen, die sie jetzt hat (#455); sonst leer. */
    themen?: Thema[];
    /**
     * Ohne Dublette false: Aussage angegeben, aber nicht verknuepft - die Hintergrundinfo steht trotzdem.
     * Bei einer Dublette true nur, wenn die genommene vorhandene jetzt an der Aussage haengt; sonst false.
     */
    verknuepft?: boolean;
    /** Gesetzt: Es gibt schon einen sehr aehnlichen Beitrag (id: dessen ID), nichts angelegt; Titel und ob er von derselben Person ist. */
    vorhanden?: VorhandenDto | null;
}


// SearchGenericText
