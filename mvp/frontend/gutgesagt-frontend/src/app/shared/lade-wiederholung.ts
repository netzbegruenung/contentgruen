import { Observable, Subscription, fromEvent, merge, timer } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';

/**
 * Abstaende der Wiederholung nach einem Ladefehler: erst schnell, dann seltener; der
 * letzte gilt fuer alle weiteren Versuche. Niemand muss die Seite neu laden.
 */
export const WIEDERHOLUNG_MS: readonly number[] = [2000, 5000, 15000, 30000, 60000];

/**
 * Ob sich ein neuer Versuch von selbst lohnt: ohne Antwort (Netz weg, Status 0 oder
 * kein HTTP-Fehler), Timeout (408), gebremst (429) oder Serverfehler (5xx). Andere
 * 4xx aendern sich nicht durch Warten; dort bleibt nur der Knopf.
 */
export function lohntWiederholung(fehler: unknown): boolean {
  const status = (fehler as { status?: unknown } | null)?.status;
  if (typeof status !== 'number') {
    return true;
  }
  return status === 0 || status === 408 || status === 429 || status >= 500;
}

/**
 * Plant nach einem Ladefehler den naechsten Versuch mit wachsendem Abstand
 * (WIEDERHOLUNG_MS), sofern er sich lohnt (lohntWiederholung). Solange ein Fehler
 * offen ist, startet sie ausserdem sofort einen Versuch, wenn das Netz zurueckkommt
 * (``online``) oder der Tab wieder sichtbar wird. Endet mit ``ende$`` (dem destroy$
 * der Seite).
 *
 * Gebrauch: vor jedem Laden ``abbrechen()``, nach Erfolg ``erfolg()``, nach einem
 * Fehler ``fehlgeschlagen(fehler, () => this.laden())``.
 */
export class LadeWiederholung {
  private fehlversuche = 0;
  private geplant: Subscription | null = null;
  /** Gesetzt, solange ein Fehler offen ist: was ``online``/sichtbar ausloest. */
  private offen: (() => void) | null = null;

  constructor(private readonly ende$: Observable<unknown>) {
    merge(
      fromEvent(window, 'online'),
      fromEvent(document, 'visibilitychange').pipe(filter(() => document.visibilityState === 'visible')),
    )
      .pipe(takeUntil(ende$))
      .subscribe(() => this.offen?.());
  }

  /** Merkt den Fehler; gibt zurueck, ob ein Versuch von selbst geplant ist. */
  fehlgeschlagen(fehler: unknown, laden: () => void): boolean {
    this.abbrechen();
    this.offen = laden;
    if (!lohntWiederholung(fehler)) {
      return false;
    }
    const abstand = WIEDERHOLUNG_MS[Math.min(this.fehlversuche, WIEDERHOLUNG_MS.length - 1)];
    this.fehlversuche++;
    this.geplant = timer(abstand).pipe(takeUntil(this.ende$)).subscribe(() => laden());
    return true;
  }

  abbrechen(): void {
    this.geplant?.unsubscribe();
    this.geplant = null;
    this.offen = null;
  }

  erfolg(): void {
    this.fehlversuche = 0;
  }
}
