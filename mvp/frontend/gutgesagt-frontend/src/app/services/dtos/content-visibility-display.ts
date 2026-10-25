import { ContentVisibility } from "./content-visibility-enum";

export const ContentVisibilityIcons: Record<ContentVisibility, string> = {
    [ContentVisibility.VISIBLE]: '👁️',
    [ContentVisibility.HIDDEN]: '🚫',
    [ContentVisibility.INTERNAL]: '🏢',
    [ContentVisibility.RESTRICTED]: '🔒',
};

export const ContentVisibilityStrings: Record<ContentVisibility, string> = {
    [ContentVisibility.VISIBLE]: 'Sichtbar',
    [ContentVisibility.HIDDEN]: 'Versteckt',
    [ContentVisibility.INTERNAL]: 'Grün-Intern',
    [ContentVisibility.RESTRICTED]: 'Eingeschränkt',
};
