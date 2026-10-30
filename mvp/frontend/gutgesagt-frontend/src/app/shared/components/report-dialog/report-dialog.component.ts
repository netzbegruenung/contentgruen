import { Component, ElementRef, Inject, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { ModerationService } from '../../../services/moderation.service';
import { MELDEGRUENDE, MeldegrundWert, brauchtBegruendung } from '../../meldegruende';
import { istEmailAdresse } from '../../email-adresse';

export interface ReportDialogData {
  contentId: string;
  contentType: string;
}

// Grenzen wie im Suchdienst (api/v1/moderation.py: MELDER_NAME_MAX, MELDER_EMAIL_MAX).
export const MELDER_NAME_MAX = 200;
export const MELDER_EMAIL_MAX = 254;


/**
 * Der Meldedialog. Der DSA gilt fuer Gut gesagt (#438).
 * Deshalb fragt er die Angaben nach Art. 16 Abs. 2 DSA ab: Name und E-Mail-Adresse
 * freiwillig, die Erklaerung guten Glaubens als Pflicht. Eine Eingangsbestaetigung
 * per Mail gibt es nicht (kein Mailversand); bestaetigt wird der Eingang hier.
 */
@Component({
  selector: 'app-report-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatIconModule
  ],
  templateUrl: './report-dialog.component.html',
  styleUrls: ['./report-dialog.component.css']
})
export class ReportDialogComponent {
  selectedReason: MeldegrundWert = 'spam';
  description: string = '';
  melderName = '';
  melderEmail = '';
  guterGlaube = false;
  submitting = false;
  submitted = false;
  /** Ob die abgeschickte Meldung eine E-Mail-Adresse trug: davon haengt die Bestaetigung ab. */
  mitEmail = false;
  /** Erst nach dem Verlassen des Feldes zeigt der Dialog, dass die Adresse nicht stimmt. */
  emailVerlassen = false;
  error: string | null = null;

  @ViewChild('bestaetigung') set bestaetigung(element: ElementRef<HTMLElement> | undefined) {
    // Das Formular samt fokussiertem „Melden“ verschwindet; der Fokus geht auf die
    // Eingangsbestaetigung, damit ein Screenreader sie vorliest.
    element?.nativeElement.focus();
  }

  readonly reasons = MELDEGRUENDE;
  readonly nameMax = MELDER_NAME_MAX;
  readonly emailMax = MELDER_EMAIL_MAX;

  constructor(
    public dialogRef: MatDialogRef<ReportDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ReportDialogData,
    private moderationService: ModerationService
  ) {}

  get emailUngueltig(): boolean {
    const email = this.melderEmail.trim();
    return email !== '' && !istEmailAdresse(email);
  }

  get emailFehlerZeigen(): boolean {
    return this.emailVerlassen && this.emailUngueltig;
  }

  get begruendungPflicht(): boolean {
    return brauchtBegruendung(this.selectedReason);
  }

  get kannMelden(): boolean {
    return (
      !this.submitting &&
      !!this.selectedReason &&
      this.guterGlaube &&
      !this.emailUngueltig &&
      (!this.begruendungPflicht || this.description.trim() !== '')
    );
  }

  submitReport() {
    if (!this.kannMelden) {
      return;
    }
    this.submitting = true;
    this.error = null;
    const melderEmail = this.melderEmail.trim() || null;

    this.moderationService.reportContent({
      contentId: this.data.contentId,
      contentType: this.data.contentType,
      reason: this.selectedReason,
      description: this.description || undefined,
      melderName: this.melderName.trim() || null,
      melderEmail,
      guterGlaube: true,
    }).subscribe({
      next: () => {
        this.submitting = false;
        this.submitted = true;
        this.mitEmail = melderEmail !== null;
      },
      error: (error) => {
        this.submitting = false;

        if (error.status === 429) {
          this.error = 'Zu viele Meldungen. Bitte warte einige Minuten, bevor du erneut meldest.';
        } else if (error.status === 422) {
          this.error = 'Bitte prüfe deine Angaben, etwa die E-Mail-Adresse.';
        } else {
          this.error = 'Fehler beim Senden der Meldung. Bitte versuche es erneut.';
        }

        // Nur der Status: Der Fehlertext des Suchdienstes kann die eingegebene Adresse enthalten.
        console.error('Error reporting content:', error.status);
      }
    });
  }

  close(gemeldet: boolean) {
    this.dialogRef.close(gemeldet);
  }
}
