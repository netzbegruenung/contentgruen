import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { distinctUntilChanged } from 'rxjs/operators';

/**
 * Was die App über die Art.-9-Einwilligung der angemeldeten Person weiß:
 * ``unbekannt`` (Besucher, noch nicht gefragt oder Stand nicht abrufbar),
 * ``eingewilligt`` oder ``fehlt`` (nie erteilt, widerrufen oder zu einem früheren
 * Wortlaut, der nicht mehr zählt).
 */
export type Art9Zustand = 'unbekannt' | 'eingewilligt' | 'fehlt';

/**
 * Der Stand der Einwilligung für Formulare und Interceptor, ohne HttpClient: Der
 * Interceptor soll keinen Dienst holen, der selbst HTTP macht. Den Stand setzt
 * ``Art9EinwilligungService`` (Anmelden, Einwilligen, Widerrufen) und der
 * Interceptor bei einem 403 ``art9_einwilligung_fehlt``.
 *
 * Formulare mit eigenem Hinweiskasten (``EinwilligungHinweisComponent``) melden sich
 * hier an; solange einer da ist, zeigt der Interceptor keinen zweiten Hinweis als
 * Snackbar.
 */
@Injectable({ providedIn: 'root' })
export class Art9EinwilligungZustand {
  private readonly stand = new BehaviorSubject<Art9Zustand>('unbekannt');
  readonly zustand$ = this.stand.asObservable().pipe(distinctUntilChanged());
  private hinweise = 0;

  get wert(): Art9Zustand {
    return this.stand.value;
  }

  setzen(zustand: Art9Zustand): void {
    if (this.stand.value !== zustand) this.stand.next(zustand);
  }

  /** Ein Hinweiskasten ist auf der Seite; die Rückgabe meldet ihn wieder ab. */
  hinweisAnmelden(): () => void {
    this.hinweise += 1;
    let abgemeldet = false;
    return () => {
      if (!abgemeldet) {
        abgemeldet = true;
        this.hinweise -= 1;
      }
    };
  }

  /** Ob die Seite einen eigenen Hinweiskasten hat. */
  get hinweisDa(): boolean {
    return this.hinweise > 0;
  }
}
