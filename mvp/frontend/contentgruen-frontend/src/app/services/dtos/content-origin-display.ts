import { ContentOrigin } from "./content-origin-enum";

export const ContentOriginIcons: Record<ContentOrigin, string> = {
    [ContentOrigin.INITIAL_DATA]: '🌱',
    [ContentOrigin.MANUALLY_CREATED]: '✍️',
    [ContentOrigin.AI_GENERATED]: '🤖',
    [ContentOrigin.INGESTED]: '📥',
};

export const ContentOriginStrings: Record<ContentOrigin, string> = {
    [ContentOrigin.INITIAL_DATA]: 'Initialdaten',
    [ContentOrigin.MANUALLY_CREATED]: 'Manuell erstellt',
    [ContentOrigin.AI_GENERATED]: 'KI generiert',
    [ContentOrigin.INGESTED]: 'Importiert',
};
