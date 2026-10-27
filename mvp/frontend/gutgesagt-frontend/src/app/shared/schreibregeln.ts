/**
 * Wie man gut schreibt (docs/VISION.md, "Ton und Schreiben"): die sechs
 * Schreibregeln, die Schreibhilfen und die Titelbeispiele. Sie lenken sanft und
 * sperren nichts; die Hinweise beim Speichern sind eine eigene Stelle (#358).
 *
 * Hier gepflegt, damit Formularhilfe und Hilfe-Dialog dieselben Saetze zeigen.
 */

import { FormularTyp } from './formular-adresse';

/** Die sechs Schreibregeln, in der Reihenfolge der Vision. */
export const SCHREIBREGELN: readonly string[] = [
  'Schreib für die Unentschiedenen, die mitlesen.',
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
  { name: 'Aufhänger vor Begründung', text: 'Erst das, was Lesende packt, dann die Begründung.' },
  { name: 'Lesende als Hauptfigur', text: 'Sprich die Lesenden mit „du“ an und erzähl von ihrem Alltag.' },
  { name: 'Zahlen in den Alltag', text: '„Jede dritte Wohnung“ statt „33 Prozent“.' },
];

export interface SchwacherTitel {
  titel: string;
  warum: string;
}

/**
 * Titel: ein Satz, eine Behauptung mit Haltung (GLOSSARY.md, Titel). Gezeigt
 * beim Kommentar; die Hintergrundinfo liegt ausserhalb von #344, Post-Titel
 * folgen der Regel nicht.
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
  'Nicht jede Aussage braucht eine Antwort. Jede Antwort macht sie sichtbarer. Bei kleinen Accounts lieber nicht antworten, sondern die Aussage bei der Plattform melden, auf der sie steht.';

/** Der Meldedialog hat (noch) keinen eigenen Grund dafuer, daher der Weg ueber „Andere“. */
export const ERFUNDENES_MELDEN =
  'Erfundene Erlebnisse oder Zahlen in einem Beitrag? Melde ihn hier bei Gut gesagt unter „Andere“ und schreib dazu, was nicht stimmt.';

/**
 * 'post' kennt FormularTyp erst mit dem Post-Formular (#297); bis dahin steht
 * er hier zusaetzlich, danach reicht FormularTyp.
 */
type TypMitHilfe = FormularTyp | 'post';

/** Beitragstypen, deren Formularhilfe die Schreibregeln zeigt. */
export const TYPEN_MIT_SCHREIBREGELN: readonly TypMitHilfe[] = ['commentary', 'post'];

/** Beitragstypen, deren Formularhilfe Titelbeispiele zeigt. */
export const TYPEN_MIT_TITELBEISPIELEN: readonly TypMitHilfe[] = ['commentary'];
