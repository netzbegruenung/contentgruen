import { NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, ElementRef, HostListener, Inject, signal } from '@angular/core';
import { MAT_BOTTOM_SHEET_DATA, MatBottomSheetRef } from '@angular/material/bottom-sheet';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { filter, finalize, switchMap } from 'rxjs/operators';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenDaten } from './karten-daten';
import { ContributionsService } from '../services/contributions.service';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/** Ab so vielen Pixeln nach unten schliesst ein Wisch das Sheet. */
export const WISCH_SCHWELLE = 80;

/** loeschbar nur aus "Meine Beitraege": dort ist es sicher der eigene Beitrag. */
export type BeitragSheetDaten = KartenDaten & { loeschbar?: boolean };

/** Ergebnis des Sheets, wenn der Autor den Beitrag geloescht hat; die Liste laedt dann neu. */
export const GELOESCHT = 'geloescht';

const LOESCHEN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Beitrag löschen?',
  text:
    'Niemand findet ihn danach mehr, auch nicht in „Meine Beiträge“. Gespeichert bleibt er trotzdem, ' +
    'und zurückholen kannst du ihn nicht. Macht er dich erkennbar, entfernen wir ihn auf deinen Hinweis ganz ' +
    '(siehe Datenschutz).',
  ja: 'Löschen',
  nein: 'Abbrechen',
};

/**
 * Was beim Loeschen schiefging. 401 behandelt der Auth-Interceptor (Anmeldung); 403
 * heisst, der Beitrag ist nicht der eigene, und "noch einmal" waere ein falscher Rat.
 */
export function loeschenFehlertext(status: number | undefined): string {
  if (status === 403) {
    return 'Löschen kann nur der Autor des Beitrags.';
  }
  return 'Löschen hat nicht geklappt. Versuch es gleich noch einmal.';
}

/**
 * Ein Beitrag aus dem Album als volle Karte im Bottom Sheet, mit Kopieren, Melden und
 * Herkunft; ohne Abstimmen, weil es der eigene Beitrag ist. Klick ausserhalb und Escape schliessen ueber MatBottomSheet selbst; den
 * Wisch nach unten bringt Material nicht mit. Er zaehlt nur, solange das Sheet ganz
 * oben steht, sonst gehoert die Geste dem Scrollen im Sheet.
 *
 * Mit loeschbar kann der Autor den Beitrag nach einer Rueckfrage loeschen (#250); das
 * Sheet schliesst dann mit GELOESCHT.
 */
@Component({
  selector: 'app-beitrag-sheet',
  standalone: true,
  imports: [NgIf, BeitragskarteComponent, MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sheet-griff" aria-hidden="true"></div>
    <!-- Der eigene Beitrag: nicht abstimmen, Kopieren und Melden bleiben -->
    <app-beitragskarte [daten]="daten" variante="voll" [abstimmenSichtbar]="false"></app-beitragskarte>
    <div class="sheet-fuss" *ngIf="daten.loeschbar">
      <button
        mat-button
        type="button"
        class="loeschen-knopf"
        [disabled]="loeschtGerade()"
        (click)="loeschen()"
      >
        <mat-icon>delete</mat-icon>
        Beitrag löschen
      </button>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        padding-bottom: 16px;
      }

      .sheet-griff {
        width: 40px;
        height: 4px;
        margin: 4px auto 12px;
        border-radius: 2px;
        background: rgba(0, 0, 0, 0.24);
      }

      app-beitragskarte {
        display: block;
        max-width: 450px;
        margin: 0 auto;
      }

      .sheet-fuss {
        display: flex;
        justify-content: flex-end;
        max-width: 450px;
        margin: 8px auto 0;
      }

      .loeschen-knopf {
        color: var(--error-color);
      }
    `,
  ],
})
export class BeitragSheetComponent {
  private wischStart: number | null = null;

  /** Solange Rueckfrage oder Anfrage laufen: ein zweiter Klick oeffnet keine zweite Rueckfrage. */
  readonly loeschtGerade = signal(false);

  constructor(
    @Inject(MAT_BOTTOM_SHEET_DATA) readonly daten: BeitragSheetDaten,
    private sheet: MatBottomSheetRef<BeitragSheetComponent>,
    private element: ElementRef<HTMLElement>,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private beitraege: ContributionsService,
  ) {}

  /** Ein 404 heisst: schon geloescht oder gesperrt. Fuer die Liste ist er so oder so weg. */
  loeschen(): void {
    if (this.loeschtGerade()) {
      return;
    }
    this.loeschtGerade.set(true);
    this.dialog
      .open(BestaetigungsDialogComponent, { data: LOESCHEN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(
        filter((ja) => ja === true),
        switchMap(() => this.beitraege.beitragLoeschen(this.daten.id)),
        finalize(() => this.loeschtGerade.set(false)),
      )
      .subscribe({
        next: () => this.weg('Beitrag gelöscht'),
        error: (fehler) => {
          if (fehler?.status === 404) {
            this.weg('Der Beitrag ist nicht mehr da.');
            return;
          }
          this.snackBar.open(loeschenFehlertext(fehler?.status), 'OK', { duration: 5000 });
        },
      });
  }

  /** Der Beitrag ist fuer die Liste weg: geloescht oder inzwischen nicht mehr da (404). */
  private weg(meldung: string): void {
    this.snackBar.open(meldung, 'OK', { duration: 3000 });
    this.sheet.dismiss(GELOESCHT);
  }

  @HostListener('touchstart', ['$event'])
  wischBeginnen(event: TouchEvent): void {
    const container = this.element.nativeElement.closest('.mat-bottom-sheet-container');
    const obenAngekommen = (container?.scrollTop ?? 0) <= 0;
    this.wischStart = obenAngekommen ? (event.touches[0]?.clientY ?? null) : null;
  }

  @HostListener('touchend', ['$event'])
  wischBeenden(event: TouchEvent): void {
    const ende = event.changedTouches[0]?.clientY;
    if (this.wischStart !== null && ende !== undefined && ende - this.wischStart > WISCH_SCHWELLE) {
      this.sheet.dismiss();
    }
    this.wischStart = null;
  }
}
