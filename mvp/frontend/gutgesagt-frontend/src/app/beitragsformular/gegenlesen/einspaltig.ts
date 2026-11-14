import { Signal, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver } from '@angular/cdk/layout';
import { map } from 'rxjs/operators';

/** Ab hier steht die Vorschau unter dem Formular (shared/styles/_contribution-form.scss). */
export const EINSPALTIG = '(max-width: 1024px)';

/**
 * Ob das Beitragsformular einspaltig ist. Dann steht das Gegenlesen kompakt direkt
 * unter dem Textfeld statt neben der Vorschau, die weit unten liegt (Nutzerfuehrung
 * 13.11.). Im Injektionskontext aufrufen, etwa als Feld der Komponente.
 */
export function einspaltig(): Signal<boolean> {
  return toSignal(
    inject(BreakpointObserver)
      .observe(EINSPALTIG)
      .pipe(map((zustand) => zustand.matches)),
    { initialValue: false },
  );
}
