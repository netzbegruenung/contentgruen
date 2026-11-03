import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { filter } from 'rxjs';
import { AngabenGeloescht, ContentReport, MelderSuche, ModerationService } from '../../services/moderation.service';
import { meldegrundLabel } from '../../shared/meldegruende';
import { meldungsstatusLabel } from '../../shared/meldungsstatus';
import {
  BestaetigungsDialogComponent,
  BestaetigungsDialogDaten,
} from '../../shared/components/bestaetigungs-dialog/bestaetigungs-dialog.component';

const LOESCHEN_TEXT =
  'Bearbeitete und abgewiesene Meldungen mit diesen Angaben werden gelöscht. Offene bleiben zur ' +
  'Bearbeitung stehen, ohne Name und E-Mail-Adresse; die Entscheidung kann der Person dann niemand mehr mitteilen.';

/**
 * Die Rückfrage vor dem Löschen. Nach einer Suche nur mit dem Namen können die Treffer
 * verschiedene Personen sein: Dann bestätigt der Admin ausdrücklich, dass alle Treffer
 * dieselbe Person sind; das Backend löscht sonst nicht.
 */
function loeschenFrage(nurName: boolean, anzahl: number): BestaetigungsDialogDaten {
  if (!nurName) {
    return { titel: 'Angaben der Person löschen?', text: LOESCHEN_TEXT, ja: 'Angaben löschen', nein: 'Abbrechen' };
  }
  const treffer = anzahl === 1 ? 'Der Treffer gehört' : `Alle ${anzahl} Treffer gehören`;
  return {
    titel: `${treffer} zu derselben Person?`,
    text:
      'Gesucht wurde nur nach dem Namen; den können mehrere Personen tragen. Bitte jeden Treffer prüfen. ' +
      LOESCHEN_TEXT,
    ja: 'Ja, dieselbe Person: Angaben löschen',
    nein: 'Abbrechen',
  };
}

/**
 * Meldungen einer Person nach Name oder E-Mail-Adresse finden und ihre Angaben löschen
 * (#494). Gelöscht werden nur die gezeigten Treffer. Wer ohne Konto meldet, ist nur über diese Angaben zu finden: Die Liste ist die
 * Auskunft (Art. 15 DSGVO), „Angaben löschen“ die Löschung (Art. 17 DSGVO).
 */
@Component({
  selector: 'app-meldungen-einer-person',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSnackBarModule,
  ],
  template: `
    <form class="melder-suche" (ngSubmit)="suchen()">
      <p class="hinweis">
        Für Auskunft oder Löschung auf Verlangen einer Person ohne Konto. Gesucht wird die ganze Angabe,
        Groß- und Kleinschreibung zählen nicht; sind beide angegeben, müssen beide passen. Bei einer Suche nur
        nach dem Namen prüfen, ob alle Treffer dieselbe Person sind.
      </p>
      <mat-form-field appearance="outline">
        <mat-label>E-Mail-Adresse</mat-label>
        <input matInput name="email" type="text" autocomplete="off" [(ngModel)]="email" />
      </mat-form-field>
      <mat-form-field appearance="outline">
        <mat-label>Name</mat-label>
        <input matInput name="name" type="text" autocomplete="off" [(ngModel)]="name" />
      </mat-form-field>
      <button mat-raised-button color="primary" type="submit" [disabled]="!eingabe() || suchtGerade || loeschtGerade">
        <mat-icon>search</mat-icon>
        Suchen
      </button>
    </form>

    <p *ngIf="fehler" class="error">{{ fehler }}</p>

    <ng-container *ngIf="treffer && !fehler">
      <p *ngIf="treffer.length === 0" class="leer">Keine Meldungen mit diesen Angaben.</p>
      <ng-container *ngIf="treffer.length > 0">
        <div class="treffer-kopf">
          <strong>{{ treffer.length === 1 ? '1 Meldung' : treffer.length + ' Meldungen' }}</strong>
          <button mat-raised-button color="warn" type="button" [disabled]="suchtGerade || loeschtGerade" (click)="angabenLoeschen()">
            <mat-icon>delete</mat-icon>
            Angaben löschen
          </button>
        </div>
        <div *ngFor="let m of treffer" class="treffer mat-elevation-z1">
          <div><strong>{{ statusLabel(m.status) }}</strong> · {{ formatDate(m.created) }} · {{ grundLabel(m.reason) }}</div>
          <div *ngIf="m.description">Beschreibung: {{ m.description }}</div>
          <div>Beitrag: <code>{{ m.content_id }}</code></div>
          <div *ngIf="m.melder_name">Name: {{ m.melder_name }}</div>
          <div *ngIf="m.melder_email">E-Mail-Adresse: {{ m.melder_email }}</div>
          <div *ngIf="m.reported_by_user_id">Kennung: {{ m.reported_by_user_id }}</div>
          <div *ngIf="m.resolution_notes">Notiz: {{ m.resolution_notes }}</div>
        </div>
      </ng-container>
    </ng-container>
  `,
  styles: [`
    .melder-suche { display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline; }
    .melder-suche .hinweis { flex-basis: 100%; margin: 0; }
    .treffer-kopf { display: flex; justify-content: space-between; align-items: center; margin: 16px 0 8px; }
    .treffer { padding: 12px; margin-bottom: 8px; display: grid; gap: 4px; overflow-wrap: anywhere; }
    .error { color: var(--error-color); }
  `],
})
export class MeldungenEinerPersonComponent {
  email = '';
  name = '';
  /** null: noch nicht gesucht. */
  treffer: ContentReport[] | null = null;
  fehler: string | null = null;
  suchtGerade = false;
  loeschtGerade = false;
  /** Die Angaben der gezeigten Treffer; „Angaben löschen“ nimmt diese, nicht die Felder. */
  private gesucht: MelderSuche | null = null;

