/**
 * Tastatur im WAI-ARIA-Tab-Muster: Pfeil rechts und links waehlen den naechsten
 * bzw. vorigen Tab (am Ende geht es von vorn weiter), Pos1 und Ende den ersten
 * bzw. letzten. Der gewaehlte Tab bekommt auch den Fokus; andere Tasten bleiben
 * unberuehrt.
 *
 * Gedacht fuer ``(keydown)`` an der ``tablist``: ``event.currentTarget`` ist die
 * Liste, ihre ``[role="tab"]``-Knoepfe stehen in der Reihenfolge der Tabs.
 */
export function tabTaste(
  event: KeyboardEvent,
  jetzt: number,
  anzahl: number,
  waehlen: (ziel: number) => void,
): void {
  const ziel = (
    {
      ArrowRight: (jetzt + 1) % anzahl,
      ArrowLeft: (jetzt - 1 + anzahl) % anzahl,
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
