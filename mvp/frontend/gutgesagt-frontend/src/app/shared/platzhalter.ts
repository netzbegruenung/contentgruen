import { textStuecke } from './vorlagen-luecke';

/**
 * Platzhalter vor dem Kopieren füllen (Persona-Test Dennis, 13.11.): Ein Platzhalter
 * „[Hier ein eigenes Erlebnis: …]“ soll nicht mitsamt Klammern im echten Post landen.
 * Vor dem Kopieren fragt ein Dialog je Platzhalter nach dem eigenen Satz; wer keinen
 * hat, kopiert ohne die Klammer-Stelle. Erkannt wird, was `vorlagen-luecke.ts` erkennt.
 */

/** Ein Platzhalter im Text, mit dem Hinweis aus der Klammer („Hier ein eigenes Erlebnis: …“). */
export interface Platzhalter {
  hinweis: string;
}

/** Die Platzhalter des Texts in ihrer Reihenfolge; leer, wenn es keine gibt. */
export function platzhalterIn(text: string | null | undefined): Platzhalter[] {
  if (!text) {
    return [];
  }
  return textStuecke(text)
    .filter((stueck) => stueck.luecke)
    .map((stueck) => ({ hinweis: stueck.text.slice(1, -1).trim() }));
}

/**
 * Setzt je Platzhalter den eingegebenen Satz ein, in derselben Reihenfolge wie
 * `platzhalterIn`. Ein leerer Satz entfernt seinen Platzhalter wie `ohnePlatzhalter`.
 */
export function platzhalterFuellen(text: string, saetze: readonly string[]): string {
  let i = 0;
  const teile = textStuecke(text).map((stueck) => {
    if (!stueck.luecke) {
      return stueck.text;
    }
    const satz = (saetze[i++] ?? '').trim();
    return satz || ENTFERNT;
  });
  return aufraeumen(teile.join(''));
}

/** Der Text ohne die Klammer-Stellen, ohne doppelte Leerzeichen und verwaiste Satzzeichen. */
export function ohnePlatzhalter(text: string): string {
  return platzhalterFuellen(text, []);
}

/** Markiert eine entfernte Stelle, bis `aufraeumen` sie samt Umgebung glättet. */
const ENTFERNT = '\u0000';

function aufraeumen(text: string): string {
  if (!text.includes(ENTFERNT)) {
    return text;
  }
  // Geglaettet wird nur um die entfernten Stellen; der uebrige Text bleibt, wie er ist.
  return (
    text
      // Am Satzanfang (Textanfang, nach Satzende oder Doppelpunkt) faellt ein Satzzeichen
      // direkt nach der Stelle mit weg: "Gut. [Hier …]. Weiter" -> "Gut. Weiter".
      .replace(/(^|[.!?:\n][ \t]*)\u0000[ \t]*[.,;:!?]+[ \t]*/g, '$1')
      // Zwischen zwei Kommas oder Semikolons bleibt eins: "Gut, [Hier …], weiter." -> "Gut, weiter."
      .replace(/([,;])[ \t]*\u0000[ \t]*[,;]/g, '$1')
      // Eine Klammer, die nur die Stelle enthielt, faellt ganz weg: "A ([Hier …]) b" -> "A b"
      .replace(/[ \t]*\([ \t]*\u0000[ \t]*\)/g, '')
      // Mitten im Satz kein Leerzeichen vor dem folgenden Satzzeichen oder der schliessenden
      // Klammer: "Weil [Hier …]." -> "Weil.", "(z. B. [Hier …])" -> "(z. B.)"
      .replace(/[ \t]*\u0000[ \t]*(?=[.,;:!?)])/g, '')
      .replace(/[ \t]+\u0000[ \t]+/g, ' ')
      .replace(/^[ \t]*\u0000[ \t]*/gm, '')
      .replace(/[ \t]*\u0000[ \t]*$/gm, '')
      .replace(/\u0000/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  );
}
