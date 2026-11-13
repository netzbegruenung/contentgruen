/**
 * Eine begonnene Formulareingabe, solange die Person einwilligt (UX-Review B4): im
 * sessionStorage unter Praefix plus Adresse der Seite, mit Zeitpunkt. Nur dieser Tab,
 * nichts geht an den Server. Ein Entwurf verfällt nach ENTWURF_HOECHSTENS_MS und wird
 * beim Abmelden und beim Kontowechsel gelöscht (Art9EinwilligungService.starten), damit
 * kein Text von vor der Einwilligung länger liegen bleibt als nötig.
 */
export const ENTWURF_PRAEFIX = 'gutgesagt-entwurf-vor-einwilligung:';

/** Länger dauert der Umweg über die Einwilligung nicht; ein älterer Entwurf fällt weg. */
export const ENTWURF_HOECHSTENS_MS = 60 * 60 * 1000;

interface Entwurf {
  zeit: number;
  werte: unknown;
}

export function entwurfSichern(adresse: string, werte: unknown, jetzt = Date.now()): void {
  try {
    sessionStorage.setItem(ENTWURF_PRAEFIX + adresse, JSON.stringify({ zeit: jetzt, werte } satisfies Entwurf));
  } catch {
    // Ohne Speicher geht nur die Eingabe verloren; der Weg zur Einwilligung klappt.
  }
}

/** Der Entwurf zu dieser Adresse, einmal: Gelesen wird er gelöscht. Zu alt oder kaputt: undefined. */
export function entwurfHolen(adresse: string, jetzt = Date.now()): unknown {
  let gelesen: Partial<Entwurf> | null;
  try {
    const wert = sessionStorage.getItem(ENTWURF_PRAEFIX + adresse);
    if (!wert) return undefined;
    sessionStorage.removeItem(ENTWURF_PRAEFIX + adresse);
    gelesen = JSON.parse(wert);
  } catch {
    return undefined;
  }
  if (!gelesen || typeof gelesen !== 'object' || typeof gelesen.zeit !== 'number') return undefined;
  if (jetzt - gelesen.zeit > ENTWURF_HOECHSTENS_MS || jetzt < gelesen.zeit) return undefined;
  return gelesen.werte;
}

/** Alle Entwürfe weg, etwa beim Abmelden oder Kontowechsel. */
export function entwuerfeLoeschen(): void {
  try {
    const schluessel: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i);
      if (k?.startsWith(ENTWURF_PRAEFIX)) schluessel.push(k);
    }
    schluessel.forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // Ohne Speicher gibt es auch keine Entwürfe.
  }
}
