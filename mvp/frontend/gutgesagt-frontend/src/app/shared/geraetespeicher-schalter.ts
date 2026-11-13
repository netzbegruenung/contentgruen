import { InjectionToken } from '@angular/core';

/**
 * Schalter fuer Eintraege, die die App ueber das Schliessen hinaus im Browser ablegt und
 * deren Einordnung nach § 25 TDDDG (unbedingt erforderlich oder einwilligungspflichtig)
 * noch offen ist. Ein Schalter je Eintrag; aus heisst: kein Lesen, kein Schreiben, und
 * die Funktion, die ihn braucht, entfaellt.
 */

/**
 * „Seit deinem letzten Besuch“ auf der Startseite (Merker `gutgesagt-letzter-besuch-…`).
 * Erst nach juristischer Pruefung (§ 25 TDDDG) auf true; mit dem Schalter erscheint auch
 * der Absatz dazu in der Datenschutzerklaerung (Entscheidung 13.11.).
 */
export const LETZTER_BESUCH_AKTIV = false;

/** Der Schalter fuer Komponenten; Tests stellen ihn per Provider um. */
export const LETZTER_BESUCH_AN = new InjectionToken<boolean>('LETZTER_BESUCH_AN', {
  providedIn: 'root',
  factory: () => LETZTER_BESUCH_AKTIV,
});
