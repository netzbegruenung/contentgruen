import { FORMULAR_PFAD } from '../shared/formular-adresse';

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

/**
 * Der Satz über der Login-Auswahl, der sagt, wozu die Anmeldung nötig ist (#600): nur für
 * die Formulare, die auf eine Aussage antworten, also das Ziel von „Antworten“.
 * Für andere Ziele, auch nach Klick auf „Anmelden“ im Kopf, steht kein Satz.
 */
export function anmeldegrund(ziel: string): string | null {
  const pfad = ziel.split(/[?#]/)[0];
  const antwortFormulare = [FORMULAR_PFAD.commentary, FORMULAR_PFAD.generictext];
  return antwortFormulare.includes(pfad) ? 'Zum Beantworten melde dich an.' : null;
}
