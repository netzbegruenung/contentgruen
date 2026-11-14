/**
 * Wann das Siegel Glanz trägt (#351, GLOSSARY.md „Siegel“).
 *
 * Glanz zeichnet den Beitrag aus: Er hat viel Wirkung, gemessen am Zähler der Karte,
 * den alle sehen. Er betrifft keine Person und erscheint deshalb auch Besuchern.
 * Was die Person auszeichnet, steht am Namen (Abzeichen), nicht am Siegel (Entscheidung 14.11.).
 */

/** Ab so vielen Nutzungen glänzt das Siegel; „Beliebt“ (🔥) kommt schon früher. */
export const GLANZ_AB = 25;

export function hatGlanz(nutzung: number | null | undefined): boolean {
  return (nutzung ?? 0) >= GLANZ_AB;
}

export const GLANZ_TEXT = `Glanz: Der Beitrag wurde mindestens ${GLANZ_AB}-mal genutzt.`;
