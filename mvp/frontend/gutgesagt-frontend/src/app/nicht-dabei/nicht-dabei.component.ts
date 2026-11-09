import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BehaviorSubject, combineLatest, of } from 'rxjs';
import { catchError, distinctUntilChanged, map, switchMap } from 'rxjs/operators';
import { AuthService } from '../auth/auth.service';
import { AUSSAGE_MIN_ZEICHEN, StatementService } from '../services/statement.service';
import { StatementSearchResult } from '../services/dtos/statementDtos';
import { LoggingService } from '../services/logging.service';
import { FORMULAR_PFAD, SUCHTEXT_PARAM, aussageParameter } from '../shared/formular-adresse';

/** Fortlaufende Nummer fuer eindeutige IDs je Instanz (aria-labelledby). */
let naechsteNummer = 0;

/**
 * "Nicht dabei?" auf der Ergebnisseite, ohne Treffer und unter den Treffern: Die
 * Suche soll nie in einer Sackgasse enden (#362, docs/VISION.md "Lieber keine
 * Antwort als eine falsche").
 *
 * Zeigt bis zu drei aehnliche Aussagen, markiert "passt vielleicht" - dieselbe
 * Auswahl wie die Vorschlaege im Feld "Antwort auf" (gepflegte Aussagen ab der
 * unteren Grenze, ohne Widerspruch). Ein Klick sucht nach der Aussage. Aussagen,
 * deren Beitraege schon als Treffer dastehen, fallen weg. Jede sagt, wie viele
 * Antworten sie hat, und bietet "Selbst beantworten" fuer sich an - vor dem Knopf
 * fuer die eigene Formulierung, damit keine doppelte Aussage entsteht (#617).
 *
 * Nur fuer Angemeldete: Der Endpunkt der Aussagen ist nicht anonym erreichbar, ein
 * 401 fuehrte Besucher auf /login. Ohne Anmeldung oder wenn nichts ladbar ist,
 * bleibt nur der Weg zum Neu-Anlegen, den die Ergebnisseite als Inhalt hineinreicht.
 */
@Component({
  selector: 'app-nicht-dabei',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink],
  templateUrl: './nicht-dabei.component.html',
  styleUrls: ['./nicht-dabei.component.css'],
})
export class NichtDabeiComponent implements OnInit, OnChanges {
  /** Der Suchtext; nach ihm werden aehnliche Aussagen gesucht. */
  @Input() suchtext = '';

  /** IDs der Aussagen, deren Beitraege schon als Treffer angezeigt werden. */
  @Input() bekannteAussagen: readonly string[] = [];

  /**
   * Ohne Treffer steht "Nicht dabei?" nur ueber einer Liste: Sonst folgte auf
   * "noch nichts drin" eine Frage ohne Auswahl (etwa fuer Besucher).
   */
  @Input() titelNurMitListe = false;

  readonly kommentarPfad = FORMULAR_PFAD.commentary;
  readonly titelId = `nicht-dabei-titel-${++naechsteNummer}`;
  readonly listenId = `aehnliche-titel-${naechsteNummer}`;

  private geladen: StatementSearchResult[] = [];
  private readonly suchtext$ = new BehaviorSubject<string>('');

  constructor(
    private statementService: StatementService,
    private authService: AuthService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    const angemeldet$ = this.authService.userInfo$.pipe(
      map((info) => !!info?.isAuthenticated),
      distinctUntilChanged(),
    );
    combineLatest([this.suchtext$.pipe(distinctUntilChanged()), angemeldet$])
      .pipe(
        switchMap(([text, angemeldet]) =>
          !angemeldet || text.length < AUSSAGE_MIN_ZEICHEN
            ? of([] as StatementSearchResult[])
            : this.statementService.aussageVorschlaege(text).pipe(
                catchError((error) => {
                  // Ohne aehnliche Aussagen bleibt das Neu-Anlegen.
                  this.logger.warn('Aehnliche Aussagen nicht ladbar', error);
                  return of([] as StatementSearchResult[]);
                }),
              ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((aussagen) => {
        this.geladen = aussagen;
        this.cdr.markForCheck();
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['suchtext']) {
      this.suchtext$.next((this.suchtext ?? '').trim());
    }
  }

  /** Die aehnlichen Aussagen ohne die, die schon als Treffer dastehen. */
  get aehnliche(): StatementSearchResult[] {
    return this.geladen.filter((aussage) => !this.bekannteAussagen.includes(aussage.id));
  }

  get titelZeigen(): boolean {
    return !this.titelNurMitListe || this.aehnliche.length > 0;
  }

  /**
   * Ohne Treffer fragt "Nicht dabei?" nach etwas, das gar nicht dasteht; dann
   * "Meintest du …?" ueber den aehnlichen Aussagen (#617).
   */
  get titel(): string {
    return this.titelNurMitListe ? 'Meintest du …?' : 'Nicht dabei?';
  }

  antwortenText(anzahl: number): string {
    return anzahl === 1 ? '1 Antwort' : `${anzahl} Antworten`;
  }

  /** Query-Parameter, um im Kommentarformular auf diese Aussage zu antworten. */
  antwortAuf(aussage: StatementSearchResult): Record<string, string> {
    return aussageParameter(aussage.id, aussage.text);
  }

  /** Query-Parameter, um nach einer Aussage zu suchen. */
  sucheNach(aussage: StatementSearchResult): Record<string, string> {
    return { [SUCHTEXT_PARAM]: aussage.text };
  }
}
