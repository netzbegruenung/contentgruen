/**
 * Das Wort fuer eine unbeantwortete Aussage aus „Hier fehlt eine Antwort“ in den Texten
 * zur Wirkung (Nutzerfuehrung 13.11.). Ob es bei „Lücke“ bleibt, ist offen: Im Glossar
 * heisst so auch die Platzhalter-Klammer im Text. Getauscht wird nur hier.
 */
export const LUECKE = { einzahl: 'Lücke', mehrzahl: 'Lücken' } as const;

/** „Lücke zu.“ auf der Ergebnisseite. */
export const LUECKE_ZU = `${LUECKE.einzahl} zu.`;

/** Der Hauptknopf danach. */
export const NAECHSTE_LUECKE = `Nächste ${LUECKE.einzahl}`;

/** Startseite: „3 Lücken warten auf eine Antwort“. */
export function lueckenWarten(anzahl: number): string {
  return anzahl === 1
    ? `1 ${LUECKE.einzahl} wartet auf eine Antwort`
    : `${anzahl} ${LUECKE.mehrzahl} warten auf eine Antwort`;
}
