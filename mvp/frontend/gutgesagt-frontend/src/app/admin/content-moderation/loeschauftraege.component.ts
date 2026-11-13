import { Component, EventEmitter, HostListener, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { filter } from 'rxjs';
import { Loeschauftrag, LoeschauftragAusgefuehrt, ModerationService } from '../../services/moderation.service';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

/** Kennzeichen des Backends (api/v1/loeschauftraege.py): Stand während der Ausführung geändert. */
export const STAND_GEAENDERT = 'loeschauftrag_stand_geaendert';

/** So oft lädt die Liste nach, solange der Reiter sichtbar ist. */
export const NACHLADEN_MS = 30_000;

const AUSFUEHREN_FRAGE: BestaetigungsDialogDaten = {
  titel: 'Löschablauf ausführen?',
  text:
    'Die Beiträge der Person zeigen danach „ehemalige Person“, ihre Einwürfe werden gelöscht, und ihre Sätze an ' +
    'Einwürfen anderer verlieren ihren Namen, soweit sie vor einer neuen Einwilligung entstanden sind; was danach ' +
    'kam, bleibt. Das lässt sich nicht rückgängig machen. Konto und Anzeigename bleiben.',
  ja: 'Löschablauf ausführen',
  nein: 'Abbrechen',
};

/**
 * Löschaufträge nach dem Widerruf der Art.-9-Einwilligung (Glossar „Löschauftrag“, DSFA R9b).
 * Ein Admin führt binnen der Frist den Löschablauf aus; überfällige stehen hervorgehoben oben.
 * Die Liste lädt selbst nach: beim Zurückkehren auf den Reiter und alle NACHLADEN_MS, solange er
 * sichtbar ist. Niemand muss die Seite neu laden.
 */
@Component({
  selector: 'app-loeschauftraege',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
  template: `
    <p class="hinweis">
      Wer die Einwilligung widerruft, bekommt einen Löschauftrag. Binnen {{ fristTage }} Tagen den Löschablauf ausführen:
      Beiträge zeigen dann „ehemalige Person“, eigene Einwürfe werden gelöscht, Sätze an fremden Einwürfen verlieren den
      Namen. Danach die Texte der Beiträge durchsehen (Löschkonzept, Schritt 3).
    </p>

    <div *ngIf="auftraege === null" class="laedt" role="status">
      <mat-spinner diameter="32"></mat-spinner>
      <span>{{ fehler ? 'Löschaufträge gerade nicht erreichbar, neuer Versuch in Kürze …' : 'Lade Löschaufträge …' }}</span>
    </div>

    <ng-container *ngIf="auftraege !== null">
      <div *ngIf="fehler" class="laedt klein" role="status">
        <mat-spinner diameter="16"></mat-spinner>
        <span>Aktualisieren gerade nicht möglich, neuer Versuch in Kürze …</span>
      </div>
      <p *ngIf="auftraege.length === 0" class="leer">Keine offenen Löschaufträge.</p>
      <div
        *ngFor="let a of auftraege"
        class="auftrag mat-elevation-z1"
        [class.ueberfaellig]="a.ueberfaellig"
        data-testid="loeschauftrag"
      >
        <div class="person">
          <strong>{{ a.anzeigename || a.user_id }}</strong>
          <span *ngIf="a.anzeigename"> ({{ a.user_id }})</span>
        </div>
        <div>Widerrufen am {{ datum(a.widerrufen_am) }}</div>
        <div *ngIf="a.neu_eingewilligt_am" class="neu-eingewilligt" data-testid="neu-eingewilligt">
          <mat-icon aria-hidden="true">info</mat-icon>
          Neu eingewilligt am {{ datum(a.neu_eingewilligt_am) }}: was ab da kam, bleibt
        </div>
        <div class="frist">
          <mat-icon *ngIf="a.ueberfaellig" aria-hidden="true">warning</mat-icon>
          {{ a.ueberfaellig ? 'Überfällig seit' : 'Frist bis' }} {{ datum(a.frist) }}
        </div>
        <button
          mat-raised-button
          color="warn"
          type="button"
          [disabled]="ausfuehrend !== null"
          (click)="ausfuehren(a)"
        >
          <ng-container *ngIf="ausfuehrend === a.id; else knopf">
            <mat-spinner diameter="18" class="im-knopf"></mat-spinner>
            Wird ausgeführt …
          </ng-container>
          <ng-template #knopf>
            <mat-icon>delete_sweep</mat-icon>
            Löschablauf ausführen
          </ng-template>
        </button>
      </div>
    </ng-container>
  `,
  styles: [`
    .hinweis { margin: 0 0 16px; }
    .laedt { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
    .laedt.klein { margin: 0 0 8px; font-size: 0.875rem; color: var(--text-secondary); }
    .auftrag { padding: 12px; margin-bottom: 8px; display: grid; gap: 4px; overflow-wrap: anywhere;
               border-left: 4px solid transparent; }
    .auftrag button { justify-self: start; margin-top: 4px; }
    .auftrag.ueberfaellig { border-left-color: var(--error-color); }
    .auftrag.ueberfaellig .frist { color: var(--error-color); font-weight: 700; }
    .frist, .neu-eingewilligt { display: flex; align-items: center; gap: 4px; }
    .im-knopf { display: inline-block; margin-right: 8px; vertical-align: middle; }
  `],
})
export class LoeschauftraegeComponent implements OnInit, OnDestroy {
  /** Zahl der offenen Aufträge nach jedem Laden, für die Zahl am Umschalter. */
  @Output() anzahl = new EventEmitter<number>();

  /** null: noch nie geladen. */
  auftraege: Loeschauftrag[] | null = null;
  fristTage = 7;
  fehler = false;
  /** Kennung des Auftrags, der gerade ausgeführt wird. */
  ausfuehrend: string | null = null;
  private laedtGerade = false;
  private takt: ReturnType<typeof setInterval> | null = null;

  constructor(
    private moderation: ModerationService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.laden();
    this.takt = setInterval(() => {
      if (document.visibilityState === 'visible') {
        this.laden();
      }
    }, NACHLADEN_MS);
  }

  ngOnDestroy(): void {
    if (this.takt !== null) {
      clearInterval(this.takt);
    }
  }

  /** Zurück auf dem Reiter: sofort nachladen, statt bis zum nächsten Takt zu warten. */
  @HostListener('document:visibilitychange')
  sichtbarkeitGeaendert(): void {
    if (document.visibilityState === 'visible') {
      this.laden();
    }
  }

  ausfuehren(auftrag: Loeschauftrag): void {
    if (this.ausfuehrend !== null) {
      return;
    }
    this.dialog
      .open(BestaetigungsDialogComponent, { data: AUSFUEHREN_FRAGE, autoFocus: 'dialog' })
      .afterClosed()
      .pipe(filter((ja) => ja === true))
      .subscribe(() => {
        this.ausfuehrend = auftrag.id;
        this.moderation.loeschauftragAusfuehren(auftrag.id).subscribe({
          next: (ergebnis) => {
            this.ausfuehrend = null;
            this.snackBar.open(ergebnisText(ergebnis), 'OK', { duration: 8000 });
            this.laden();
          },
          error: (fehler) => {
            this.ausfuehrend = null;
            const text =
              fehler?.status === 409 && fehler?.error?.detail === STAND_GEAENDERT
                ? 'Die Person hat währenddessen widerrufen oder neu eingewilligt; der Auftrag bleibt offen. ' +
                  'Bitte erneut ausführen.'
                : fehler?.status === 409
                ? 'Der Löschauftrag ist schon erledigt.'
                : fehler?.status === 404
                  ? 'Den Löschauftrag gibt es nicht mehr, etwa nach einer Kontolöschung.'
                  : 'Löschablauf fehlgeschlagen; der Auftrag bleibt offen. Erneut ausführen holt nach, was fehlt.';
            this.snackBar.open(text, 'OK', { duration: 8000 });
            this.laden();
          },
        });
      });
  }

  datum(wert: string): string {
    return new Date(wert).toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private laden(): void {
    if (this.laedtGerade) {
      return;
    }
    this.laedtGerade = true;
    this.moderation.getLoeschauftraege().subscribe({
      next: (antwort) => {
        this.laedtGerade = false;
        this.fehler = false;
        this.fristTage = antwort.frist_tage;
        this.auftraege = antwort.auftraege;
        this.anzahl.emit(antwort.auftraege.length);
      },
      error: () => {
        this.laedtGerade = false;
        this.fehler = true;
      },
    });
  }
}

function anzahl(n: number, eins: string, viele: string): string {
  return n === 1 ? `1 ${eins}` : `${n} ${viele}`;
}

function ergebnisText(e: LoeschauftragAusgefuehrt): string {
  return (
    `Erledigt: ${anzahl(e.beitraege, 'Beitrag', 'Beiträge')} anonymisiert, ` +
    `${anzahl(e.einwuerfe, 'Einwurf', 'Einwürfe')} gelöscht, ` +
    `${anzahl(e.saetze, 'Satz', 'Sätze')} ohne Namen.`
  );
}
