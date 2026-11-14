import { ChangeDetectionStrategy, Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Clipboard } from '@angular/cdk/clipboard';
import { TextFieldModule } from '@angular/cdk/text-field';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { Platzhalter, ohnePlatzhalter, platzhalterFuellen, platzhalterIn } from '../../shared/platzhalter';
import { PLATZHALTER_TEXTE } from './platzhalter-texte';

export interface PlatzhalterDialogDaten {
  /** Der Text, wie er kopiert würde, mit mindestens einem Platzhalter „[Hier …]“. */
  text: string;
}

/** Was in der Zwischenablage gelandet ist; undefined = abgebrochen, nichts kopiert. */
export interface PlatzhalterErgebnis {
  text: string;
}

/**
 * Vor dem Kopieren eines Texts mit Platzhalter (Persona-Test Dennis, 13.11.): je
 * Platzhalter ein Feld für den eigenen Satz, der Hinweis aus der Klammer darüber.
 * „Kopieren“ geht erst, wenn alle gefüllt sind; „Ohne Platzhalter kopieren“ nimmt die
 * Klammer-Stellen heraus. Kopiert wird hier im Klick selbst und nicht erst nach dem
 * Schließen: Manche Browser erlauben die Zwischenablage nur direkt in der Geste.
 */
@Component({
  selector: 'app-platzhalter-dialog',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TextFieldModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 mat-dialog-title>{{ platzhalter.length === 1 ? texte.titel : texte.titelMehrere }}</h2>
    <form [formGroup]="formular" (ngSubmit)="kopieren()">
      <mat-dialog-content>
        <p class="platzhalter-einleitung">{{ texte.einleitung }}</p>
        <div class="platzhalter-feld" *ngFor="let p of platzhalter; let i = index">
          <p class="platzhalter-hinweis" [id]="'platzhalter-hinweis-' + i">{{ p.hinweis }}</p>
          <mat-form-field appearance="outline" subscriptSizing="dynamic">
            <mat-label>{{ platzhalter.length === 1 ? texte.feld : texte.feld + ' ' + (i + 1) }}</mat-label>
            <textarea matInput class="platzhalter-eingabe" [formControl]="saetze.at(i)"
                      [attr.aria-describedby]="'platzhalter-hinweis-' + i"
                      cdkTextareaAutosize cdkAutosizeMinRows="2" cdkAutosizeMaxRows="6"></textarea>
          </mat-form-field>
        </div>
      </mat-dialog-content>
      <mat-dialog-actions class="platzhalter-aktionen">
        <button mat-button type="button" class="abbrechen" mat-dialog-close>{{ texte.abbrechen }}</button>
        <button mat-button type="button" class="ohne-platzhalter" (click)="ohneKopieren()">{{ texte.ohne }}</button>
        <button mat-flat-button type="submit" class="mit-satz" [disabled]="saetze.invalid">{{ texte.kopieren }}</button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .platzhalter-einleitung {
        margin-top: 0;
      }
      .platzhalter-hinweis {
        margin: 8px 0 4px;
        padding: 2px 6px;
        border-radius: 2px;
        background: var(--hint-bg);
        text-decoration: underline dashed;
        text-decoration-color: var(--hint-border);
        text-underline-offset: 3px;
      }
      mat-form-field {
        width: 100%;
      }
      .platzhalter-aktionen {
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 4px;
      }
      .mit-satz:not([disabled]) {
        background-color: var(--primary-fill);
        color: white;
      }
    `,
  ],
})
export class PlatzhalterDialogComponent {
  readonly texte = PLATZHALTER_TEXTE;
  readonly platzhalter: Platzhalter[];
  /** Je Platzhalter ein Pflichtfeld; nur Leerzeichen zählen nicht als gefüllt. */
  readonly saetze: FormArray<FormControl<string>>;
  /** Damit der Kopieren-Knopf über ngSubmit geht und der Browser das Formular nicht abschickt. */
  readonly formular: FormGroup;

  constructor(
    @Inject(MAT_DIALOG_DATA) private daten: PlatzhalterDialogDaten,
    private dialogRef: MatDialogRef<PlatzhalterDialogComponent, PlatzhalterErgebnis>,
    private clipboard: Clipboard,
  ) {
    this.platzhalter = platzhalterIn(daten.text);
    this.saetze = new FormArray(
      this.platzhalter.map(
        () => new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/\S/)] }),
      ),
    );
    this.formular = new FormGroup({ saetze: this.saetze });
  }

  kopieren(): void {
    if (this.saetze.invalid) {
      return;
    }
    this.schliessenMit(platzhalterFuellen(this.daten.text, this.saetze.getRawValue()));
  }

  ohneKopieren(): void {
    this.schliessenMit(ohnePlatzhalter(this.daten.text));
  }

  private schliessenMit(text: string): void {
    this.clipboard.copy(text);
    this.dialogRef.close({ text });
  }
}

/** Öffnet den Dialog; schmal genug fürs Handy, wie der Melde-Dialog. */
export function platzhalterDialogOeffnen(
  dialog: MatDialog,
  text: string,
): MatDialogRef<PlatzhalterDialogComponent, PlatzhalterErgebnis> {
  return dialog.open<PlatzhalterDialogComponent, PlatzhalterDialogDaten, PlatzhalterErgebnis>(PlatzhalterDialogComponent, {
    width: '500px',
    maxWidth: '95vw',
    data: { text },
    autoFocus: 'first-tabbable',
  });
}
