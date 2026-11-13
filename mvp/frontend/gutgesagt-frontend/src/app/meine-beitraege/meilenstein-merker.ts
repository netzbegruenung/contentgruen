import type { Meilenstein } from '../services/usage-tracking.service';

/**
 * Welche erreichten Meilensteine dem Konto in diesem Browser schon angezeigt wurden
 * (#351): eine Liste der Kennungen im localStorage, je Konto unter einem eigenen
 * Schlüssel. Der Schlüssel trägt einen Prüfwert der Kennung, nicht die Kennung selbst,
 * damit sich zwei Konten im selben Browser nicht vermischen. Beim Abmelden und beim
 * Widerruf der Art.-9-Einwilligung wird der Eintrag entfernt (merkerEntfernen).
 * Nichts davon geht an den Server.
 */
export const MEILENSTEINE_GESEHEN_PRAEFIX = 'gutgesagt-meilensteine-gesehen-';

/** FNV-1a über die Kennung, 32 Bit hexadezimal: genügt zum Trennen, ist kein Geheimnis. */
export function merkerSchluessel(kennung: string): string {
  let wert = 0x811c9dc5;
  for (let i = 0; i < kennung.length; i++) {
    wert ^= kennung.charCodeAt(i);
    wert = Math.imul(wert, 0x01000193) >>> 0;
  }
  return MEILENSTEINE_GESEHEN_PRAEFIX + wert.toString(16).padStart(8, '0');
}

/**
 * Die schon angezeigten Kennungen, oder null ohne Konto oder ohne Speicher (privates
 * Fenster, gesperrt). Ohne Speicher gibt es keinen Hinweis: Er käme sonst jedes Mal.
 */
export function gesehenLesen(kennung: string | null): Set<string> | null {
  if (!kennung) {
    return null;
  }
  try {
    const roh = localStorage.getItem(merkerSchluessel(kennung));
    const liste: unknown = roh ? JSON.parse(roh) : [];
    return new Set(Array.isArray(liste) ? liste.filter((k): k is string => typeof k === 'string') : []);
  } catch {
    return null;
  }
}

/** Diese Meilensteine als angezeigt merken; ohne Konto oder Speicher passiert nichts. */
export function gesehenMerken(kennung: string | null, meilensteine: Meilenstein[]): void {
  const gesehen = gesehenLesen(kennung);
  if (!gesehen || !kennung) {
    return;
  }
  meilensteine.filter((m) => m.erreicht).forEach((m) => gesehen.add(m.kennung));
  try {
    localStorage.setItem(merkerSchluessel(kennung), JSON.stringify([...gesehen]));
  } catch {
    // Ohne Speicher kein Merker; der Hinweis bleibt dann ganz aus (gesehenLesen).
  }
}

/** Beim Abmelden und beim Widerruf: den Eintrag des Kontos entfernen. */
export function merkerEntfernen(kennung: string | null): void {
  if (!kennung) {
    return;
  }
  try {
    localStorage.removeItem(merkerSchluessel(kennung));
  } catch {
    // Ohne Speicher gibt es nichts zu entfernen.
  }
}
