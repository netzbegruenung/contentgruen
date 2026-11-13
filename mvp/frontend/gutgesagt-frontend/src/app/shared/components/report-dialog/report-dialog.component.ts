import { Component, DestroyRef, ElementRef, Inject, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
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
import { AuthService } from '../../../auth/auth.service';

interface FehlendeAngabe {
  text: string;
  /** Endet mit einem Nebensatz, den vor „und“ ein Komma schliesst. */
  endetMitNebensatz?: boolean;
}

export interface ReportDialogData {
  contentId: string;
  contentType: string;
}

/**
 * Ob das Haekchen „Bestaetigung und Entscheidung per Mail an mein Konto“ vorausgewaehlt
 * ist. Vorerst nein (Datenschutz durch Voreinstellung, Art. 25 Abs. 2 DSGVO), bis der
 * Maintainer entschieden hat; umstellen nur hier.
 */
export const MELDEN_AN_KONTO_VORAUSGEWAEHLT = false;

// Grenzen wie im Suchdienst (api/v1/moderation.py: MELDER_NAME_MAX, MELDER_EMAIL_MAX).
export const MELDER_NAME_MAX = 200;
export const MELDER_EMAIL_MAX = 254;


/**
 * Der Meldedialog. Der DSA gilt fuer Gut gesagt (#438).
 * Deshalb fragt er die Angaben nach Art. 16 Abs. 2 DSA ab: Name und E-Mail-Adresse
 * freiwillig, die Erklaerung guten Glaubens als Pflicht. Angemeldete fragt er weder
 * nach Name noch nach Adresse (UX-Review B17, Entscheidung Maintainer 13.11.2026): Die
 * Meldung haengt an ihrem Konto (``reported_by_user_id``), und ein vorausgewaehltes
 * Haekchen laesst den Suchdienst Bestaetigung und Entscheidung an die Adresse des
 * Kontos schicken. Die Adresse kommt dort aus dem Konto (BFF), nie aus dem Dialog. Bestaetigt wird der Eingang
 * hier; mit E-Mail-Adresse schickt der Suchdienst die Bestaetigung und spaeter die
 * Entscheidung auch per Mail (#493, services/meldung_mitteilen.py).
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
  /** Nicht vorbelegt (#581): Den Meldegrund waehlt die Person selbst. */
  selectedReason: MeldegrundWert | null = null;
  description: string = '';
  melderName = '';
  melderEmail = '';
  guterGlaube = false;
  submitting = false;
  submitted = false;
  /** Ob die abgeschickte Meldung eine E-Mail-Adresse trug: davon haengt die Bestaetigung ab. */
  mitEmail = false;
  /** Doppelmeldung: Die Person hat diesen Beitrag schon gemeldet, nichts Neues angelegt. */
  schonGemeldet = false;
  /** Angemeldet mit Haekchen, aber der Suchdienst hat keine Adresse (etwa keine bestaetigte im Konto). */
  kontoOhneMail = false;
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
  /**
   * Angemeldet: kein Namens- und kein Adressfeld, die Meldung haengt am Konto. Folgt der
   * Anmeldung, auch wenn sie erst nach dem Oeffnen feststeht (Review zu #670).
   */
  angemeldet = false;
  /** Angemeldet: Bestaetigung und Entscheidung per Mail an das Konto. */
  bestaetigungAnKonto = MELDEN_AN_KONTO_VORAUSGEWAEHLT;

  constructor(
    public dialogRef: MatDialogRef<ReportDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ReportDialogData,
    private moderationService: ModerationService,
    authService: AuthService,
  ) {
    authService.userInfo$
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe((info) => (this.angemeldet = !!info?.isAuthenticated));
  }

  get emailUngueltig(): boolean {
    const email = this.melderEmail.trim();
    return email !== '' && !istEmailAdresse(email);
  }

  get emailFehlerZeigen(): boolean {
    return this.emailVerlassen && this.emailUngueltig;
  }

  get begruendungPflicht(): boolean {
    return this.selectedReason !== null && brauchtBegruendung(this.selectedReason);
  }

  /**
   * Was zum Melden noch fehlt, in der Reihenfolge der Felder. Der Dialog nennt es
   * neben dem ausgegrauten „Melden“ (#581), weil Checkbox und Felder auf kleinen
   * Bildschirmen unter dem Falz liegen. Fuer den Hinweis zaehlt die E-Mail-Adresse
   * erst nach dem Verlassen des Feldes, wie ihre Fehlermeldung; fuer den Knopf sofort.
   */
  private fehlendeAngaben(fuerHinweis: boolean): FehlendeAngabe[] {
    const fehlt: FehlendeAngabe[] = [];
    if (this.selectedReason === null) {
      fehlt.push({ text: 'ein Grund' });
    }
    if (this.begruendungPflicht && this.description.trim() === '') {
      fehlt.push({ text: 'die Begründung, warum der Beitrag rechtswidrig ist', endetMitNebensatz: true });
    }
    if (!this.angemeldet && (fuerHinweis ? this.emailFehlerZeigen : this.emailUngueltig)) {
      fehlt.push({ text: 'eine gültige E-Mail-Adresse (oder das Feld leer lassen)' });
    }
    if (!this.guterGlaube) {
      fehlt.push({ text: 'deine Erklärung guten Glaubens' });
    }
    return fehlt;
  }

  /** Der Hinweis neben „Melden“; leer, wenn nichts fehlt oder gerade gesendet wird. */
  get fehltHinweis(): string {
    const fehlt = this.submitting ? [] : this.fehlendeAngaben(true);
    if (fehlt.length === 0) {
      return '';
    }
    if (fehlt.length === 1) {
      return `Zum Melden fehlt noch: ${fehlt[0].text}.`;
    }
    const davor = fehlt.slice(0, -1);
    // Ein Nebensatz („…, warum … ist“) vor „und“ wird mit einem Komma geschlossen.
    const komma = davor[davor.length - 1].endetMitNebensatz ? ',' : '';
    const liste = `${davor.map((a) => a.text).join(', ')}${komma} und ${fehlt[fehlt.length - 1].text}`;
    return `Zum Melden fehlen noch: ${liste}.`;
  }

  get kannMelden(): boolean {
    return !this.submitting && this.fehlendeAngaben(false).length === 0;
  }

  submitReport() {
    const grund = this.selectedReason;
    if (!this.kannMelden || grund === null) {
      return;
    }
    this.submitting = true;
    this.error = null;
    const melderEmail = this.angemeldet ? null : this.melderEmail.trim() || null;
    const anKonto = this.angemeldet && this.bestaetigungAnKonto;

    this.moderationService.reportContent({
      contentId: this.data.contentId,
      contentType: this.data.contentType,
      reason: grund,
      description: this.description || undefined,
      melderName: this.angemeldet ? null : this.melderName.trim() || null,
      melderEmail,
      guterGlaube: true,
      ...(anKonto ? { bestaetigungAnKonto: true } : {}),
    }).subscribe({
      next: (antwort) => {
        this.submitting = false;
        this.submitted = true;
        // Die Zusage einer Mail richtet sich nach dem, was der Suchdienst gespeichert hat:
        // Fuer Angemeldete kann die Adresse fehlen (Sitzung abgelaufen, keine im Konto).
        this.mitEmail = antwort?.mit_email ?? (melderEmail !== null || anKonto);
        this.schonGemeldet = antwort?.schon_gemeldet === true;
        this.kontoOhneMail = anKonto && !this.mitEmail && !this.schonGemeldet;
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

/**
 * Oeffnet den Melde-Dialog: 500 px breit, auf dem Handy hoechstens 95 % der
 * Fensterbreite wie Feedback und Profilbild (#512).
 */
export function meldeDialogOeffnen(
  dialog: MatDialog,
  data: ReportDialogData,
): MatDialogRef<ReportDialogComponent> {
  return dialog.open(ReportDialogComponent, { width: '500px', maxWidth: '95vw', data });
}
