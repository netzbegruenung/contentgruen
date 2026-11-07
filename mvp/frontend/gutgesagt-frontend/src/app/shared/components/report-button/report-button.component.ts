import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { meldeDialogOeffnen } from '../report-dialog/report-dialog.component';

@Component({
  selector: 'app-report-button',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <button
      mat-icon-button
      class="report-button"
      matTooltip="Inhalt melden"
      (click)="openReportDialog(); $event.stopPropagation()"
      aria-label="Inhalt melden">
      <mat-icon>flag</mat-icon>
    </button>
  `,
  styles: [`
    .report-button {
      color: var(--text-muted);
    }

    .report-button:hover {
      color: var(--error-main);
    }
  `]
})
export class ReportButtonComponent {
  @Input() contentId!: string;
  @Input() contentType!: string;

  constructor(private dialog: MatDialog) {}

  openReportDialog() {
    meldeDialogOeffnen(this.dialog, { contentId: this.contentId, contentType: this.contentType });
  }
}
