import { Observable, Subscription, timer } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

/**
 * Abstaende der Wiederholung nach einem Ladefehler: erst schnell, dann seltener; der
 * letzte gilt fuer alle weiteren Versuche. Niemand muss die Seite neu laden.
 */
export const WIEDERHOLUNG_MS: readonly number[] = [2000, 5000, 15000, 30000, 60000];

/**
 * Plant nach einem Ladefehler den naechsten Versuch mit wachsendem Abstand
 * (WIEDERHOLUNG_MS). Endet mit ``ende$`` (dem destroy$ der Seite).
 *
 * Gebrauch: vor jedem Laden ``abbrechen()``, nach Erfolg ``erfolg()``, nach einem
 * Fehler ``planen(() => this.laden())``.
 */
export class LadeWiederholung {
  private fehlversuche = 0;
  private geplant: Subscription | null = null;

  constructor(private readonly ende$: Observable<unknown>) {}

  planen(laden: () => void): void {
    this.abbrechen();
    const abstand = WIEDERHOLUNG_MS[Math.min(this.fehlversuche, WIEDERHOLUNG_MS.length - 1)];
    this.fehlversuche++;
    this.geplant = timer(abstand).pipe(takeUntil(this.ende$)).subscribe(() => laden());
  }

  abbrechen(): void {
    this.geplant?.unsubscribe();
    this.geplant = null;
  }

  erfolg(): void {
    this.fehlversuche = 0;
  }
}
