/**
 * Wann das Siegel Glanz trägt (#351, GLOSSARY.md „Siegel“).
 *
 * Glanz zeichnet den Beitrag aus: Er hat viel Wirkung, gemessen am Zähler der Karte,
 * den alle sehen. Er betrifft keine Person und erscheint deshalb auch Besuchern.
 *
 * Eine Krone für die Person gibt es am Siegel nicht mehr: Sie beschrieb die Autorin, nicht
 * den Beitrag (Entscheidung 14.11.). Die Meilensteine stehen weiter als Abzeichen am Namen.
 */

/** Ab so vielen Nutzungen glänzt das Siegel; „Beliebt“ (🔥) kommt schon früher. */
export const GLANZ_AB = 25;

export function hatGlanz(nutzung: number | null | undefined): boolean {
  return (nutzung ?? 0) >= GLANZ_AB;
}

export const GLANZ_TEXT = `Glanz: Der Beitrag wurde mindestens ${GLANZ_AB}-mal genutzt.`;
