/**
 * Was sich der Browser für Willkommen und Rundgang merkt (#389): nur, dass ein Angebot
 * schon beantwortet wurde (Rundgang gestartet oder ausgeblendet, #587). Kein
 * Server-Eintrag, keine Zählung, nichts über die Person. Fehlt der Speicher (privates
 * Fenster, gesperrt), merkt sich nur der laufende Besuch die Antwort: Beim nächsten
 * Besuch erscheint das Angebot wieder.
 */
export const WILLKOMMEN_SCHLUESSEL = 'gutgesagt-willkommen-gesehen';
export const MITMACHEN_SCHLUESSEL = 'gutgesagt-mitmachen-angeboten';
/**
 * Hinweis „Gut gesagt als App“ auf iPhone und iPad: ausgeblendet bzw. schon einmal hier
 * gewesen. Nur dort im Browser geschrieben und nur bei HOME_HINWEIS_MERKER (§ 25 TDDDG).
 */
export const HOME_HINWEIS_SCHLUESSEL = 'gutgesagt-home-hinweis-ausgeblendet';
export const SCHON_DA_SCHLUESSEL = 'gutgesagt-schon-da-gewesen';

export function gesehen(schluessel: string): boolean {
  try {
    return localStorage.getItem(schluessel) === '1';
  } catch {
    return false;
  }
}

/** true, wenn der Browser den Merker angenommen hat. */
export function merken(schluessel: string): boolean {
  try {
    localStorage.setItem(schluessel, '1');
    return true;
  } catch {
    // Ohne Speicher kommt das Angebot beim nächsten Besuch wieder; mehr passiert nicht.
    return false;
  }
}
