/**
 * Wie man gut schreibt (docs/VISION.md, "Ton und Schreiben"): die sechs
 * Schreibregeln, die Schreibhilfen und die Titelbeispiele. Sie lenken sanft und
 * sperren nichts; die Hinweise beim Speichern sind eine eigene Stelle (#358).
 *
 * Hier gepflegt, damit Formularhilfe und Hilfe-Dialog dieselben Saetze zeigen.
 */

/** Die sechs Schreibregeln, in der Reihenfolge der Vision. */
export const SCHREIBREGELN: readonly string[] = [
  'Schreib für die Unentschiedenen, die mitlesen – nicht für die Person, von der die Aussage stammt.',
  'Wiederhole den Vorwurf nicht, auch nicht, um ihn zu widerlegen.',
  'Fang mit dem an, was ihr gemeinsam habt.',
  'Sag, wofür du bist, nicht nur, wogegen.',
  'Erfinde nichts. Ein eigenes Erlebnis nur als Platzhalter: [Hier ein eigenes Erlebnis: …]',
  'Schreib kurz, ohne Belehrung, ohne Häme.',
];

export interface Schreibhilfe {
  name: string;
  text: string;
}

export const SCHREIBHILFEN: readonly Schreibhilfe[] = [
  { name: 'Küchenzuruf', text: 'Was würdest du in einem Satz durch die Küche rufen? Das ist deine Kurzfassung.' },
  { name: 'Aufhänger vor Beleg', text: 'Erst was Lesende packt, dann der Beleg.' },
  { name: 'Lesende als Hauptfigur', text: 'Sprich sie mit „du“ an: Es geht um ihren Alltag, nicht um dich.' },
  { name: 'Zahlen in den Alltag', text: '„Jede dritte Wohnung“ statt „33 Prozent“.' },
];

export interface SchwacherTitel {
  titel: string;
  warum: string;
}

/**
 * Titel eines Kommentars: ein Satz, eine Behauptung mit Haltung (GLOSSARY.md,
 * Titel). Post-Titel folgen der Regel nicht und bekommen keine Beispiele.
 */
export const TITEL_BEISPIELE: { gut: readonly string[]; schwach: readonly SchwacherTitel[] } = {
  gut: [
    'Wärmepumpe lohnt sich auch im Altbau',
    'Wärmepumpen rechnen sich im Altbau, wenn man die Förderung mitrechnet',
  ],
  schwach: [
    { titel: 'Lohnt sich die Wärmepumpe im Altbau?', warum: 'eine Frage – sie gehört in die Aussage' },
    { titel: 'Wärmepumpen im Altbau', warum: 'ein Thema, keine Behauptung' },
    { titel: 'Faktenhammer', warum: 'ein Etikett, sagt nichts' },
  ],
};

export const NICHT_JEDE_AUSSAGE =
  'Nicht jede Aussage braucht eine Antwort. Eine Antwort macht sie sichtbarer; kommt sie von einem kleinen Account, melde sie lieber bei der Plattform.';

export const ERFUNDENES_MELDEN =
  'Erfundene Erlebnisse oder Zahlen sind ein Grund zu melden: Melde den Beitrag und schreib dazu, was nicht stimmt.';

/** Beitragstypen, deren Formularhilfe die Schreibregeln zeigt. */
export const TYPEN_MIT_SCHREIBREGELN: readonly string[] = ['commentary', 'post'];

/** Beitragstypen, deren Formularhilfe Titelbeispiele zeigt. */
export const TYPEN_MIT_TITELBEISPIELEN: readonly string[] = ['commentary'];
