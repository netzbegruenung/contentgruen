import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FEEDBACK_AUFBEWAHRUNG_TAGE, FeedbackService } from './feedback.service';

// Grenzen wie im Backend (services/feedback_service.py).
export const FEEDBACK_TEXT_MAX = 2000;
export const FEEDBACK_KONTAKT_MAX = 200;

/**
 * Das kurze Formular hinter dem Knopf "Feedback" im Kopf: Freitext, optional ein
 * Kontakt. Ersetzt die Mail-Adresse am Ende der Ueber-Seite (#343).
 */
@Component({
  selector: 'app-feedback-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './feedback-dialog.component.html',
  styleUrls: ['./feedback-dialog.component.css'],
})
export class FeedbackDialogComponent {
  readonly textMax = FEEDBACK_TEXT_MAX;
  readonly kontaktMax = FEEDBACK_KONTAKT_MAX;
  readonly aufbewahrungTage = FEEDBACK_AUFBEWAHRUNG_TAGE;

  text = '';
  kontakt = '';
  sendet = false;
  gesendet = false;
  fehler: string | null = null;

  constructor(
    public dialogRef: MatDialogRef<FeedbackDialogComponent>,
    private feedbackService: FeedbackService
  ) {}

  get kannSenden(): boolean {
    return !this.sendet && this.text.trim().length > 0;
  }

  senden(): void {
    if (!this.kannSenden) {
      return;
    }
    this.sendet = true;
    this.fehler = null;
    this.feedbackService.senden(this.text.trim(), this.kontakt.trim() || null).subscribe({
      next: () => {
        this.sendet = false;
        this.gesendet = true;
      },
      error: (error) => {
        this.sendet = false;
        this.fehler =
          error?.status === 429
            ? 'Gerade kam sehr viel Feedback an. Bitte versuch es in ein paar Minuten noch einmal.'
            : 'Dein Feedback wurde nicht gesendet. Bitte versuch es noch einmal.';
      },
    });
  }

  schliessen(): void {
    this.dialogRef.close();
  }
}
