import { inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl } from '@angular/forms';
import { Thema } from '../services/dtos/themenDtos';
import { ThemenService } from '../services/themen.service';
import { AntwortAuf } from './antwort-auf/antwort-auf.component';
import { themenWaehlbar } from './aussage-fuer-anfrage';

/**
 * Die Themenwahl fuer die Aussage eines Beitragsformulars (#455), fuer das
 * Kommentar- und das Hintergrundinfo-Formular gleich. Haelt das Control der Themen
 * passend zur Aussage im Antwort-auf-Block.
 *
 * Im Konstruktor der Komponente anlegen: Die Liste laedt sie selbst und hoert mit
 * der Komponente auf.
 */
export class ThemenWahl {
  /** Die feste Themenliste; leer, solange sie nicht geladen (oder nicht ladbar) ist. */
  liste: Thema[] = [];

  constructor(private readonly themen: AbstractControl<string[] | null>) {
    // Ist die Liste nicht ladbar, fehlt die Themenwahl; speichern geht trotzdem.
    inject(ThemenService)
      .liste()
      .pipe(takeUntilDestroyed())
      .subscribe({ next: (liste) => (this.liste = liste), error: () => (this.liste = []) });
  }

  /** Zu sehen fuer eine neue Aussage per Text (themenWaehlbar), wenn die Liste da ist. */
  zeigtFuer(aussage: AntwortAuf): boolean {
    return this.liste.length > 0 && themenWaehlbar(aussage);
  }

  /**
   * Ist keine Themenwahl mehr moeglich (eine vorhandene Aussage gewaehlt, das Feld
   * leer), fallen die gewaehlten Themen weg: Unsichtbar mitgefuehrt kaemen sie
   * spaeter ungesehen mit einer anderen Aussage zurueck.
   */
  anAussageAnpassen(aussage: AntwortAuf): void {
    if (!themenWaehlbar(aussage) && this.themen.value?.length) {
      this.themen.setValue([]);
    }
  }

  setzen(themen: string[]): void {
    this.themen.setValue(themen);
  }
}
