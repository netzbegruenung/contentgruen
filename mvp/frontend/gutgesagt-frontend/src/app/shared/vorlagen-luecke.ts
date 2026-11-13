/**
 * Lücken in Vorlagen (#640, R38): Ein eigenes Erlebnis steht in einem Kommentar nur als
 * Platzhalter in eckigen Klammern, "[Hier ein eigenes Erlebnis: …]" (Schreibregel, siehe
 * schreibregeln.ts). Die Karte hebt ihn als Feld hervor, und nach dem Kopieren erinnert
 * der Hinweis daran, ihn auszufüllen - sonst landet der Platzhalter im echten Post.
 *
 * Erkannt wird nur die Form der Schreibregel, "[Hier …]": Andere eckige Klammern
 * ("[1]", "[sic]") sind keine Lücke.
 */
const LUECKE = /\[Hier\b[^\]\n]*\]/g;

// Sagt, was als Naechstes kommt (UX-Review B16), statt nur "Erfolgreich kopiert!"
export const KOPIERT = 'Kopiert – jetzt unter dem Post einfügen.';
export const KOPIERT_MIT_LUECKE = 'Kopiert – füll noch die Lücke in [ ] aus.';

export interface TextStueck {
  text: string;
  luecke: boolean;
}

export function hatLuecke(text: string | null | undefined): boolean {
  return !!text && new RegExp(LUECKE.source).test(text);
}

/** Der Text in Stücke zerlegt, die Lücken als eigene Stücke; ohne Lücke ein Stück. */
export function textStuecke(text: string): TextStueck[] {
  const stuecke: TextStueck[] = [];
  let rest = 0;
  for (const treffer of text.matchAll(LUECKE)) {
    const anfang = treffer.index ?? 0;
    if (anfang > rest) {
      stuecke.push({ text: text.slice(rest, anfang), luecke: false });
    }
    stuecke.push({ text: treffer[0], luecke: true });
    rest = anfang + treffer[0].length;
  }
  if (rest < text.length || stuecke.length === 0) {
    stuecke.push({ text: text.slice(rest), luecke: false });
  }
  return stuecke;
}
