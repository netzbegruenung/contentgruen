import { TITEL_MAX } from '../shared/beitrag-grenzen';
import { einzeilig } from './einzeilig';

/**
 * Der vorgeschlagene Titel eines Kommentars (Entscheidung E2, 14.11.2026): Das Titelfeld steht
 * unter dem Text und ist damit vorbelegt, bleibt aber Pflicht und änderbar.
 *
 * WIE vorgeschlagen wird, steht nur hier. Vorerst der erste Satz des Textes, gekürzt auf
 * TITEL_MAX. Ob es dabei bleibt oder ein anderes Verfahren ohne generative KI kommt (etwa aus
 * der Aussage), ist noch offen; dann ändert sich nur diese Funktion. ``aussage`` ist dafür
 * schon da und wird vom ersten Satz noch nicht genutzt.
 */
export function titelVorschlag(text: string | null | undefined, _aussage: string | null | undefined = ''): string {
  return gekuerzt(ersterSatz(einzeilig(text)), TITEL_MAX);
}

/** Bis zum ersten Satzzeichen (. ! ?), dem Leerraum oder das Ende folgt; sonst der ganze Text. */
function ersterSatz(text: string): string {
  const treffer = text.match(/^.*?[.!?…](?=\s|$)/);
  return (treffer ? treffer[0] : text).trim();
}

/** Höchstens ``max`` Zeichen, an einer Wortgrenze, mit Auslassungszeichen. */
function gekuerzt(text: string, max: number): string {
  if (text.length <= max) {
    return text;
  }
  const vorne = text.slice(0, max - 1);
  const grenze = vorne.lastIndexOf(' ');
  return `${(grenze > max / 2 ? vorne.slice(0, grenze) : vorne).trimEnd()}…`;
}
