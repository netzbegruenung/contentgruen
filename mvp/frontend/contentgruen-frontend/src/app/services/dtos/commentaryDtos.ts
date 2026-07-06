
//TODO: Evaluate usage of camel case and transformation in the backend




// AddCommentary

export interface ReferenceInput {
    reference_string: string;
    description?: string;
}

export interface AddCommentaryRequest {
    commentary: Commentary
    references: ReferenceInput[];
}

export interface Commentary {
    text: string;
    title: string;
    long_text: string;
    short_text: string;
    references: CommentaryReference[];
}

export interface CommentaryReference {
    reference_id: string;
    created: string;
}

export interface AddCommentaryResponse {
    id: string;
}



// SearchCommentary
