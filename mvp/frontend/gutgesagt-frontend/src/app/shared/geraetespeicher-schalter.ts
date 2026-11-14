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

/**
 * Hinweis „Gut gesagt als App“ auf iPhone und iPad (14.11.2026): zwei Merker im
 * localStorage, „schon einmal hier gewesen“ und „ausgeblendet“, ohne Angaben über die
 * Person, nur auf diesen Geräten im Browser geschrieben. Als Komfortfunktion nach § 25
 * Abs. 2 Nr. 2 TDDDG ohne Einwilligung. Aus, bis die Datenschutzerklärung die beiden
 * Merker nennt (dort stehen bisher nur Willkommen und Mitmachen). Auf false: kein Zugriff
 * auf den Speicher dafür und kein Hinweis.
 */
export const HOME_HINWEIS_MERKER_AKTIV = false;

export const HOME_HINWEIS_MERKER = new InjectionToken<boolean>('HOME_HINWEIS_MERKER', {
  providedIn: 'root',
  factory: () => HOME_HINWEIS_MERKER_AKTIV,
});
