/**
 * Wohin es nach dem Anmelden zurueckgeht. Liegt im sessionStorage, weil der Weg ueber
 * die Login-Seiten und Keycloak die Adresse nicht immer mitnimmt. Das ist an die
 * Handlung "Anmelden" gebunden; ohne echtes Ziel (Startseite, Login-Seite) wird
 * nichts abgelegt. Ein gesperrter Storage (privater Modus, blockierte Seitendaten)
 * wirft nicht, das Ziel gilt dann eben nicht ueber den Umweg.
 */
export const RUECKKEHRZIEL_SCHLUESSEL = 'loginReturnUrl';

function istZiel(url: string | null): url is string {
  return !!url && url !== '/' && !url.startsWith('/login');
}

export function rueckkehrzielLesen(): string | null {
  try {
    const gespeichert = sessionStorage.getItem(RUECKKEHRZIEL_SCHLUESSEL);
    return istZiel(gespeichert) ? gespeichert : null;
  } catch {
    return null;
  }
}

/** Merkt sich `url`; ist sie kein Ziel, wird ein altes verworfen statt "/" abzulegen. */
export function rueckkehrzielMerken(url: string): void {
  if (!istZiel(url)) {
    rueckkehrzielLoeschen();
    return;
  }
  try {
    sessionStorage.setItem(RUECKKEHRZIEL_SCHLUESSEL, url);
  } catch {
    // Ohne Storage traegt nur noch der Parameter returnUrl das Ziel.
  }
}

export function rueckkehrzielLoeschen(): void {
  try {
    sessionStorage.removeItem(RUECKKEHRZIEL_SCHLUESSEL);
  } catch {
    // Ohne Zugriff auf den Storage liegt dort auch nichts zum Loeschen.
  }
}
