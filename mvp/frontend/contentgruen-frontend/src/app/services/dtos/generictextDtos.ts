
//TODO: Evaluate usage of camel case and transformation in the backend




// AddGenericText

export interface ReferenceInput {
    reference_string: string;
    description?: string;
}

export interface AddGenericTextRequest {
    generictext: GenericText;
    references: ReferenceInput[];
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
}


// SearchGenericText
