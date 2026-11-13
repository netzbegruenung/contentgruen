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

/** Der Merker eines Kontos: die angezeigten Kennungen und ob es schon einen Eintrag gibt. */
export interface Merker {
  gesehen: Set<string>;
  vorhanden: boolean;
}

/**
 * Der Merker, oder null ohne Konto oder ohne Speicher (privates Fenster, gesperrt).
 * Ohne Speicher gibt es keinen Hinweis: Er käme sonst jedes Mal.
 */
export function merkerLesen(kennung: string | null): Merker | null {
  if (!kennung) {
    return null;
  }
  try {
    const roh = localStorage.getItem(merkerSchluessel(kennung));
    const liste: unknown = roh ? JSON.parse(roh) : [];
    const gesehen = new Set(Array.isArray(liste) ? liste.filter((k): k is string => typeof k === 'string') : []);
    return { gesehen, vorhanden: roh !== null };
  } catch {
    return null;
  }
}

/** Die schon angezeigten Kennungen, oder null ohne Konto oder ohne Speicher. */
export function gesehenLesen(kennung: string | null): Set<string> | null {
  return merkerLesen(kennung)?.gesehen ?? null;
}

/**
 * Diese Meilensteine als angezeigt merken. Geschrieben wird nur, wenn es Meilensteine
 * gibt (also Punkte an und eingewilligt) und dabei etwas Erreichtes neu ist, oder
 * einmal zum Anlegen des Eintrags: Ohne Eintrag gilt alles schon Erreichte still als
 * gesehen (merkerAnlegen). Ohne Konto oder Speicher passiert nichts.
 */
export function gesehenMerken(kennung: string | null, meilensteine: Meilenstein[]): void {
  const merker = merkerLesen(kennung);
  if (!merker || !kennung || !meilensteine.length) {
    return;
  }
  const neu = meilensteine.filter((m) => m.erreicht && !merker.gesehen.has(m.kennung));
  if (!neu.length && merker.vorhanden) {
    return;
  }
  neu.forEach((m) => merker.gesehen.add(m.kennung));
  try {
    localStorage.setItem(merkerSchluessel(kennung), JSON.stringify([...merker.gesehen]));
  } catch {
    // Ohne Speicher kein Merker; der Hinweis bleibt dann ganz aus (merkerLesen).
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
