import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { SPERRGRUENDE, SperrgrundWert } from '../../shared/sperrgruende';

/** Höchstlänge der Begründung, wie im Suchdienst. */
export const BEGRUENDUNG_MAX = 2000;

/**
 * 'sperren': Sperrgrund und Begründung für eine neue Sperre.
 * 'bestaetigen': nach einem Widerspruch nur die Begründung, warum die Sperre bleibt.
 */
export interface SperrenDialogDaten {
  art: 'sperren' | 'bestaetigen';
  titel: string;
  /** Der Text des Beitrags, damit vor der Entscheidung gelesen werden kann, worum es geht. */
  text?: string | null;
  /** Beim Bestätigen: der Widerspruch des Autors (null: ohne Text). */
  widerspruch?: string | null;
}

export interface SperrenDialogErgebnis {
  sperrgrund: SperrgrundWert | null;
  begruendung: string;
}

/**
 * Fragt vor dem Sperren Sperrgrund und Begründung ab (#448); ohne beides lässt er
 * nicht sperren. Beides liest der Autor in seiner Sperrnachricht, deshalb steht der
 * Hinweis darauf über dem Feld.
 */
@Component({
  selector: 'app-sperren-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ daten.art === 'sperren' ? 'Beitrag sperren' : 'Sperre bestätigen' }}</h2>
    <div mat-dialog-content>
      <p class="sperren-titel">„{{ daten.titel }}“</p>
      <!-- Erst lesen, dann entscheiden: Text und Widerspruch stehen im Dialog (Persona-Test 13.11.) -->
      <div *ngIf="daten.text" class="sperren-zitat">
        <p class="zitat-label">Text des Beitrags</p>
        <p class="zitat-text">{{ daten.text }}</p>
      </div>
      <div *ngIf="daten.art === 'bestaetigen'" class="sperren-zitat">
        <p class="zitat-label">Widerspruch des Autors</p>
        <p class="zitat-text">{{ daten.widerspruch ? '„' + daten.widerspruch + '“' : 'ohne Text' }}</p>
      </div>
      <p *ngIf="daten.art === 'sperren'">
        Der Beitrag verschwindet aus Suche und Ansicht, bleibt aber erhalten; die Sperre lässt sich
        aufheben. Alle Meldungen zum Beitrag stehen danach auf bearbeitet.
      </p>
      <p *ngIf="daten.art === 'bestaetigen'">
        Der Autor hat widersprochen. Bleibt die Sperre nach erneuter Prüfung, sag ihm, warum.
        Soll sie nicht bleiben: abbrechen und entsperren.
      </p>
      <p class="sperren-hinweis">
        Der Autor liest {{ daten.art === 'sperren' ? 'Sperrgrund und Begründung' : 'die Begründung' }} in „Meine Beiträge“.
      </p>

      <mat-form-field *ngIf="daten.art === 'sperren'" appearance="outline" class="volle-breite">
        <mat-label>Sperrgrund</mat-label>
        <mat-select [(ngModel)]="sperrgrund" required>
          <mat-option *ngFor="let grund of sperrgruende" [value]="grund.value">{{ grund.label }}</mat-option>
        </mat-select>
      </mat-form-field>

      <mat-form-field appearance="outline" class="volle-breite">
        <mat-label>Begründung</mat-label>
        <textarea matInput [(ngModel)]="begruendung" rows="4" required
                  [maxlength]="BEGRUENDUNG_MAX"
                  placeholder="Was genau am Beitrag nicht in Ordnung ist"></textarea>
        <mat-hint align="end">{{ begruendung.length }} / {{ BEGRUENDUNG_MAX }}</mat-hint>
      </mat-form-field>
    </div>
    <div mat-dialog-actions align="end">
      <button mat-button type="button" (click)="abbrechen()">Abbrechen</button>
      <button mat-raised-button color="warn" type="button" [disabled]="!vollstaendig" (click)="bestaetigen()">
        {{ daten.art === 'sperren' ? 'Sperren' : 'Sperre bestätigen' }}
      </button>
    </div>
  `,
  styles: [
    `
      .volle-breite { width: 100%; }
      .sperren-titel { font-weight: 500; }
      .sperren-hinweis { color: var(--text-secondary); }
      .sperren-zitat { margin: 0 0 12px; padding: 8px 12px; border-left: 3px solid var(--divider-color); }
      .zitat-label { margin: 0 0 4px; font-size: 0.8125rem; color: var(--text-secondary); }
      .zitat-text { margin: 0; max-height: 12em; overflow-y: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
    `,
  ],
})
export class SperrenDialogComponent {
  readonly sperrgruende = SPERRGRUENDE;
  readonly BEGRUENDUNG_MAX = BEGRUENDUNG_MAX;
  sperrgrund: SperrgrundWert | null = null;
  begruendung = '';

  constructor(
    private dialogRef: MatDialogRef<SperrenDialogComponent, SperrenDialogErgebnis>,
    @Inject(MAT_DIALOG_DATA) public daten: SperrenDialogDaten,
  ) {}

  /** Ohne Begründung nie; beim Sperren auch nicht ohne Sperrgrund. */
  get vollstaendig(): boolean {
    return !!this.begruendung.trim() && (this.daten.art === 'bestaetigen' || !!this.sperrgrund);
  }

  bestaetigen(): void {
    if (!this.vollstaendig) {
      return;
    }
    this.dialogRef.close({ sperrgrund: this.sperrgrund, begruendung: this.begruendung.trim() });
  }

  abbrechen(): void {
    this.dialogRef.close();
  }
}
