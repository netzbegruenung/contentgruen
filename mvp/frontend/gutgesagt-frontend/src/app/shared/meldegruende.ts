/**
 * Meldegruende (Glossar „Meldegrund“): eine Liste fuer Meldedialog, Admin-Ansicht
 * und Hilfe. Die Werte sind dieselben wie in `domain/models/meldegrund.py` im
 * Suchdienst; gespeicherte Meldungen tragen sie, deshalb nie umbenennen.
 */
export type MeldegrundWert =
  | 'spam'
  | 'inappropriate'
  | 'fabricated_or_false'
  | 'duplicate'
  | 'illegal_content'
  | 'other';

export interface Meldegrund {
  value: MeldegrundWert;
  label: string;
}

/** Erfundene Erlebnisse oder Zahlen nennt docs/VISION.md ausdruecklich als Meldegrund (#423). */
export const ERFUNDEN_ODER_FALSCH: Meldegrund = {
  value: 'fabricated_or_false',
  label: 'Erfunden oder sachlich falsch',
};

export const MELDEGRUENDE: readonly Meldegrund[] = [
  { value: 'spam', label: 'Spam oder unerwünschte Werbung' },
  { value: 'inappropriate', label: 'Unangemessener Inhalt' },
  ERFUNDEN_ODER_FALSCH,
  { value: 'duplicate', label: 'Dublette' },
  { value: 'illegal_content', label: 'Rechtswidriger Inhalt' },
  { value: 'other', label: 'Andere' },
];

/**
 * Bei rechtswidrigem Inhalt verlangt Art. 16 Abs. 2 lit. a DSA eine begruendete
 * Erlaeuterung (#438); der Suchdienst prueft dasselbe.
 */
export function brauchtBegruendung(value: MeldegrundWert): boolean {
  return value === 'illegal_content';
}

/** Die Beschriftung eines Meldegrunds; ein unbekannter Wert bleibt, wie er ist. */
export function meldegrundLabel(value: string): string {
  return MELDEGRUENDE.find((grund) => grund.value === value)?.label ?? value;
}
