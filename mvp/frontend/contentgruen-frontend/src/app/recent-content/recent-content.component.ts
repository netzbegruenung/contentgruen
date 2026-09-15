import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BreakpointObserver } from '@angular/cdk/layout';
import { ContentService, RecentContentResponse } from '../services/content.service';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
import { LoadingSpinnerComponent } from '../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../shared/components/error-message/error-message.component';

/** So viele Beitraege zeigt der Teaser auf der Startseite. */
export const TEASER_ANZAHL = 5;

/** /recent liefert nur diese beiden Typen (api/v1/content.py). */
const TEASER_TYPEN = ['commentary', 'generictext'];

@Component({
  selector: 'app-recent-content',
  standalone: true,
  imports: [
    CommonModule,
    ResultCarouselComponent,
    KartenlisteComponent,
    LoadingSpinnerComponent,
    ErrorMessageComponent
  ],
  templateUrl: './recent-content.component.html',
  styleUrls: ['./recent-content.component.css']
})
export class RecentContentComponent implements OnInit, OnDestroy {
  karten: KartenDaten[] = [];
  loading = false;
  error = '';
  /** Bis 599 px eine Liste, darueber das Karussell. */
  istMobil = false;
  private destroy$ = new Subject<void>();

  constructor(
    private contentService: ContentService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private contentRefreshService: ContentRefreshService,
    private breakpointObserver: BreakpointObserver
  ) {}

  ngOnInit(): void {
    this.breakpointObserver
      .observe('(max-width: 599px)')
      .pipe(takeUntil(this.destroy$))
      .subscribe((zustand) => {
        this.istMobil = zustand.matches;
        this.cdr.markForCheck();
      });

    this.loadRecentContent();

    this.contentRefreshService.refresh$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.logger.info('Neueste Inhalte: Aktualisierung angefordert');
        this.loading = true;
        this.cdr.markForCheck();
        this.loadRecentContent();
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRecentContent(): void {
    this.loading = true;
    this.error = '';

    this.contentService.getRecentContent(TEASER_ANZAHL).subscribe({
      next: (response: RecentContentResponse) => {
        this.karten = response.results
          .filter((item) => TEASER_TYPEN.includes(item.result_type))
          .map((item) =>
            ausSuchergebnis({
              score: 1.0,
              statement_text: '',
              statement_similarity_score: 0,
              reply_relevance: 0,
              content_type: item.result_type,
              [`${item.result_type}_result`]: item,
            }),
          );
        this.logger.info(`Neueste Inhalte: ${this.karten.length} Karten`, this.karten.map((karte) => karte.id));
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.logger.error('Failed to load recent content', error);
        this.error = 'Fehler beim Laden der neuesten Inhalte';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  retryLoad = () => {
    this.loadRecentContent();
  }
}
