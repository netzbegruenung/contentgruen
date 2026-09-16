import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
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
    // Worauf der Beitrag antwortet, steht in der Adresse (?aussage= oder
    // ?searchQuery=). Beim Oeffnen wird dafuer keine Aussage angelegt.
    this.aussageLaden();

    this.rohinputId = this.uebergabe.rohinputId(this.route);
    if (this.rohinputId) {
      this.uebergabe.vorbefuellungLaden(this.rohinputId).subscribe({
        next: (vorbefuellung) => (this.vorbefuellung = vorbefuellung),
        error: (error) => this.logger.error('Einwurf fuer die Vorbefuellung nicht ladbar', error),
      });
    }
  }

  aussageLaden(): void {
    const params = this.route.snapshot?.queryParamMap ?? convertToParamMap({});
    this.isLoadingStatement = true;
    this.statementError = null;

    this.statementService.aussageAusAdresse(params).subscribe({
      next: (aussage) => {
        this.statementId = aussage.statement_id;
        this.statementText = aussage.statement_text;
        this.isLoadingStatement = false;
      },
      error: (error) => {
        this.logger.error('Aussage aus der Adresse nicht ladbar', error);
        this.statementError = 'Die Aussage, auf die du antworten willst, konnte nicht geladen werden.';
        this.isLoadingStatement = false;
      }
    });
  }

  onSuccess(responseId: string) {
    // Trigger refresh of recent content
    this.contentRefreshService.triggerRefresh();

    // Aus dem Destillier-Ablauf: Einwurf verknuepfen und den naechsten oeffnen.
    if (this.rohinputId) {
      this.uebergabe.nachSpeichern(this.rohinputId, responseId, 'commentary');
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
