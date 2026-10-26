import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ReportDialogComponent } from '../report-dialog/report-dialog.component';

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
      color: #666;
    }

    .report-button:hover {
      color: #d32f2f;
    }
  `]
})
export class ReportButtonComponent {
  @Input() contentId!: string;
  @Input() contentType!: string;

  constructor(private dialog: MatDialog) {}

  openReportDialog() {
    this.dialog.open(ReportDialogComponent, {
      width: '500px',
      data: {
        contentId: this.contentId,
        contentType: this.contentType
      }
    });
  }
}
