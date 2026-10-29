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
