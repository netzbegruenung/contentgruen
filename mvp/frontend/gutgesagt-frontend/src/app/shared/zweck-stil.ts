/**
 * Zweck und Stil eines Kommentars (GLOSSARY.md, #357); die Werte sind dieselben wie
 * im Backend (`Zweck` und `Stil` in domain/models/commentary.py).
 *
 * Zweck: fuer wen der Kommentar geschrieben ist - als Antwort in Kommentarspalten
 * (Standard) oder fuer die eigenen Leute. Stil: die Tonlage, optional.
 */
export type Zweck = 'kommentarspalte' | 'eigene_leute';

export type Stil = 'sachlich' | 'humorvoll' | 'persoenlich' | 'brueckenbauend' | 'bissig';

/** Ohne Angabe gilt ein Kommentar als Antwort in Kommentarspalten. */
export const ZWECK_STANDARD: Zweck = 'kommentarspalte';

export const ZWECK_LABEL: Record<Zweck, string> = {
  kommentarspalte: 'Antwort in Kommentarspalten',
  eigene_leute: 'Für die eigenen Leute',
};

export const STIL_LABEL: Record<Stil, string> = {
  sachlich: 'sachlich',
  humorvoll: 'humorvoll',
  persoenlich: 'persönlich',
  brueckenbauend: 'brückenbauend',
  bissig: 'bissig',
};

/** "Bissig" gibt es nur beim Zweck "Für die eigenen Leute". */
export function stileFuer(zweck: Zweck): Stil[] {
  const stile = Object.keys(STIL_LABEL) as Stil[];
  return zweck === 'eigene_leute' ? stile : stile.filter((stil) => stil !== 'bissig');
}

/** Ob der Stil zum Zweck passt; ohne Stil passt jeder Zweck. */
export function stilPasst(stil: Stil | null | undefined, zweck: Zweck): boolean {
  return !stil || stileFuer(zweck).includes(stil);
}
