/** Text, wie Lesende ihn sehen: Umbrueche und Einrueckung als ein Leerzeichen. */
export function normalisiert(text: string | null): string {
  return (text ?? '').replace(/\s+/g, ' ').trim();
}

/**
 * Der sichtbare Text eines Abschnitts in einem Rechtstext: von seiner Ueberschrift (h2 oder
 * h3) bis zur naechsten Ueberschrift derselben oder hoeheren Ebene. ``titel`` ist der ganze
 * Ueberschriftentext oder ein Muster, etwa ``/^7\. /`` fuer einen nummerierten Abschnitt.
 */
export function abschnitt(seite: HTMLElement, titel: string | RegExp): string {
  const kopf = Array.from(seite.querySelectorAll('h2, h3')).find((h) => {
    const text = normalisiert(h.textContent);
    return typeof titel === 'string' ? text === titel : titel.test(text);
  });
  if (!kopf) {
    throw new Error(`Kein Abschnitt "${titel}"`);
  }
  const ebene = kopf.tagName === 'H2' ? ['H2'] : ['H2', 'H3'];
  const teile: string[] = [];
  let knoten = kopf.nextElementSibling;
  while (knoten && !ebene.includes(knoten.tagName)) {
    teile.push(knoten.textContent ?? '');
    knoten = knoten.nextElementSibling;
  }
  return normalisiert(teile.join(' '));
}

const MONATE = [
  'Januar',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
];

/**
 * Ob ``text`` ein Tagesdatum ist, wie es in der Stand-Zeile eines Rechtstexts steht:
 * „2. November 2026“, und ob es diesen Tag gibt („31. September 2026“ nicht).
 */
export function istTagesdatum(text: string): boolean {
  const treffer = /^([1-9]|[12]\d|3[01])\. (\S+) (\d{4})$/.exec(text);
  const monat = treffer ? MONATE.indexOf(treffer[2]) : -1;
  if (!treffer || monat < 0) {
    return false;
  }
  const tag = new Date(Number(treffer[3]), monat, Number(treffer[1]));
  return tag.getMonth() === monat;
}

/** Der Text hinter „Stand:“ im Update-Hinweis am Ende eines Rechtstexts (#498). */
export function stand(seite: HTMLElement): string {
  const zeile = seite.querySelector('.update-notice p');
  const text = normalisiert(zeile?.textContent ?? null);
  if (!text.startsWith('Stand:')) {
    throw new Error('Keine Stand-Zeile im Update-Hinweis');
  }
  return text.replace(/^Stand:\s*/, '');
}
