/**
 * Eine begonnene Formulareingabe, solange die Person einwilligt (UX-Review B4): im
 * sessionStorage unter Praefix plus Adresse der Seite, mit Zeitpunkt und einem Pruefwert
 * des Kontos. Nur dieser Tab, nichts geht an den Server.
 *
 * Nach ENTWURF_HOECHSTENS_MS wird ein Entwurf nicht mehr verwendet. Geloescht wird er,
 * sobald er wieder im Formular steht, beim naechsten Ablegen eines Entwurfs und beim
 * App-Start (abgelaufene und die eines anderen Kontos), beim Abmelden und Kontowechsel
 * (Art9EinwilligungService.starten), spaetestens wenn der Tab schliesst.
 */
export const ENTWURF_PRAEFIX = 'gutgesagt-entwurf-vor-einwilligung:';

/** Laenger dauert der Umweg ueber die Einwilligung nicht; ein aelterer Entwurf faellt weg. */
export const ENTWURF_HOECHSTENS_MS = 60 * 60 * 1000;

interface Entwurf {
  zeit: number;
  /** Pruefwert der Kennung (FNV-1a), nicht die Kennung selbst; null ohne Anmeldung. */
  konto: number | null;
  werte: unknown;
}

/** FNV-1a wie im Profilbild-Dienst: klein, ohne Abhaengigkeit, nicht umkehrbar gemeint. */
export function kontoPruefwert(kennung: string | null | undefined): number | null {
  if (!kennung) return null;
  let wert = 0x811c9dc5;
  for (let i = 0; i < kennung.length; i++) {
    wert ^= kennung.charCodeAt(i);
    wert = Math.imul(wert, 0x01000193);
  }
  return wert >>> 0;
}

function lesen(schluessel: string): Partial<Entwurf> | null {
  try {
    const wert = JSON.parse(sessionStorage.getItem(schluessel) ?? 'null');
    return wert && typeof wert === 'object' ? wert : null;
  } catch {
    return null;
  }
}

function abgelaufen(entwurf: Partial<Entwurf> | null, jetzt: number): boolean {
  return (
    !entwurf ||
    typeof entwurf.zeit !== 'number' ||
    jetzt - entwurf.zeit > ENTWURF_HOECHSTENS_MS ||
    jetzt < entwurf.zeit
  );
}

function alleSchluessel(): string[] {
  const schluessel: string[] = [];
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i);
      if (k?.startsWith(ENTWURF_PRAEFIX)) schluessel.push(k);
    }
  } catch {
    // Ohne Speicher gibt es auch keine Entwuerfe.
  }
  return schluessel;
}

function entfernen(schluessel: string): void {
  try {
    sessionStorage.removeItem(schluessel);
  } catch {
    // Ohne Speicher nichts zu entfernen.
  }
}

/**
 * Abgelaufene Entwuerfe weg, und mit ``kennung`` auch die eines anderen Kontos. Beim
 * App-Start und vor jedem neuen Entwurf.
 */
export function entwuerfeAufraeumen(kennung: string | null = null, jetzt = Date.now()): void {
  const konto = kontoPruefwert(kennung);
  for (const schluessel of alleSchluessel()) {
    const entwurf = lesen(schluessel);
    const fremd = konto !== null && entwurf?.konto !== konto;
    if (abgelaufen(entwurf, jetzt) || fremd) entfernen(schluessel);
  }
}

export function entwurfSichern(adresse: string, werte: unknown, kennung: string | null, jetzt = Date.now()): void {
  entwuerfeAufraeumen(null, jetzt);
  try {
    const entwurf: Entwurf = { zeit: jetzt, konto: kontoPruefwert(kennung), werte };
    sessionStorage.setItem(ENTWURF_PRAEFIX + adresse, JSON.stringify(entwurf));
  } catch {
    // Ohne Speicher geht nur die Eingabe verloren; der Weg zur Einwilligung klappt.
  }
}

/**
 * Der Entwurf zu dieser Adresse, einmal: Gelesen wird er geloescht. Zu alt, von einem
 * anderen Konto oder kaputt: undefined.
 */
export function entwurfHolen(adresse: string, kennung: string | null, jetzt = Date.now()): unknown {
  const schluessel = ENTWURF_PRAEFIX + adresse;
  const entwurf = lesen(schluessel);
  entfernen(schluessel);
  if (!entwurf || abgelaufen(entwurf, jetzt) || entwurf.konto !== kontoPruefwert(kennung)) return undefined;
  return entwurf.werte;
}

/** Alle Entwuerfe weg, etwa beim Abmelden oder Kontowechsel. */
export function entwuerfeLoeschen(): void {
  alleSchluessel().forEach(entfernen);
}
