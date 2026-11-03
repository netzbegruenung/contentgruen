import { ChangeDetectionStrategy, Component, Inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { NgIf } from '@angular/common';
import { finalize } from 'rxjs/operators';

import { KartenDaten, KartenQuelle } from './karten-daten';
import { TEXT_MAX as KOMMENTAR_TEXT_MAX, TITEL_MAX } from '../add-commentary/add-commentary.component';
import { TEXT_MAX as HINTERGRUNDINFO_TEXT_MAX } from '../add-generictext/add-generictext.component';
import { ReferenceInputComponent } from '../reference-input/reference-input.component';
import { Cc0HinweisComponent } from '../shared/cc0-hinweis/cc0-hinweis.component';
import { HerkunftEingabe, MeineBeitraegeService } from '../services/meine-beitraege.service';

/** Wie in den Formularen beim Anlegen. */
export const TEXT_MIN = 10;

/** Die Beitragstypen, die der Autor aendern kann (#299), mit der Grenze ihres Texts wie beim Anlegen. */
export const AENDERBARE_TYPEN: Readonly<Record<string, number>> = {
  commentary: KOMMENTAR_TEXT_MAX,
  generictext: HINTERGRUNDINFO_TEXT_MAX,
};

export function istAenderbar(typ: string | null): boolean {
  return typ !== null && typ in AENDERBARE_TYPEN;
}

/** Was beim Speichern schiefging; 401 behandelt der Auth-Interceptor. */
export function aendernFehlertext(fehler: { status?: number; error?: any } | undefined): string {
  const grund = fehler?.error?.detail;
  if (fehler?.status === 400 && typeof grund === 'string') {
    return grund;
  }
  if (fehler?.status === 422) {
    return 'Titel oder Text passen nicht. Der Titel braucht mindestens 3 Zeichen, der Text 10.';
  }
  if (fehler?.status === 403) {
    return 'Ändern kann nur der Autor des Beitrags.';
  }
  if (fehler?.status === 404) {
    return 'Den Beitrag gibt es nicht mehr.';
  }
  return 'Speichern hat nicht geklappt. Versuch es gleich noch einmal.';
}

/**
 * Die Herkunft einer Karte als Eingabe, mit der Notiz dieses Beitrags. Nicht mit der
 * Beschreibung der Karte: Ohne Notiz zeigt sie den Text der Herkunft, der sonst zur
 * Notiz wuerde.
 */
function alsEingabe(quelle: KartenQuelle): HerkunftEingabe {
  return { reference_string: quelle.url!, description: quelle.notiz };
}

/**
 * Der Autor aendert Titel, Text und Herkunft seines Kommentars oder seiner
 * Hintergrundinfo (#299). Schliesst mit true, wenn gespeichert ist.
 */
@Component({
  selector: 'app-beitrag-aendern-dialog',
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    TextFieldModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    ReferenceInputComponent,
    Cc0HinweisComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 mat-dialog-title>Beitrag ändern</h2>
    <form [formGroup]="formular" (ngSubmit)="speichern()" novalidate>
      <mat-dialog-content>
        <mat-form-field appearance="outline" class="feld">
          <mat-label>Titel</mat-label>
          <textarea matInput formControlName="title" required [attr.maxlength]="titelMax"
                    placeholder="Was ist der Punkt? Ein Satz."
                    cdkTextareaAutosize cdkAutosizeMinRows="2" cdkAutosizeMaxRows="4"
                    (keydown.enter)="$event.preventDefault()"></textarea>
          <mat-hint align="end">{{ formular.value.title?.length ?? 0 }} / {{ titelMax }}</mat-hint>
          <mat-error *ngIf="formular.controls.title.hasError('required')">Der Titel fehlt.</mat-error>
          <mat-error *ngIf="formular.controls.title.hasError('minlength')">Mindestens 3 Zeichen.</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="feld">
          <mat-label>Text</mat-label>
          <textarea matInput formControlName="text" required [attr.maxlength]="textMax"
                    cdkTextareaAutosize cdkAutosizeMinRows="4" cdkAutosizeMaxRows="12"></textarea>
          <mat-hint align="end">{{ formular.value.text?.length ?? 0 }} / {{ textMax }}</mat-hint>
          <mat-error *ngIf="formular.controls.text.hasError('required')">Der Text fehlt.</mat-error>
          <mat-error *ngIf="formular.controls.text.hasError('minlength')">Mindestens {{ textMin }} Zeichen.</mat-error>
          <mat-error *ngIf="formular.controls.text.hasError('maxlength')">Höchstens {{ textMax }} Zeichen.</mat-error>
        </mat-form-field>

        <app-reference-input formControlName="references" [kompakt]="true"></app-reference-input>

        <p class="fehler" role="alert" *ngIf="fehler()">{{ fehler() }}</p>
        <p appCc0Hinweis></p>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" [mat-dialog-close]="false">Abbrechen</button>
        <button mat-flat-button type="submit" class="speichern-knopf"
                [disabled]="formular.invalid || speichertGerade()">Speichern</button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .feld {
        width: 100%;
      }

      .fehler {
        color: var(--error-color);
        margin: 8px 0 0;
      }

      .speichern-knopf:not([disabled]) {
        background-color: var(--primary-dark);
        color: white;
      }
    `,
  ],
})
export class BeitragAendernDialogComponent {
  readonly titelMax = TITEL_MAX;
  readonly textMin = TEXT_MIN;
  readonly textMax: number;
  readonly speichertGerade = signal(false);
  readonly fehler = signal<string | null>(null);

  readonly formular;

  constructor(
    @Inject(MAT_DIALOG_DATA) private readonly daten: KartenDaten,
    private readonly dialogRef: MatDialogRef<BeitragAendernDialogComponent, boolean>,
    private readonly beitraege: MeineBeitraegeService,
    fb: NonNullableFormBuilder,
  ) {
    this.textMax = AENDERBARE_TYPEN[daten.typ ?? ''] ?? KOMMENTAR_TEXT_MAX;
    this.formular = fb.group({
      // Wie beim Anlegen: eine Behauptung in einem Satz, 3 bis 120 Zeichen (Titelregel).
      title: [daten.titel ?? '', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      text: [daten.text ?? '', [Validators.required, Validators.minLength(TEXT_MIN), Validators.maxLength(this.textMax)]],
      // Herkuenfte, die sich nicht laden liessen, haben keine Adresse und lassen sich nicht anzeigen.
      references: [daten.quellen.filter((q) => !!q.url).map(alsEingabe)],
    });
  }

  speichern(): void {
    if (this.formular.invalid || this.speichertGerade()) {
      return;
    }
    this.speichertGerade.set(true);
    this.fehler.set(null);
    const { title, text, references } = this.formular.getRawValue();
    this.beitraege
      .beitragAendern(this.daten.id, { title: title.trim(), text: text.trim(), references })
      .pipe(finalize(() => this.speichertGerade.set(false)))
      .subscribe({
        next: () => this.dialogRef.close(true),
        error: (fehler) => this.fehler.set(aendernFehlertext(fehler)),
      });
  }
}
