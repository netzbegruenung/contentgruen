/**
 * Der Sofort-Dank nach einer Stimme (Entscheidung Maintainer 20.11.2026), an einer Stelle.
 * Er kommt als Snackbar wie beim Kopieren, nicht in der Karte: Die Karte behält ihre Größe.
 *
 * Stimmen gehen erst ab einer Mindestzahl verschiedener Stimmender in die Güte ein (DSFA,
 * Maßnahme M5; domain/guete.py). Darunter tut sich nach der ersten Stimme nichts
 * Sichtbares; der Dank sagt deshalb, dass die Stimme zählt, sobald genug zusammenkommen.
 *
 * Ob ein Beitrag unter der Schwelle liegt, weiß die Karte schon: Die Antwort trägt
 * `guete_stimmen_zaehlen` an jedem Beitrag, für alle, die ihn sehen. Der Dank braucht also
 * keine neue Angabe vom Server und verrät nichts, was die Karte nicht ohnehin zeigt.
 * Maßgeblich ist der Stand vor der Stimme: War der Beitrag darunter, ist die Person unter
 * den ersten drei, auch wenn ihre Stimme gerade die dritte war, und der Satz stimmt weiter.
 */

/**
 * Ab so vielen verschiedenen Stimmenden zählen Stimmen. Spiegelt den Standard von
 * `SEMANTIC_SEARCH_GUETE_STIMMEN_AB` (core/config.py); wer ihn ändert, ändert ihn hier mit.
 */
export const STIMMEN_AB = 3;

/** So lange steht der Dank. */
export const STIMM_DANK_MS = 6000;

/** Ein Dank: dekoratives Symbol (Screenreader lesen es nicht) und Text, getrennt. */
export interface StimmDank {
  icon: string;
  text: string;
}

/** Unter der Schwelle: positiv, die Person ist unter den Ersten. */
export const DANK_UNTER_DEN_ERSTEN: StimmDank = {
  icon: '🌱',
  text: `Danke! Du bist unter den Ersten. Ab ${STIMMEN_AB} Stimmen zählt sie.`,
};

/** Ab der Schwelle: kurz. */
export const DANK_ZAEHLT: StimmDank = { icon: '👍', text: 'Danke! Deine Stimme zählt.' };

/** Ohne Angabe zur Güte (etwa eine ältere Antwort): ohne Aussage über die Güte. */
export const DANK_SCHLICHT: StimmDank = { icon: '👍', text: 'Danke für deine Stimme!' };

/** Am eigenen Beitrag: Die eigene Stimme zählt nie in die Güte (guete_service.py). */
export const DANK_EIGENER_BEITRAG: StimmDank = { icon: '✔️', text: 'Gespeichert. Eigene Stimmen zählen nicht.' };

/**
 * Der Dank zu einer gesetzten Stimme. ``stimmenZaehlen``: der Stand an der Karte vor der
 * Stimme, null = unbekannt. ``eigenerBeitrag``: die Person hat den Beitrag geschrieben.
 */
export function stimmDank(stimmenZaehlen: boolean | null, eigenerBeitrag: boolean): StimmDank {
  if (eigenerBeitrag) {
    return DANK_EIGENER_BEITRAG;
  }
  if (stimmenZaehlen === null) {
    return DANK_SCHLICHT;
  }
  return stimmenZaehlen ? DANK_ZAEHLT : DANK_UNTER_DEN_ERSTEN;
}
