
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
    /** false: Aussage angegeben, aber nicht verknuepft - die Hintergrundinfo steht trotzdem. */
    verknuepft?: boolean;
}


// SearchGenericText
