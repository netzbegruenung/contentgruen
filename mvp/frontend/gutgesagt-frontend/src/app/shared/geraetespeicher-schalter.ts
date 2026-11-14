import { InjectionToken } from '@angular/core';

/**
 * Schalter für Einträge, die die App auf dem Gerät der Person speichert und deren
 * Zulässigkeit nach § 25 TDDDG noch geprüft wird. Andere Funktionen legen ihre
 * Schalter in diese Datei.
 */

/**
 * Merker der angezeigten Meilensteine im localStorage (#351). Nach § 25 TDDDG geprüft am
 * 13.11.2026: fester Schlüssel ohne Angaben über die Person, gelöscht bei jedem An- und
 * Abmelden. Auf false: kein Zugriff auf den Speicher dafür, keine Meilenstein-Hinweise
 * und kein Absatz dazu in der Datenschutzerklärung.
 */
export const MEILENSTEIN_MERKER_AKTIV = true;

/** Derselbe Schalter zum Einspritzen, damit Tests beide Stellungen prüfen können. */
export const MEILENSTEIN_MERKER = new InjectionToken<boolean>('MEILENSTEIN_MERKER', {
  providedIn: 'root',
  factory: () => MEILENSTEIN_MERKER_AKTIV,
});
