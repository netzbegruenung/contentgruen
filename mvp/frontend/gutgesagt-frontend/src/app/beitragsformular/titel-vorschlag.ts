import { TITEL_MAX } from '../shared/beitrag-grenzen';
import { einzeilig } from './einzeilig';

/** Bis etwa hierhin bleibt der erste Satz ganz (Entscheidung 14.11.2026: „ca. 80 Zeichen“). */
export const TITEL_VORSCHLAG_ZIEL = 80;

/**
 * Der vorgeschlagene Titel eines Kommentars (Entscheidung E2, 14.11.2026): Das Titelfeld steht
 * unter dem Text und ist damit vorbelegt, bleibt aber Pflicht und änderbar.
 *
 * WIE vorgeschlagen wird, steht nur hier. Vorerst der erste Satz des Textes. Hat er mehr als
 * etwa TITEL_VORSCHLAG_ZIEL Zeichen, wird an der letzten Satzgrenze innerhalb des Satzes
 * gekürzt (Komma, Semikolon, Doppelpunkt, Gedankenstrich), sonst an einer Wortgrenze mit
 * Auslassungszeichen. Über ein anderes Verfahren ohne generative KI wird später entschieden;
 * dann ändert sich nur diese Funktion. ``aussage`` ist dafür schon da und wird noch nicht genutzt.
 */
export function titelVorschlag(text: string | null | undefined, _aussage: string | null | undefined = ''): string {
  return gekuerzt(ersterSatz(einzeilig(text)), TITEL_VORSCHLAG_ZIEL);
}

/** Bis zum ersten Satzzeichen (. ! ? …), dem Leerraum oder das Ende folgt; sonst der ganze Text. */
function ersterSatz(text: string): string {
  const treffer = text.match(/^.*?[.!?…](?=\s|$)/);
  return (treffer ? treffer[0] : text).trim();
}

/** Satzgrenzen innerhalb eines Satzes, an denen ein Titel enden darf. */
const TEILSATZ_GRENZE = /[,;:]\s|\s[–—-]\s/g;

/**
 * Höchstens etwa ``ziel`` Zeichen: an der letzten Teilsatzgrenze davor, wenn sie nicht zu früh
 * kommt; sonst an einer Wortgrenze mit Auslassungszeichen. Nie über TITEL_MAX.
 */
function gekuerzt(text: string, ziel: number): string {
  if (text.length <= ziel) {
    return text;
  }
  let grenze = -1;
  for (const treffer of text.slice(0, ziel + 1).matchAll(TEILSATZ_GRENZE)) {
    grenze = treffer.index!;
  }
  if (grenze >= ziel / 2) {
    return text.slice(0, grenze).trimEnd();
  }
  const vorne = text.slice(0, Math.min(ziel, TITEL_MAX) - 1);
  const wort = vorne.lastIndexOf(' ');
  return `${(wort > ziel / 2 ? vorne.slice(0, wort) : vorne).trimEnd()}…`;
}
