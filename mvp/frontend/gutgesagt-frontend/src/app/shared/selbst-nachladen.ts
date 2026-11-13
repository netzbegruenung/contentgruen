import { DestroyRef } from '@angular/core';
import { Observable, fromEvent, merge, timer } from 'rxjs';
import { filter, map } from 'rxjs/operators';

/** So oft laden Listen nach, solange der Reiter sichtbar ist (Grundsatz 13.11.2026). */
export const NACHLADEN_MS = 30_000;

function sichtbar(): boolean {
  return document.visibilityState === 'visible';
}

/**
 * Die Anlaesse zum Nachladen: alle ``ms``, solange der Reiter sichtbar ist, und sofort,
 * wenn er wieder sichtbar wird. Der erste Anlass kommt erst nach ``ms`` oder beim
 * Sichtbarwerden; das erste Laden macht die Seite selbst.
 *
 * Oberflaechen laden selbst nach, niemand muss „Aktualisieren“ druecken oder die Seite
 * neu laden. Ein versteckter Reiter fragt nicht: Das spart Anfragen und haelt die
 * Ratenbremse fern.
 */
export function nachladeAnlaesse(ms = NACHLADEN_MS): Observable<void> {
  return merge(
    timer(ms, ms).pipe(filter(sichtbar)),
    fromEvent(document, 'visibilitychange').pipe(filter(sichtbar)),
  ).pipe(map(() => undefined));
}

/**
 * Ruft ``laden`` bei jedem Anlass (``nachladeAnlaesse``) auf, bis ``destroyRef`` endet.
 * Gebrauch im Konstruktor oder in ngOnInit: ``selbstNachladen(() => this.laden(), this.destroyRef)``.
 */
export function selbstNachladen(laden: () => void, destroyRef: DestroyRef, ms = NACHLADEN_MS): void {
  const abo = nachladeAnlaesse(ms).subscribe(() => laden());
  destroyRef.onDestroy(() => abo.unsubscribe());
}
