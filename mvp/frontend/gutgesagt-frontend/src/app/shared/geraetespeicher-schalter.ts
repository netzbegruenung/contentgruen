import { InjectionToken } from '@angular/core';

/**
 * Schalter für Einträge, die die App auf dem Gerät der Person speichert und deren
 * Zulässigkeit nach § 25 TDDDG noch geprüft wird. Andere Funktionen legen ihre
 * Schalter in diese Datei.
 */

/**
 * Merker der angezeigten Meilensteine im localStorage (#351). Erst nach juristischer
 * Prüfung (§ 25 TDDDG) auf true; bis dahin kein Zugriff auf den Speicher dafür, keine
 * Meilenstein-Hinweise und kein Absatz dazu in der Datenschutzerklärung.
 */
export const MEILENSTEIN_MERKER_AKTIV = false;

/** Derselbe Schalter zum Einspritzen, damit Tests beide Stellungen prüfen können. */
export const MEILENSTEIN_MERKER = new InjectionToken<boolean>('MEILENSTEIN_MERKER', {
  providedIn: 'root',
  factory: () => MEILENSTEIN_MERKER_AKTIV,
});
