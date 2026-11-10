/**
 * Wann das Siegel Glanz und Krone trägt (#351, GLOSSARY.md „Siegel“).
 *
 * Glanz zeichnet den Beitrag aus: Er hat viel Wirkung, gemessen am Zähler der Karte,
 * den alle sehen. Er betrifft keine Person und erscheint deshalb auch Besuchern.
 *
 * Die Krone zeichnet die Person aus: Sie steht nur, wenn der Server ein
 * Meilenstein-Abzeichen der Autorin mitschickt, also nur für Angemeldete, nur mit ihrer
 * Zustimmung zur Sichtbarkeit und nur bei eingeschalteten Abzeichen (ADR 0004).
 */

/** Ab so vielen Nutzungen glänzt das Siegel; „Beliebt“ (🔥) kommt schon früher. */
export const GLANZ_AB = 25;

/** Ab so vielen erreichten Meilensteinen der Autorin trägt das Siegel eine Krone. */
export const KRONE_AB = 5;

export function hatGlanz(nutzung: number | null | undefined): boolean {
  return (nutzung ?? 0) >= GLANZ_AB;
}

/** `abzeichen` ist nur gesetzt, wenn die Autorin der Sichtbarkeit zugestimmt hat. */
export function hatKrone(abzeichen: number | null | undefined): boolean {
  return (abzeichen ?? 0) >= KRONE_AB;
}

export const GLANZ_TEXT = `Glanz: Der Beitrag wurde mindestens ${GLANZ_AB}-mal genutzt.`;
export const KRONE_TEXT = `Krone: Die Person dahinter hat mindestens ${KRONE_AB} Meilensteine erreicht.`;
