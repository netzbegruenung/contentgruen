import { ChangeDetectionStrategy, Component, Inject, ViewChild, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { NgIf } from '@angular/common';
import { finalize } from 'rxjs/operators';

import { KartenDaten, KartenQuelle } from './karten-daten';
import {
  HINTERGRUNDINFO_TEXT_MAX,
  KOMMENTAR_TEXT_MAX,
  KURZFASSUNG_MAX,
  LANGFASSUNG_MAX,
  TEXT_MIN,
  TITEL_MAX,
} from '../shared/beitrag-grenzen';
import { ReferenceInputComponent } from '../reference-input/reference-input.component';
import { Cc0HinweisComponent } from '../shared/cc0-hinweis/cc0-hinweis.component';
import { BeitragAenderung, HerkunftEingabe, MeineBeitraegeService } from '../services/meine-beitraege.service';

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
  // 400: Grenzen, die nur der Server kennt; 409: eine Meldung ist offen.
  if ((fehler?.status === 400 || fehler?.status === 409) && typeof grund === 'string') {
    return grund;
  }
  if (fehler?.status === 422) {
    return 'Titel, Text oder Herkunft passen nicht. Der Titel braucht 3 bis 120 Zeichen, der Text mindestens 10; höchstens 10 Herkünfte.';
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
 * Hintergrundinfo (#299), beim Kommentar auch Kurz- und Langfassung (#551), damit sie
 * dem neuen Text nicht widersprechen. Schliesst mit true, wenn gespeichert ist.
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

        <ng-container *ngIf="hatFassungen">
          <mat-form-field appearance="outline" class="feld">
            <mat-label>Kurzfassung (optional)</mat-label>
            <textarea matInput id="aendern-kurz" formControlName="kurz" [attr.maxlength]="kurzMax"
                      placeholder="Der Punkt in einem Satz"
                      cdkTextareaAutosize cdkAutosizeMinRows="2" cdkAutosizeMaxRows="6"></textarea>
            <mat-hint>für X/Bluesky</mat-hint>
            <mat-hint align="end">{{ formular.value.kurz?.length ?? 0 }} / {{ kurzMax }}</mat-hint>
            <mat-error *ngIf="formular.controls.kurz.hasError('maxlength')">Höchstens {{ kurzMax }} Zeichen.</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline" class="feld">
            <mat-label>Langfassung (optional)</mat-label>
            <textarea matInput id="aendern-lang" formControlName="lang" [attr.maxlength]="langMax"
                      cdkTextareaAutosize cdkAutosizeMinRows="3" cdkAutosizeMaxRows="12"></textarea>
            <mat-hint align="end">{{ formular.value.lang?.length ?? 0 }} / {{ langMax }}</mat-hint>
            <mat-error *ngIf="formular.controls.lang.hasError('maxlength')">Höchstens {{ langMax }} Zeichen.</mat-error>
          </mat-form-field>
        </ng-container>

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
  readonly kurzMax = KURZFASSUNG_MAX;
  readonly langMax = LANGFASSUNG_MAX;
  /** Kurz- und Langfassung hat nur der Kommentar (GLOSSARY.md, Fassung). */
  readonly hatFassungen: boolean;
  readonly speichertGerade = signal(false);
  readonly fehler = signal<string | null>(null);

  readonly formular;

  @ViewChild(ReferenceInputComponent) referenceInput?: ReferenceInputComponent;

  constructor(
    @Inject(MAT_DIALOG_DATA) private readonly daten: KartenDaten,
    private readonly dialogRef: MatDialogRef<BeitragAendernDialogComponent, boolean>,
    private readonly beitraege: MeineBeitraegeService,
    fb: NonNullableFormBuilder,
  ) {
    this.textMax = AENDERBARE_TYPEN[daten.typ ?? ''] ?? KOMMENTAR_TEXT_MAX;
    this.hatFassungen = daten.typ === 'commentary';
    this.formular = fb.group({
      // Wie beim Anlegen: eine Behauptung in einem Satz, 3 bis 120 Zeichen (Titelregel).
      title: [daten.titel ?? '', [Validators.required, Validators.minLength(3), Validators.maxLength(TITEL_MAX)]],
      text: [daten.text ?? '', [Validators.required, Validators.minLength(TEXT_MIN), Validators.maxLength(this.textMax)]],
      // Leer, wenn der Kommentar die Fassung nicht hat; ausserhalb des Kommentars nicht angezeigt.
      kurz: [daten.extra?.kurz ?? '', [Validators.maxLength(KURZFASSUNG_MAX)]],
      lang: [daten.extra?.lang ?? '', [Validators.maxLength(LANGFASSUNG_MAX)]],
      // Herkuenfte, die sich nicht laden liessen, haben keine Adresse und lassen sich nicht anzeigen.
      references: [daten.quellen.filter((q) => !!q.url).map(alsEingabe)],
    });
  }

  speichern(): void {
    // Noch nicht bestaetigte Herkunft oder offene Notiz uebernehmen, bevor der
    // Formularwert gelesen wird - wie beim Anlegen, sonst gehen sie stumm verloren.
    this.referenceInput?.flushPendingInput();
    if (this.formular.invalid || this.speichertGerade()) {
      return;
    }
    this.speichertGerade.set(true);
    this.fehler.set(null);
    const { title, text, kurz, lang, references } = this.formular.getRawValue();
    const aenderung: BeitragAenderung = { title: title.trim(), text: text.trim(), references };
    if (this.hatFassungen) {
      // Immer beide mitschicken: leer entfernt die Fassung, wie beim Anlegen.
      aenderung.short_text = kurz.trim();
      aenderung.long_text = lang.trim();
    }
    this.beitraege
      .beitragAendern(this.daten.id, aenderung)
      .pipe(finalize(() => this.speichertGerade.set(false)))
      .subscribe({
        next: () => this.dialogRef.close(true),
        error: (fehler) => this.fehler.set(aendernFehlertext(fehler)),
      });
  }
}
