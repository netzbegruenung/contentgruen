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
import { AddGenerictextComponent } from '../add-generictext/add-generictext.component';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { StatementService } from '../services/statement.service';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import { AUSSAGE_PARAM, SUCHTEXT_PARAM, gespeichertPfad } from '../shared/formular-adresse';
import { NACH_DEM_AUSFORMULIEREN } from '../raw-input-list/fangkorb-filter';
import { StateManagementService } from '../services/state-management.service';
import {
  BeitragGespeichert,
  GespeichertZustand,
  SUCHE_PARAM,
  VON_PARAM,
} from '../beitragsformular/beitrag-gespeichert/gespeichert-adresse';
import {
  DestillierUebergabeService,
  Vorbefuellung,
} from '../destillieren/destillier-uebergabe.service';
import { EINWURF_PARAM } from '../destillieren/einwurf-adresse';

/** Hinweis im Formular, wenn ?aussage= auf nichts (mehr) zeigt. */
export const AUSSAGE_NICHT_VERFUEGBAR =
  'Die Aussage ist nicht mehr verfügbar — du kannst eine andere eintragen oder ohne speichern.';

/** Die vorhandene Hintergrundinfo aus dem Fangkorb gewaehlt: gespeichert wurde nichts, verknuepft schon. */
export const EINWURF_MIT_VORHANDENER_VERKNUEPFT = 'Der Einwurf ist jetzt mit der vorhandenen Hintergrundinfo verknüpft.';

export const EINWURF_NICHT_VERKNUEPFT =
  'Der Einwurf ließ sich nicht mit der vorhandenen Hintergrundinfo verknüpfen und ist noch nicht ausformuliert.';

export const ERNEUT_VERKNUEPFEN = 'Erneut versuchen';

@Component({
  standalone: true,
  selector: 'app-add-generictext-workflow',
  templateUrl: './add-generictext-workflow.component.html',
  styleUrls: ['./add-generictext-workflow.component.css'],
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatButtonModule,
    ...SHARED_IMPORTS,
    AddGenerictextComponent
  ]
})
export class AddGenerictextWorkflowComponent implements OnInit {
  private destroyRef = inject(DestroyRef);
  statementId: string = '';
  statementText: string = '';
  isLoadingStatement: boolean = false;
  /** Gesetzt, wenn die Aussage aus der Adresse nicht ladbar war; das Formular bleibt nutzbar. */
  aussageHinweis: string | null = null;
  /** Gesetzt, wenn das Formular aus dem Destillier-Ablauf geoeffnet wurde. */
  einwurfId: string | null = null;
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
    private snackBar: MatSnackBar,
  ) { }

  ngOnInit(): void {
    // Worauf der Beitrag antwortet und aus welchem Einwurf er entsteht, steht in
    // der Adresse. Reaktiv statt ueber den Snapshot: Aendern sich die Parameter,
    // waehrend die Seite offen ist, zieht das Formular nach. Beim Oeffnen wird
    // keine Aussage angelegt.
    this.route.queryParamMap
      .pipe(
        switchMap((params) => {
          this.einwurfUebernehmen(params.get(EINWURF_PARAM));
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

  private einwurfUebernehmen(einwurfId: string | null): void {
    if (einwurfId === this.einwurfId) {
      return;
    }
    this.einwurfId = einwurfId;
    this.vorbefuellung = null;
    if (einwurfId) {
      this.uebergabe.vorbefuellungLaden(einwurfId).subscribe({
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
      ...(ergebnis.themenHinweis ? { themenHinweis: ergebnis.themenHinweis } : {}),
    };

    if (this.einwurfId) {
      const einwurfId = this.einwurfId;
      this.uebergabe.mitBeitragVerknuepfen(einwurfId, ergebnis.id, 'generic_text').subscribe((einwurfVerknuepft) =>
        this.zurErgebnisseite(ergebnis.id, { [EINWURF_PARAM]: einwurfId }, { ...zustand, einwurfVerknuepft }),
      );
      return;
    }

    const queryParams = this.ausSuche
      ? { [VON_PARAM]: 'suche', ...(this.ausSuche.anfrage ? { [SUCHE_PARAM]: this.ausSuche.anfrage } : {}) }
      : {};
    this.zurErgebnisseite(ergebnis.id, queryParams, zustand);
  }

  /**
   * Die vorhandene Hintergrundinfo gewaehlt (zugestimmt oder die eigene genommen)
   * statt zu speichern. Aus dem Fangkorb wird der Einwurf dann mit ihr verknuepft -
   * er ist damit ausformuliert - und es geht zum naechsten Einwurf. Keine
   * Ergebnisseite: Gespeichert wurde nichts. Scheitert das Verknuepfen, laesst es
   * sich aus der Meldung wiederholen. Ohne Einwurf bleibt das Formular.
   */
  onVorhandenGewaehlt(hintergrundinfoId: string): void {
    const einwurfId = this.einwurfId;
    if (!einwurfId) {
      return;
    }
    this.uebergabe.mitBeitragVerknuepfen(einwurfId, hintergrundinfoId, 'generic_text').subscribe((einwurfVerknuepft) => {
      if (!einwurfVerknuepft) {
        this.snackBar
          .open(EINWURF_NICHT_VERKNUEPFT, ERNEUT_VERKNUEPFEN, { duration: 15000 })
          .onAction()
          .subscribe(() => this.onVorhandenGewaehlt(hintergrundinfoId));
        return;
      }
      this.snackBar.open(EINWURF_MIT_VORHANDENER_VERKNUEPFT, 'OK', { duration: 5000 });
      this.uebergabe.zumNaechsten(einwurfId, NACH_DEM_AUSFORMULIEREN);
    });
  }

  private zurErgebnisseite(id: string, queryParams: Record<string, string>, state: GespeichertZustand): void {
    this.router.navigate(gespeichertPfad('generictext', id), { queryParams, state, replaceUrl: true });
  }
}