  constructor(
    private moderation: ModerationService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  /** Die Angaben aus den Feldern; null, wenn beide leer sind. */
  eingabe(): MelderSuche | null {
    const email = this.email.trim() || null;
    const name = this.name.trim() || null;
    return email || name ? { email, name } : null;
  }

  suchen(): void {
    const suche = this.eingabe();
    if (suche && !this.loeschtGerade) {
      this.laden(suche);
    }
  }

  angabenLoeschen(): void {
    const suche = this.gesucht;
    const ids = (this.treffer ?? []).map((m) => m.id);
    if (!suche || ids.length === 0 || this.suchtGerade || this.loeschtGerade) {
      return;
    }
    const nurName = !suche.email;
    this.dialog
      .open(BestaetigungsDialogComponent, { data: loeschenFrage(nurName, ids.length), autoFocus: 'dialog' })
      .afterClosed()
      .pipe(filter((ja) => ja === true))
      .subscribe(() => {
        this.loeschtGerade = true;
        this.moderation.angabenLoeschen(suche, ids, nurName).subscribe({
          next: (ergebnis) => {
            this.loeschtGerade = false;
            this.snackBar.open(ergebnisText(ergebnis), 'OK', { duration: 5000 });
            this.laden(suche);
          },
          error: () => {
            this.loeschtGerade = false;
            this.snackBar.open('Fehler beim Löschen der Angaben', 'OK', { duration: 5000 });
          },
        });
      });
  }

  statusLabel(status: string): string {
    return meldungsstatusLabel(status);
  }

  grundLabel(grund: string): string {
    return meldegrundLabel(grund);
  }

  formatDate(datum: string): string {
    return new Date(datum).toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private laden(suche: MelderSuche): void {
    this.suchtGerade = true;
    this.fehler = null;
    this.moderation.meldungenEinerPerson(suche).subscribe({
      next: (antwort) => {
        this.treffer = antwort.reports;
        this.gesucht = suche;
        this.suchtGerade = false;
      },
      error: () => {
        this.treffer = null;
        this.gesucht = null;
        this.fehler = 'Fehler bei der Suche';
        this.suchtGerade = false;
      },
    });
  }
}

function ergebnisText(ergebnis: AngabenGeloescht): string {
  const erledigte = ergebnis.geloescht === 1 ? '1 erledigte Meldung' : `${ergebnis.geloescht} erledigte Meldungen`;
  return `${erledigte} gelöscht, ${ergebnis.angaben_entfernt} offene ohne Name und E-Mail-Adresse`;
}
