import { HINTERGRUNDINFO_TEXT_MAX, KOMMENTAR_TEXT_MAX } from '../shared/beitrag-grenzen';

/**
 * Die Beitragstypen, die der Autor aendern kann (#299), mit der Grenze ihres Texts wie beim
 * Anlegen. Eigene Datei, damit die Karte fragen kann, ohne den Dialog mitzuladen.
 */
export const AENDERBARE_TYPEN: Readonly<Record<string, number>> = {
  commentary: KOMMENTAR_TEXT_MAX,
  generictext: HINTERGRUNDINFO_TEXT_MAX,
};

export function istAenderbar(typ: string | null): boolean {
  return typ !== null && typ in AENDERBARE_TYPEN;
}
