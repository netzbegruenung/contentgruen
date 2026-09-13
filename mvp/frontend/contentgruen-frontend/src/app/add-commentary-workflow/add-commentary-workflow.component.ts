import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AddCommentaryComponent } from '../add-commentary/add-commentary.component';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import {
  DestillierUebergabeService,
  Vorbefuellung,
} from '../destillieren/destillier-uebergabe.service';

@Component({
  standalone: true,
  selector: 'app-add-commentary-workflow',
  templateUrl: './add-commentary-workflow.component.html',
  styleUrls: ['./add-commentary-workflow.component.css'],
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatButtonModule,
    ...SHARED_IMPORTS,
    AddCommentaryComponent
  ]
})
export class AddCommentaryWorkflowComponent implements OnInit {
  @Input() searchQuery: string = '';
  statementId: string = '';
  statementText: string = '';
  isLoadingStatement: boolean = false;
  statementError: string | null = null;
  /** Gesetzt, wenn das Formular aus dem Destillier-Ablauf geoeffnet wurde. */
  rohinputId: string | null = null;
  vorbefuellung: Vorbefuellung | null = null;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private statementService: StatementService,
    private logger: LoggingService,
    private contentRefreshService: ContentRefreshService,
    private snackBar: MatSnackBar,
    private uebergabe: DestillierUebergabeService
  ) { }

  ngOnInit(): void {
    // If we have a searchQuery, find or create the statement
    if (this.searchQuery && this.searchQuery.trim()) {
      this.findOrCreateStatement(this.searchQuery);
    }

    this.rohinputId = this.uebergabe.rohinputId(this.route);
    if (this.rohinputId) {
      this.uebergabe.vorbefuellungLaden(this.rohinputId).subscribe({
        next: (vorbefuellung) => (this.vorbefuellung = vorbefuellung),
        error: (error) => this.logger.error('Einwurf fuer die Vorbefuellung nicht ladbar', error),
      });
    }
  }

  findOrCreateStatement(text: string): void {
    this.isLoadingStatement = true;
    this.statementError = null;

    this.statementService.findOrCreateStatement(text, 'manually_created').subscribe({
      next: (response) => {
        this.statementId = response.statement_id;
        this.statementText = response.statement_text;
        this.isLoadingStatement = false;

        if (response.statement_was_new) {
          this.logger.info('Created new statement with ID:', response.statement_id);
        } else {
          this.logger.info('Using existing statement with ID:', response.statement_id);
        }
      },
      error: (error) => {
        this.logger.error('Error finding or creating statement', error);
        this.statementError = 'Fehler beim Erstellen des Statements. Bitte versuche es erneut.';
        this.isLoadingStatement = false;
        // Don't set a statementId if the operation fails
      }
    });
  }

  onSuccess(responseId: string) {
    // Trigger refresh of recent content
    this.contentRefreshService.triggerRefresh();

    // Aus dem Destillier-Ablauf: Einwurf verknuepfen und den naechsten oeffnen.
    if (this.rohinputId) {
      this.uebergabe.nachSpeichern(this.rohinputId, responseId);
      return;
    }

    // Show thank you message with snackbar
    const snackBarRef = this.snackBar.open(
      'Vielen Dank! Dein Beitrag hilft der gesamten Community. Du kannst deine Beiträge und deren Nutzung auf der "Meine Beiträge" Seite verfolgen.',
      'Meine Beiträge ansehen',
      {
        duration: 8000,
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
        panelClass: ['success-snackbar']
      }
    );

    // Navigate to contributions page when action button is clicked
    snackBarRef.onAction().subscribe(() => {
      this.router.navigate(['/contributions']);
    });

    // Navigate back to contribute page so users can add more content
    this.router.navigate(['/contribute']);
  }

  onCancel() {
    if (this.rohinputId) {
      this.uebergabe.zurueckZumEinwurf(this.rohinputId);
      return;
    }
    this.router.navigate(['/contribute']);
  }

  navigateBack(): void {
    this.router.navigate(['/contribute']);
  }
}
