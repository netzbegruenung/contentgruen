import type { Meilenstein } from '../services/usage-tracking.service';

/**
 * Welche erreichten Meilensteine in diesem Browser schon angezeigt wurden (#351): eine
 * Liste der Kennungen der Meilensteine im localStorage unter einem festen Schlüssel,
 * ohne Angaben über die Person. Getrennt nach Konten wird nur dadurch, dass der Eintrag
 * bei jedem Anmelden (MeilensteinHinweisService.anmeldung) und beim Abmelden gelöscht
 * wird, dazu beim Widerruf der Art.-9-Einwilligung. Nichts davon geht an den Server.
 * Geprüft nach § 25 TDDDG am 13.11.2026 in dieser Form (ohne Prüfwert der Kennung).
 */
export const MEILENSTEINE_GESEHEN_SCHLUESSEL = 'gutgesagt-meilensteine-gesehen';

/** Der Merker: die angezeigten Kennungen und ob es schon einen Eintrag gibt. */
export interface Merker {
  gesehen: Set<string>;
  vorhanden: boolean;
}

/**
 * Der Merker, oder null ohne Anmeldung oder ohne Speicher (privates Fenster, gesperrt).
 * Ohne Speicher gibt es keinen Hinweis: Er käme sonst jedes Mal.
 */
export function merkerLesen(kennung: string | null): Merker | null {
  if (!kennung) {
    return null;
  }
  try {
    const roh = localStorage.getItem(MEILENSTEINE_GESEHEN_SCHLUESSEL);
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
 * gesehen (MeilensteinHinweisService.neueErreichte). Ohne Anmeldung oder Speicher
 * passiert nichts.
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
    localStorage.setItem(MEILENSTEINE_GESEHEN_SCHLUESSEL, JSON.stringify([...merker.gesehen]));
  } catch {
    // Ohne Speicher kein Merker; der Hinweis bleibt dann ganz aus (merkerLesen).
  }
}

/** Bei jedem Anmelden, beim Abmelden und beim Widerruf: den Eintrag entfernen. */
export function merkerEntfernen(): void {
  try {
    localStorage.removeItem(MEILENSTEINE_GESEHEN_SCHLUESSEL);
  } catch {
    // Ohne Speicher gibt es nichts zu entfernen.
  }
}
