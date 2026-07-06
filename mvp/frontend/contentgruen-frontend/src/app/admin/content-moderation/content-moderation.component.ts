import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { ModerationService, ContentReport } from '../../services/moderation.service';

@Component({
  selector: 'app-content-moderation',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatButtonToggleModule,
    MatBadgeModule
  ],
  templateUrl: './content-moderation.component.html',
  styleUrls: ['./content-moderation.component.css'],
  animations: [
    trigger('expandCollapse', [
      state('collapsed', style({
        height: '0',
        overflow: 'hidden',
        opacity: 0,
        padding: '0'
      })),
      state('expanded', style({
        height: '*',
        overflow: 'visible',
        opacity: 1,
        padding: '16px'
      })),
      transition('collapsed <=> expanded', animate('300ms ease-in-out'))
    ])
  ]
})
export class ContentModerationComponent implements OnInit {
  reports: ContentReport[] = [];
  loading = true;
  error: string | null = null;
  selectedStatus: 'pending' | 'reviewed' | 'dismissed' | 'all' = 'pending';
  displayedColumns: string[] = ['expand', 'content_type', 'reason', 'reporter', 'created', 'actions'];
  expandedReports = new Set<string>();

  constructor(
    private moderationService: ModerationService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadReports();
  }

  loadReports() {
    this.loading = true;
    this.error = null;
    this.expandedReports.clear(); // Reset expanded rows on refresh

    this.moderationService.getReports(this.selectedStatus).subscribe({
      next: (response) => {
        // Force new array reference for change detection
        this.reports = [...response.reports];
        this.loading = false;
        this.updateDisplayedColumns();
      },
      error: (error) => {
        console.error('Error loading reports:', error);
        this.error = 'Fehler beim Laden der Meldungen';
        this.loading = false;
      }
    });
  }

  onStatusFilterChange(status: 'pending' | 'reviewed' | 'dismissed' | 'all') {
    this.selectedStatus = status;
    this.loadReports();
  }

  updateDisplayedColumns() {
    // Base columns
    const baseColumns = ['expand', 'content_type', 'reason', 'reporter', 'created'];

    // Add status column for non-pending views
    if (this.selectedStatus !== 'pending') {
      baseColumns.push('status');
    }

    // Add reviewed_by column for reviewed/dismissed/all views
    if (this.selectedStatus === 'reviewed' || this.selectedStatus === 'dismissed' || this.selectedStatus === 'all') {
      baseColumns.push('reviewed_by');
    }

    // Add actions column only for pending reports
    if (this.selectedStatus === 'pending') {
      baseColumns.push('actions');
    }

    this.displayedColumns = baseColumns;
  }

  deleteContent(report: ContentReport) {
    if (!confirm(`Möchten Sie diesen Inhalt wirklich löschen?\n\nInhalt-ID: ${report.content_id}\nTyp: ${report.content_type}\n\nDieser Vorgang kann nicht rückgängig gemacht werden.`)) {
      return;
    }

    this.moderationService.deleteContent(report.content_type, report.content_id).subscribe({
      next: (response) => {
        this.snackBar.open('Inhalt erfolgreich gelöscht', 'OK', { duration: 3000 });
        this.loadReports(); // Reload to remove from list
      },
      error: (error) => {
        this.snackBar.open('Fehler beim Löschen des Inhalts', 'OK', { duration: 3000 });
        console.error('Error deleting content:', error);
      }
    });
  }

  dismissReport(report: ContentReport) {
    this.moderationService.dismissReport(report.id, 'Dismissed by admin').subscribe({
      next: (response) => {
        this.snackBar.open('Meldung verworfen', 'OK', { duration: 3000 });
        this.loadReports(); // Reload to remove from list
      },
      error: (error) => {
        this.snackBar.open('Fehler beim Verwerfen der Meldung', 'OK', { duration: 3000 });
        console.error('Error dismissing report:', error);
      }
    });
  }

  getReasonLabel(reason: string): string {
    const labels: { [key: string]: string } = {
      'spam': 'Spam',
      'inappropriate': 'Unangemessen',
      'duplicate': 'Duplikat',
      'other': 'Andere'
    };
    return labels[reason] || reason;
  }

  getContentTypeLabel(type: string): string {
    const labels: { [key: string]: string } = {
      'commentary': 'Kommentar',
      'generictext': 'Generic Text',
      'statement': 'Statement'
    };
    return labels[type] || type;
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  toggleExpand(report: ContentReport): void {
    const reportId = report.id;
    if (this.expandedReports.has(reportId)) {
      this.expandedReports.delete(reportId);
    } else {
      this.expandedReports.add(reportId);
    }
  }

  isExpanded(report: ContentReport): boolean {
    return this.expandedReports.has(report.id);
  }

  getStatusLabel(status: string): string {
    const labels: { [key: string]: string } = {
      'pending': 'Ausstehend',
      'reviewed': 'Geprüft',
      'dismissed': 'Abgelehnt'
    };
    return labels[status] || status;
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'pending': 'warn',
      'reviewed': 'accent',
      'dismissed': 'primary'
    };
    return colors[status] || '';
  }
}
