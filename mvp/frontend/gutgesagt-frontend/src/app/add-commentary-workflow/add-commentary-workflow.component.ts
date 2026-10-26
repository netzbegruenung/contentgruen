import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { AddCommentaryComponent } from '../add-commentary/add-commentary.component';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import { AUSSAGE_PARAM, SUCHTEXT_PARAM, gespeichertPfad } from '../shared/formular-adresse';
import { StateManagementService } from '../services/state-management.service';
import {
  BeitragGespeichert,
  GespeichertZustand,
  SUCHE_PARAM,
  VON_PARAM,
} from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
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
  /** Aus der Suche geoeffnet (?aussage= oder ?searchQuery=); dann mit der Anfrage, soweit bekannt. */
  private ausSuche: { anfrage: string | null } | null = null;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private statementService: StatementService,
    private logger: LoggingService,
    private contentRefreshService: ContentRefreshService,
    private uebergabe: DestillierUebergabeService,
    private stateService: StateManagementService,
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
          this.herkunftMerken(params);
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

  private herkunftMerken(params: ParamMap): void {
    if (!params.get(AUSSAGE_PARAM) && !params.get(SUCHTEXT_PARAM)) {
      this.ausSuche = null;
      return;
    }
    // Mit ?searchQuery= steht die Anfrage in der Adresse; mit ?aussage=<id> nur
    // im Zustand der Suche, solange die Sitzung laeuft.
    const anfrage = params.get(SUCHTEXT_PARAM)?.trim() || this.stateService.currentState.searchQuery?.trim() || null;
    this.ausSuche = { anfrage };
  }

  /**
   * Nach dem Speichern immer die Ergebnisseite - auch im Destillier-Ablauf; den
   * naechsten Einwurf waehlt man dort selbst. Sie ersetzt das Formular im
   * Verlauf: Zurueck fuehrt nicht in ein Formular, das eben gespeichert wurde.
   */
  onSuccess(ergebnis: BeitragGespeichert) {
    this.contentRefreshService.triggerRefresh();

    const zustand: GespeichertZustand = {
      aussage: ergebnis.aussage.text ? ergebnis.aussage : undefined,
      verknuepft: ergebnis.verknuepft,
    };

    if (this.rohinputId) {
      const rohinputId = this.rohinputId;
      this.uebergabe.alsVerarbeitetMarkieren(rohinputId, ergebnis.id, 'commentary').subscribe((markiert) =>
        this.zurErgebnisseite(ergebnis.id, { [ROHINPUT_PARAM]: rohinputId }, { ...zustand, markiert }),
      );
      return;
    }

    const queryParams = this.ausSuche
      ? { [VON_PARAM]: 'suche', ...(this.ausSuche.anfrage ? { [SUCHE_PARAM]: this.ausSuche.anfrage } : {}) }
      : {};
    this.zurErgebnisseite(ergebnis.id, queryParams, zustand);
  }

  private zurErgebnisseite(id: string, queryParams: Record<string, string>, state: GespeichertZustand): void {
    this.router.navigate(gespeichertPfad('commentary', id), { queryParams, state, replaceUrl: true });
  }
}
