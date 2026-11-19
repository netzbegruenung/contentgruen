import { HOT_TAKES } from './startbeispiel';

/**
 * Testeingaben (GLOSSARY „Testeingabe“): Suchanfragen, die nur ausprobieren, grüßen oder
 * nach der App fragen. Statt zu suchen zeigt die Ergebnisseite eine freundliche Karte mit
 * einem der Texte der Gruppe und dem Aufruf darunter. Gesucht wird dann nicht: Die Suche
 * legte sonst ihren Text als Aussage an, und „test“ oder „hallo“ landeten nach zwei
 * Personen als Lücke in „Hier fehlt eine Antwort“ (Testdaten auf Prod, 19.11.).
 *
 * Wörter und Texte stehen nur hier. Ein Wort gilt nur, wenn es die ganze Eingabe ist
 * (siehe normalisieren); „Testergebnis Corona“ oder „Hallo, die Grünen …“ suchen normal.
 * Texte: freundlich, höchstens 140 Zeichen, keine Gedankenstriche, kein Spott, keine
 * Parteistimme (Länge und Gedankenstriche prüft testeingabe.spec.ts, den Ton das Review).
 */
export type TesteingabeArt = 'test' | 'gruss' | 'frage';

export interface TesteingabeGruppe {
  /** Klein geschrieben, ohne Satzzeichen am Ende; mehrere Wörter mit einem Leerzeichen. */
  woerter: readonly string[];
  /** Einer davon steht zufällig auf der Karte. */
  texte: readonly string[];
}

export const TESTEINGABEN: Readonly<Record<TesteingabeArt, TesteingabeGruppe>> = {
  test: {
    woerter: ['test', 'testen', 'tset', 'asdf', '123', 'foo', 'bla'],
    texte: [
      'Das hier ist keine Klassenarbeit. Probier’s einfach nochmal, ganz ohne Druck! \u{1F60A}',
      'Test bestanden ✅ Gut gesagt läuft. Jetzt du: Welcher Spruch hat dich zuletzt sprachlos gemacht?',
      'Eins, zwei, eins, zwei \u{1F3A4} Alles läuft. Tipp einfach den Spruch ein, der dir neulich begegnet ist.',
    ],
  },
  gruss: {
    woerter: ['hallo', 'hi', 'moin', 'servus', 'hey'],
    texte: [
      'Hallo zurück! \u{1F44B} Schön, dass du da bist. Welcher Spruch geht dir gerade nicht aus dem Kopf?',
      'Schön, dich zu sehen! Hier findest du Antworten auf Sprüche, die dich ärgern. Welcher war es zuletzt?',
      'Hey, willkommen! Erzähl mal: Welcher Satz hat dich neulich kurz sprachlos gemacht?',
    ],
  },
  frage: {
    woerter: ['hilfe', 'was ist das', 'wie geht das'],
    texte: [
      'Ganz einfach: Tipp einen Spruch ein, den du gehört hast. Du bekommst Antworten, die andere schon geschrieben haben.',
      'Dir fehlen bei einem Spruch die Worte? Tipp ihn hier ein und such dir eine Antwort aus, die zu dir passt.',
      'Gut gesagt sammelt gute Antworten auf schwierige Sprüche. Tipp einen ein und schau, was andere dazu schreiben.',
    ],
  },
};

/** Der Aufruf unter jedem Text, vor dem Beispiel. */
export const TESTEINGABE_AUFRUF = 'Tipp ein, was du zuletzt am Küchentisch gehört hast, zum Beispiel';

/** Das Beispiel hinter dem Aufruf; ein Klick sucht es. Ein Hot Take, den die Suche sicher erkennt. */
export const TESTEINGABE_BEISPIEL = HOT_TAKES[1].text;

/**
 * Die Eingabe, wie sie mit den Wörtern verglichen wird: ohne Leerraum außen, klein,
 * Leerraum innen zu einem Leerzeichen, ohne Satzzeichen am Ende („Hallo!“, „Was ist das?“).
 */
export function normalisieren(eingabe: string): string {
  return (eingabe ?? '')
    .trim()
    .toLocaleLowerCase('de')
    .replace(/[\s\p{P}]+$/u, '')
    .replace(/\s+/g, ' ');
}

const NACH_WORT = new Map<string, TesteingabeArt>(
  (Object.keys(TESTEINGABEN) as TesteingabeArt[]).flatMap((art) =>
    TESTEINGABEN[art].woerter.map((wort): [string, TesteingabeArt] => [wort, art]),
  ),
);

/** Ab so vielen Zeichen zählen reine Ziffern („1234“) und ein wiederholtes Zeichen („aaa“) als Test. */
export const TESTEINGABE_MIN_ZEICHEN = 3;

/**
 * Die Gruppe, wenn die ganze Eingabe ein Wort der Liste ist; sonst null (dann wird gesucht).
 * Zur Gruppe test zählen auch (Maintainer 19.11.): nur Ziffern oder ein einzelnes wiederholtes
 * Zeichen ab TESTEINGABE_MIN_ZEICHEN, und eine Eingabe nur aus Satzzeichen („?“, „...“).
 * Leere oder nur Leerraum ist keine Testeingabe: Da sucht das Feld ohnehin nicht.
 */
export function testeingabeArt(eingabe: string): TesteingabeArt | null {
  const text = normalisieren(eingabe);
  const art = NACH_WORT.get(text);
  if (art) {
    return art;
  }
  if (text === '') {
    return (eingabe ?? '').trim() ? 'test' : null;
  }
  const zeichen = [...text];
  if (zeichen.length >= TESTEINGABE_MIN_ZEICHEN && (/^\d+$/.test(text) || zeichen.every((z) => z === zeichen[0]))) {
    return 'test';
  }
  return null;
}

/** Ein zufälliger Text der Gruppe; `zufall` liefert wie Math.random eine Zahl in [0, 1). */
export function testeingabeText(art: TesteingabeArt, zufall: () => number = Math.random): string {
  const texte = TESTEINGABEN[art].texte;
  return texte[Math.min(texte.length - 1, Math.floor(zufall() * texte.length))];
}
