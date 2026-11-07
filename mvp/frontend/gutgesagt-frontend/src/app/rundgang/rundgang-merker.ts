/**
 * Was sich der Browser für Willkommen und Rundgang merkt (#389): nur, dass ein Angebot
 * schon beantwortet wurde (Rundgang gestartet oder ausgeblendet, #587). Kein
 * Server-Eintrag, keine Zählung, nichts über die Person. Fehlt der Speicher (privates
 * Fenster, gesperrt), merkt sich nur der laufende Besuch die Antwort: Beim nächsten
 * Besuch erscheint das Angebot wieder.
 */
export const WILLKOMMEN_SCHLUESSEL = 'gutgesagt-willkommen-gesehen';
export const MITMACHEN_SCHLUESSEL = 'gutgesagt-mitmachen-angeboten';

export function gesehen(schluessel: string): boolean {
  try {
    return localStorage.getItem(schluessel) === '1';
  } catch {
    return false;
  }
}

export function merken(schluessel: string): void {
  try {
    localStorage.setItem(schluessel, '1');
  } catch {
    // Ohne Speicher kommt das Angebot beim nächsten Besuch wieder; mehr passiert nicht.
  }
}
