/** Wie die Tabs einer ``tablist`` liegen, wie in ``aria-orientation``. */
export type TabAusrichtung = 'horizontal' | 'vertical';

/**
 * Tastatur im WAI-ARIA-Tab-Muster: Waagerecht waehlen Pfeil rechts und links den
 * naechsten bzw. vorigen Tab, senkrecht Pfeil runter und hoch (am Ende geht es von
 * vorn weiter); Pos1 und Ende den ersten bzw. letzten. Die Pfeile der anderen Achse
 * bleiben unberuehrt, damit die Seite mit ihnen weiter scrollt. Der gewaehlte Tab
 * bekommt auch den Fokus; andere Tasten bleiben unberuehrt.
 *
 * Gedacht fuer ``(keydown)`` an der ``tablist``: ``event.currentTarget`` ist die
 * Liste, ihre ``[role="tab"]``-Knoepfe stehen in der Reihenfolge der Tabs.
 */
export function tabMitTasteWaehlen(
  event: KeyboardEvent,
  jetzt: number,
  anzahl: number,
  waehlen: (ziel: number) => void,
  ausrichtung: TabAusrichtung = 'horizontal',
): void {
  const [vor, zurueck] = ausrichtung === 'vertical' ? ['ArrowDown', 'ArrowUp'] : ['ArrowRight', 'ArrowLeft'];
  const ziel = (
    {
      [vor]: (jetzt + 1) % anzahl,
      [zurueck]: (jetzt - 1 + anzahl) % anzahl,
      Home: 0,
      End: anzahl - 1,
    } as Record<string, number>
  )[event.key];
  if (ziel === undefined) {
    return;
  }
  event.preventDefault();
  waehlen(ziel);
  const knoepfe = (event.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('[role="tab"]');
  knoepfe[ziel]?.focus();
}
