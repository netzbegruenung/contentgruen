import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';

/** Die festen Gründe fürs Abweisen; „Anderer Grund“ verlangt einen eigenen Satz. */
export const ABWEISUNGSGRUENDE: readonly string[] = [
  'Kein Verstoß gegen die Nutzungsbedingungen',
  'Zulässige Meinungsäußerung',
  'Das Gemeldete steht nicht im Beitrag',
  'Schon entschieden (doppelte Meldung)',
  'Anderer Grund',
];

export const ANDERER_GRUND = 'Anderer Grund';

/** Höchstlänge der ganzen Begründung: Sie steht als notes in der Adresse (Logs, Grenze der URL-Länge). */
export const ABWEISUNG_MAX = 500;

export interface AbweisenDialogDaten {
  /** Titel oder Anfang des gemeldeten Beitrags. */
  titel: string;
  /** Der Meldegrund, wie die meldende Person ihn gewählt hat. */
  meldegrund: string;
  /** Hat die meldende Person eine E-Mail-Adresse angegeben? Dann geht die Entscheidung per Mail raus. */
  mitMail: boolean;
}

/**
 * Fragt vor dem Abweisen einer Meldung die Begründung ab: ein Grund aus fester Liste, dazu
 * ein freier Satz (bei „Anderer Grund“ Pflicht). Die Begründung bleibt intern an der Meldung
 * (resolution_notes); die meldende Person bekommt per Mail nur die Entscheidung mit festem
 * Text (meldung_mitteilen.py). Rückgängig gibt es nicht: Das Backend kennt kein Wiedereröffnen.
 */
@Component({
  selector: 'app-abweisen-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatSelectModule, MatInputModule],
  template: `
    <h2 mat-dialog-title>Meldung abweisen</h2>
    <div mat-dialog-content>
      <p class="abweisen-titel">„{{ daten.titel }}“</p>
      <p class="abweisen-meldegrund">Gemeldet als: {{ daten.meldegrund }}</p>
      <p>
        Der Beitrag bleibt sichtbar. Das Abweisen lässt sich nicht zurücknehmen.
      </p>
      <p class="abweisen-hinweis">
        {{ daten.mitMail
          ? 'Die meldende Person erfährt per Mail nur, dass abgewiesen wurde. Deine Begründung sieht nur das Moderationsteam.'
          : 'Ohne E-Mail-Adresse erfährt die meldende Person nichts. Die Begründung sieht nur das Moderationsteam.' }}
      </p>

      <mat-form-field appearance="outline" class="volle-breite">
        <mat-label>Grund</mat-label>
        <mat-select [(ngModel)]="grund" required>
          <mat-option *ngFor="let eintrag of gruende" [value]="eintrag">{{ eintrag }}</mat-option>
        </mat-select>
      </mat-form-field>

      <mat-form-field appearance="outline" class="volle-breite">
        <mat-label>{{ grund === andererGrund ? 'Begründung' : 'Begründung (optional)' }}</mat-label>
        <textarea matInput [(ngModel)]="satz" rows="3" [required]="grund === andererGrund"
                  [maxlength]="maxLaenge" placeholder="Ein Satz, warum die Meldung nicht zutrifft"></textarea>
        <mat-hint align="end">{{ satz.length }} / {{ maxLaenge }}</mat-hint>
      </mat-form-field>
    </div>
    <div mat-dialog-actions align="end">
      <button mat-button type="button" (click)="abbrechen()">Abbrechen</button>
      <button mat-raised-button color="primary" type="button" [disabled]="!vollstaendig" (click)="abweisen()">
        Meldung abweisen
      </button>
    </div>
  `,
  styles: [
    `
      .volle-breite { width: 100%; }
      .abweisen-titel { font-weight: 500; }
      .abweisen-meldegrund, .abweisen-hinweis { color: var(--text-secondary); }
    `,
  ],
})
export class AbweisenDialogComponent {
  readonly gruende = ABWEISUNGSGRUENDE;
  readonly andererGrund = ANDERER_GRUND;
  grund: string | null = null;
  satz = '';

  constructor(
    private dialogRef: MatDialogRef<AbweisenDialogComponent, string>,
    @Inject(MAT_DIALOG_DATA) public daten: AbweisenDialogDaten,
  ) {}

  /** Was für den eigenen Satz bleibt: ABWEISUNG_MAX abzüglich Grund und „: “. */
  get maxLaenge(): number {
    return ABWEISUNG_MAX - (this.grund?.length ?? 0) - 2;
  }

  /** Ein Grund ist Pflicht; bei „Anderer Grund“ auch der Satz. */
  get vollstaendig(): boolean {
    return !!this.grund && (this.grund !== ANDERER_GRUND || !!this.satz.trim());
  }

  /** Schließt mit der Begründung, wie sie als notes an das Backend geht. */
  abweisen(): void {
    if (!this.vollstaendig) {
      return;
    }
    const satz = this.satz.trim();
    this.dialogRef.close(satz ? `${this.grund}: ${satz}` : this.grund!);
  }

  abbrechen(): void {
    this.dialogRef.close();
  }
}
