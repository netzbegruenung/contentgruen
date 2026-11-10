import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { catchError, distinctUntilChanged, switchMap } from 'rxjs/operators';
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
 * deren Beitraege schon als Treffer dastehen, fallen weg. Ohne Treffer sagt jede,
 * wie viele Antworten sie hat, und bietet "Antworten" fuer sich an - vor
 * dem Knopf fuer die eigene Formulierung, damit keine doppelte Aussage entsteht (#617).
 *
 * Auch fuer Besucher (#642): eigener oeffentlicher Endpunkt /statement/aehnliche,
 * dieselbe Auswahl wie fuer Angemeldete. Ist nichts ladbar, bleibt nur der Weg zum
 * Neu-Anlegen, den die Ergebnisseite als Inhalt hineinreicht.
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
   * Die Suche hat keine Treffer. Dann steht der Titel nur ueber einer Liste (sonst
   * folgte auf "noch nichts drin" eine Frage ohne Auswahl, etwa fuer Besucher), er
   * lautet "Meintest du …?", und jede aehnliche Aussage nennt ihre Antworten und
   * bietet "Antworten" fuer sich an (#617).
   */
  @Input() ohneTreffer = false;

  /**
   * Wie viele aehnliche Aussagen dastehen, nach jedem Laden und jeder Aenderung der
   * bekannten Aussagen; die Ergebnisseite zeigt "Nicht gemeint?" nur mit welchen (#642).
   */
  @Output() aehnlicheAnzahl = new EventEmitter<number>();

  readonly kommentarPfad = FORMULAR_PFAD.commentary;
  readonly titelId = `nicht-dabei-titel-${++naechsteNummer}`;
  readonly listenId = `aehnliche-titel-${naechsteNummer}`;

  private geladen: StatementSearchResult[] = [];
  private readonly suchtext$ = new BehaviorSubject<string>('');

  constructor(
    private statementService: StatementService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  ngOnInit(): void {
    this.suchtext$
      .pipe(
        distinctUntilChanged(),
        switchMap((text) =>
          text.length < AUSSAGE_MIN_ZEICHEN
            ? of([] as StatementSearchResult[])
            : this.statementService.aehnlicheAussagen(text).pipe(
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
        this.aehnlicheAnzahl.emit(this.aehnliche.length);
        this.cdr.markForCheck();
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['suchtext']) {
      this.suchtext$.next((this.suchtext ?? '').trim());
    }
    if (changes['bekannteAussagen'] && !changes['bekannteAussagen'].firstChange) {
      this.aehnlicheAnzahl.emit(this.aehnliche.length);
    }
  }

  /** Die aehnlichen Aussagen ohne die, die schon als Treffer dastehen. */
  get aehnliche(): StatementSearchResult[] {
    return this.geladen.filter((aussage) => !this.bekannteAussagen.includes(aussage.id));
  }

  get titelZeigen(): boolean {
    return !this.ohneTreffer || this.aehnliche.length > 0;
  }

  /**
   * Ohne Treffer fragt "Nicht dabei?" nach etwas, das gar nicht dasteht; dann
   * "Meintest du …?" ueber den aehnlichen Aussagen (#617).
   */
  get titel(): string {
    return this.ohneTreffer ? 'Meintest du …?' : 'Nicht dabei?';
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
