/**
 * Schluessel, unter denen die SPA bis #446 eine Sitzungskennung fuer 30 Tage im
 * localStorage ablegte. Besucher erkennt seitdem der Server an einem
 * Tagespseudonym; im Browser liegt keine Kennung mehr. Das Aufraeumen kann
 * entfallen, wenn die letzte so abgelegte Kennung abgelaufen waere (30 Tage nach
 * dem Ausrollen von #446).
 */
const ALTE_SCHLUESSEL: readonly string[] = [
  'gutgesagt_session_id',
  'gutgesagt_session_id_created_at',
];

/** Den sicheren Zugriff auf localStorage: ohne Storage (gesperrt) null. */
function lokalerSpeicher(): Storage | null {
  try {
    return localStorage;
  } catch {
    return null;
  }
}

/** Entfernt die alte Sitzungskennung aus dem Browser; scheitert nie. */
export function alteSitzungskennungEntfernen(speicher: Storage | null = lokalerSpeicher()): void {
  if (!speicher) {
    return;
  }
  for (const schluessel of ALTE_SCHLUESSEL) {
    try {
      speicher.removeItem(schluessel);
    } catch {
      // Gesperrter Speicher: dann liegt dort auch nichts, das wir lesen wuerden.
    }
  }
}
