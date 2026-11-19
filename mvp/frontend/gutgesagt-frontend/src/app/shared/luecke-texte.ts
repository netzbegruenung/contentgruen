/**
 * Das Wort fuer eine unbeantwortete Aussage aus „Hier fehlt eine Antwort“ in den Texten
 * zur Wirkung (Nutzerfuehrung 13.11.; GLOSSARY „Lücke“). Die Stelle „[Hier …]“ im Text
 * heisst seit 13.11. „Platzhalter“. Soll das Wort sich aendern, nur hier tauschen.
 */
export const LUECKE = { einzahl: 'Lücke', mehrzahl: 'Lücken' } as const;

/** „Lücke zu.“ auf der Ergebnisseite. */
export const LUECKE_ZU = `${LUECKE.einzahl} zu.`;

/** Der Hauptknopf danach. */
export const NAECHSTE_LUECKE = `Nächste ${LUECKE.einzahl}`;
