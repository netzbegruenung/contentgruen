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

/**
 * Abkürzungen, an deren Punkt kein Satz endet („z. B.“ machte sonst „Das ist z.“ zum Titel).
 * Klein geschrieben, ohne Punkt; dazu gelten ein einzelner Buchstabe und ein Wort mit Punkt darin
 * („u.a.“) als Abkürzung.
 */
const ABKUERZUNGEN = new Set([
  'bzw', 'ca', 'd', 'dh', 'evtl', 'ggf', 'inkl', 'insb', 'mio', 'mrd', 'nr', 'o', 'u', 'usw', 'v', 'vgl',
  'z', 'zb', 'zt', 'bspw', 'etc', 'abs', 'art', 'dr', 'prof', 'st', 'str', 'jh', 'mind', 'max', 'min',
]);

/**
 * Wörter, vor denen eine Zahl mit Punkt eine Ordinalzahl ist („1. Januar“, „19. Jahrhundert“):
 * Dort endet kein Satz. Klein geschrieben.
 */
const NACH_ORDINALZAHL = new Set([
  'januar', 'jänner', 'februar', 'märz', 'april', 'mai', 'juni', 'juli', 'august', 'september',
  'oktober', 'november', 'dezember', 'jahrhundert', 'jahrtausend',
]);

/**
 * Artikel und Präpositionen mit Artikel, nach denen eine Zahl mit Punkt eine Ordinalzahl ist
 * („nach dem 2. Weltkrieg“, „der 1. FC“, „die 3. Klasse“). Klein geschrieben.
 */
const VOR_ORDINALZAHL = new Set([
  'der', 'die', 'das', 'dem', 'den', 'des', 'am', 'im', 'zum', 'zur', 'vom', 'beim', 'ins', 'ans',
  'ein', 'eine', 'einem', 'einen', 'einer', 'eines', 'jeder', 'jede', 'jedes', 'jedem', 'jeden',
]);

/**
 * Bis zum ersten Satzzeichen (. ! ? …), dem Leerraum oder das Ende folgt; ein Punkt hinter
 * einer Abkürzung zählt nicht. Ein Punkt hinter einer Zahl („seit 2019.“) beendet den Satz,
 * außer bei einer Ordinalzahl: vor einem Monatsnamen oder „Jahrhundert“ („1. Januar“), vor
 * einem klein geschriebenen Wort („am 3. und 4. Mai“) oder nach einem Artikel („dem 2.
 * Weltkrieg“). Sonst der ganze Text.
 */
function ersterSatz(text: string): string {
  const ende = /[.!?…](?=\s|$)/g;
  for (const treffer of text.matchAll(ende)) {
    const stelle = treffer.index!;
    if (treffer[0] === '.' && keinSatzende(text.slice(0, stelle), text.slice(stelle + 1))) {
      continue;
    }
    return text.slice(0, stelle + 1).trim();
  }
  return text.trim();
}

/** Ob der Punkt nach ``davor`` eine Abkürzung oder Ordinalzahl beendet statt eines Satzes. */
function keinSatzende(davor: string, danach: string): boolean {
  const wort = davor.match(/(\S+)$/)?.[1] ?? '';
  if (/\d$/.test(wort)) {
    const vorher = davor.slice(0, davor.length - wort.length).match(/(\p{L}+)\s*$/u)?.[1]?.toLowerCase();
    return istOrdinalzahl(danach) || (!!vorher && VOR_ORDINALZAHL.has(vorher) && !!danach.trim());
  }
  const ohneZeichen = wort.replace(/^[„"'(]+/, '').replace(/\./g, '').toLowerCase();
  // Ein Punkt schon im Wort („u.a“, „z.B“): zusammengeschriebene Abkürzung
  return /\p{L}\.\p{L}/u.test(wort) || ohneZeichen.length === 1 || ABKUERZUNGEN.has(ohneZeichen);
}

/** Ob das Wort nach „<Zahl>.“ die Zahl zur Ordinalzahl macht (Monat, Jahrhundert, klein geschrieben). */
function istOrdinalzahl(danach: string): boolean {
  const naechstes = danach.trimStart().match(/^[„"'(]*(\p{L}+)/u)?.[1];
  if (!naechstes) {
    return false;
  }
  return NACH_ORDINALZAHL.has(naechstes.toLowerCase()) || naechstes[0] === naechstes[0].toLowerCase();
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
