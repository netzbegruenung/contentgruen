
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
}

export interface Commentary {
    text: string;
    title: string;
    /** Nicht mehr im Formular; aeltere Eintraege koennen sie tragen. */
    long_text?: string;
    short_text?: string;
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
    /** false: Aussage angegeben, aber nicht verknuepft - der Kommentar steht trotzdem. */
    verknuepft?: boolean;
}



// SearchCommentary
