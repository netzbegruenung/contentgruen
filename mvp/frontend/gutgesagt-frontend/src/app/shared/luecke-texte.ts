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

/**
 * Startseite: „3 Lücken warten auf eine Antwort“; hat die Liste ihre Grenze erreicht
 * (`mehr`), „50+ Lücken …“.
 */
export function lueckenWarten(anzahl: number, mehr = false): string {
  if (mehr) {
    return `${anzahl}+ ${LUECKE.mehrzahl} warten auf eine Antwort`;
  }
  return anzahl === 1
    ? `1 ${LUECKE.einzahl} wartet auf eine Antwort`
    : `${anzahl} ${LUECKE.mehrzahl} warten auf eine Antwort`;
}
