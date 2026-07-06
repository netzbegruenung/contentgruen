import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { ModerationService } from '../../../services/moderation.service';

export interface ReportDialogData {
  contentId: string;
  contentType: string;
}

@Component({
  selector: 'app-report-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
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
  selectedReason: string = 'spam';
  description: string = '';
  submitting = false;
  submitted = false;
  error: string | null = null;

  reasons = [
    { value: 'spam', label: 'Spam oder unerwünschte Werbung' },
    { value: 'inappropriate', label: 'Unangemessener Inhalt' },
    { value: 'duplicate', label: 'Duplikat' },
    { value: 'other', label: 'Andere' }
  ];

  constructor(
    public dialogRef: MatDialogRef<ReportDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ReportDialogData,
    private moderationService: ModerationService
  ) {}

  submitReport() {
    this.submitting = true;
    this.error = null;

    this.moderationService.reportContent(
      this.data.contentId,
      this.data.contentType,
      this.selectedReason,
      this.description || undefined
    ).subscribe({
      next: (response) => {
        this.submitting = false;
        this.submitted = true;
        setTimeout(() => this.dialogRef.close(true), 2000);
      },
      error: (error) => {
        this.submitting = false;

        // Handle rate limiting (HTTP 429)
        if (error.status === 429) {
          this.error = 'Zu viele Meldungen. Bitte warten Sie einige Minuten, bevor Sie erneut melden.';
        } else {
          this.error = 'Fehler beim Senden der Meldung. Bitte versuchen Sie es erneut.';
        }

        console.error('Error reporting content:', error);
      }
    });
  }

  cancel() {
    this.dialogRef.close(false);
  }
}
