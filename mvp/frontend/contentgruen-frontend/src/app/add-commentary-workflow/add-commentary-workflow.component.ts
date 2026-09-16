import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
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
  ROHINPUT_PARAM,
  Vorbefuellung,
} from '../destillieren/destillier-uebergabe.service';

/** Hinweis im Formular, wenn ?aussage= auf nichts (mehr) zeigt. */
export const AUSSAGE_NICHT_VERFUEGBAR =
  'Die Aussage ist nicht mehr verfügbar — du kannst eine andere eintragen oder ohne speichern.';

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
  private destroyRef = inject(DestroyRef);
  statementId: string = '';
  statementText: string = '';
  isLoadingStatement: boolean = false;
  /** Gesetzt, wenn die Aussage aus der Adresse nicht ladbar war; das Formular bleibt nutzbar. */
  aussageHinweis: string | null = null;
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
    // Worauf der Beitrag antwortet und aus welchem Einwurf er entsteht, steht in
    // der Adresse. Reaktiv statt ueber den Snapshot: Aendern sich die Parameter,
    // waehrend die Seite offen ist, zieht das Formular nach. Beim Oeffnen wird
    // keine Aussage angelegt.
    this.route.queryParamMap
      .pipe(
        switchMap((params) => {
          this.einwurfUebernehmen(params.get(ROHINPUT_PARAM));
          return this.aussageLaden(params);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((aussage) => {
        this.statementId = aussage.statement_id;
        this.statementText = aussage.statement_text;
        this.isLoadingStatement = false;
      });
  }

  /**
   * Die Aussage aus ?aussage= oder ?searchQuery=. Ist sie nicht ladbar (geloescht,
   * keine gueltige ID, Netz), bleibt das Formular nutzbar: leeres Feld und ein
   * Hinweis, statt eines Fehlers, an dem es nur "Erneut versuchen" gaebe.
   */
  private aussageLaden(params: ParamMap) {
    this.isLoadingStatement = true;
    this.aussageHinweis = null;
    return this.statementService.aussageAusAdresse(params).pipe(
      catchError((error) => {
        this.logger.warn('Aussage aus der Adresse nicht ladbar', error);
        this.aussageHinweis = AUSSAGE_NICHT_VERFUEGBAR;
        return of({ statement_id: '', statement_text: '' });
      }),
    );
  }

  private einwurfUebernehmen(rohinputId: string | null): void {
    if (rohinputId === this.rohinputId) {
      return;
    }
    this.rohinputId = rohinputId;
    this.vorbefuellung = null;
    if (rohinputId) {
      this.uebergabe.vorbefuellungLaden(rohinputId).subscribe({
        next: (vorbefuellung) => (this.vorbefuellung = vorbefuellung),
        error: (error) => this.logger.error('Einwurf fuer die Vorbefuellung nicht ladbar', error),
      });
    }
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
}
