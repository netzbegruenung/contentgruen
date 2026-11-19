/**
 * Eine begonnene Formulareingabe, solange die Person einwilligt (UX-Review B4): nur im
 * Arbeitsspeicher, nicht im Browser-Speicher (Entscheidung Maintainer 13.11.2026, bis
 * Paragraf 25 TDDDG geprueft ist). /einwilligung ist eine Route der App, der Entwurf
 * uebersteht also den Weg dorthin und zurueck; ein Neuladen nicht.
 *
 * Je Adresse der Seite ein Entwurf mit Zeitpunkt und einem Pruefwert des Kontos. Nach
 * ENTWURF_HOECHSTENS_MS wird er nicht mehr verwendet; weg ist er, sobald er wieder im
 * Formular steht, beim Abmelden und Kontowechsel (Art9EinwilligungService.starten),
 * spaetestens beim Neuladen.
 */

/** Frueher lagen Entwuerfe im sessionStorage unter diesem Praefix; die App raeumt sie einmal weg. */
export const ALTER_ENTWURF_PRAEFIX = 'gutgesagt-entwurf-vor-einwilligung:';

/** Laenger dauert der Umweg ueber die Einwilligung nicht; ein aelterer Entwurf faellt weg. */
export const ENTWURF_HOECHSTENS_MS = 60 * 60 * 1000;

interface Entwurf {
  zeit: number;
  /** Pruefwert der Kennung (FNV-1a), nicht die Kennung selbst; null ohne Anmeldung. */
  konto: number | null;
  werte: unknown;
}

const entwuerfe = new Map<string, Entwurf>();

/** FNV-1a wie im Profilbild-Dienst: klein, ohne Abhaengigkeit. */
export function kontoPruefwert(kennung: string | null | undefined): number | null {
  if (!kennung) return null;
  let wert = 0x811c9dc5;
  for (let i = 0; i < kennung.length; i++) {
    wert ^= kennung.charCodeAt(i);
    wert = Math.imul(wert, 0x01000193);
  }
  return wert >>> 0;
}

function abgelaufen(entwurf: Entwurf, jetzt: number): boolean {
  return jetzt - entwurf.zeit > ENTWURF_HOECHSTENS_MS || jetzt < entwurf.zeit;
}

/** Alte Entwuerfe aus dem sessionStorage (vor der Umstellung) wegraeumen. */
function alteEintraegeWeg(): void {
  try {
    const schluessel: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i);
      if (k?.startsWith(ALTER_ENTWURF_PRAEFIX)) schluessel.push(k);
    }
    schluessel.forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // Ohne Speicher gibt es auch keine alten Eintraege.
  }
}

/**
 * Abgelaufene Entwuerfe weg, und mit ``kennung`` auch die eines anderen Kontos; dazu
 * alte Eintraege im sessionStorage. Beim App-Start, beim Anmelden und vor jedem neuen Entwurf.
 */
export function entwuerfeAufraeumen(kennung: string | null = null, jetzt = Date.now()): void {
  alteEintraegeWeg();
  const konto = kontoPruefwert(kennung);
  for (const [adresse, entwurf] of entwuerfe) {
    if (abgelaufen(entwurf, jetzt) || (konto !== null && entwurf.konto !== konto)) entwuerfe.delete(adresse);
  }
}

export function entwurfSichern(adresse: string, werte: unknown, kennung: string | null, jetzt = Date.now()): void {
  entwuerfeAufraeumen(null, jetzt);
  entwuerfe.set(adresse, { zeit: jetzt, konto: kontoPruefwert(kennung), werte });
}

/**
 * Der Entwurf zu dieser Adresse, einmal: Gelesen wird er geloescht. Zu alt oder von
 * einem anderen Konto: undefined.
 */
export function entwurfHolen(adresse: string, kennung: string | null, jetzt = Date.now()): unknown {
  const entwurf = entwuerfe.get(adresse);
  entwuerfe.delete(adresse);
  if (!entwurf || abgelaufen(entwurf, jetzt) || entwurf.konto !== kontoPruefwert(kennung)) return undefined;
  return entwurf.werte;
}

/** Ob zu dieser Adresse ein Entwurf liegt (fuer Tests und Pruefungen). */
export function entwurfDa(adresse: string): boolean {
  return entwuerfe.has(adresse);
}

/** Alle Entwuerfe weg, etwa beim Abmelden oder Kontowechsel. */
export function entwuerfeLoeschen(): void {
  entwuerfe.clear();
}
