import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ContentService, RecentContentResponse } from '../services/content.service';
import { LoggingService } from '../services/logging.service';
import { ContentRefreshService } from '../services/content-refresh.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { resolveResultComponent } from '../shared/content-type-registry';
import { LoadingSpinnerComponent } from '../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../shared/components/error-message/error-message.component';

@Component({
  selector: 'app-recent-content',
  standalone: true,
  imports: [
    CommonModule,
    ResultCarouselComponent,
    LoadingSpinnerComponent,
    ErrorMessageComponent
  ],
  templateUrl: './recent-content.component.html',
  styleUrls: ['./recent-content.component.css']
})
export class RecentContentComponent implements OnInit, OnDestroy {
  recentContent: any[] = [];
  commentaryItems: any[] = [];
  generictextItems: any[] = [];
  loading = false;
  error = '';
  private destroy$ = new Subject<void>();

  // Per-item component resolution for the mixed-type carousel (replaces UnifiedResultItem).
  readonly resultComponentResolver = resolveResultComponent;

  constructor(
    private contentService: ContentService,
    private logger: LoggingService,
    private cdr: ChangeDetectorRef,
    private contentRefreshService: ContentRefreshService
  ) {
    const timestamp = new Date().toISOString();
    this.logger.debug(`[${timestamp}] === RECENT CONTENT COMPONENT: Constructor ===`);
  }

  ngOnInit(): void {
    const timestamp = new Date().toISOString();
    this.logger.debug(`[${timestamp}] === RECENT CONTENT COMPONENT: ngOnInit START ===`);
    this.logger.debug('Initial loading of recent content');
    this.loadRecentContent();

    // Listen for refresh signals
    this.contentRefreshService.refresh$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        const refreshTimestamp = new Date().toISOString();
        this.logger.info(`[${refreshTimestamp}] === REFRESH SIGNAL RECEIVED ===`);
        this.logger.info('Current content IDs before refresh:', this.recentContent.map(item =>
          item.commentary_result?.id || item.generictext_result?.id
        ));

        // Show loading state immediately
        this.loading = true;
        this.logger.debug('Setting loading to true');
        this.cdr.markForCheck();

        // Content is already indexed when we get here (proven by getById working)
        // Load immediately without delay
        this.logger.info('Loading fresh content immediately (content already indexed)');
        this.loadRecentContent();
      });

    this.logger.debug('=== RECENT CONTENT COMPONENT: ngOnInit END ===');
  }

  ngOnDestroy(): void {
    const timestamp = new Date().toISOString();
    this.logger.debug(`[${timestamp}] === RECENT CONTENT COMPONENT: ngOnDestroy ===`);
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRecentContent(): void {
    const startTimestamp = new Date().toISOString();
    this.logger.debug(`[${startTimestamp}] === LOAD RECENT CONTENT START ===`);

    this.loading = true;
    this.error = '';
    this.logger.debug('Clearing error and setting loading=true');

    this.logger.debug('Calling contentService.getRecentContent(10)...');
    this.contentService.getRecentContent(10).subscribe({
      next: (response: RecentContentResponse) => {
        const responseTimestamp = new Date().toISOString();
        this.logger.info(`[${responseTimestamp}] === CONTENT RESPONSE RECEIVED IN COMPONENT ===`);
        this.logger.info(`Loaded ${response.results_count} recent content items`);
        this.logger.info('Response IDs:', response.results.map(r => r.id));

        // Log current arrays before clearing
        this.logger.debug('Current arrays before clearing:');
        this.logger.debug('- commentaryItems:', this.commentaryItems.length);
        this.logger.debug('- generictextItems:', this.generictextItems.length);
        this.logger.debug('- recentContent:', this.recentContent.length);

        // Clear arrays
        this.commentaryItems = [];
        this.generictextItems = [];
        this.recentContent = [];
        this.logger.debug('Arrays cleared');

        // Transform and separate the results by type
        response.results.forEach(item => {
          // Wrap each item in the expected structure for result carousel
          if (item.result_type === 'commentary') {
            const wrappedItem = {
              score: 1.0, // No relevance score for recent content
              statement_text: '',
              statement_similarity_score: 0,
              reply_relevance: 0,
              commentary_result: item,
              content_type: 'commentary'
            };
            this.commentaryItems.push(wrappedItem);
            this.recentContent.push(wrappedItem);
          } else if (item.result_type === 'generictext') {
            const wrappedItem = {
              score: 1.0, // No relevance score for recent content
              statement_text: '',
              statement_similarity_score: 0,
              reply_relevance: 0,
              generictext_result: item,
              content_type: 'generictext'
            };
            this.generictextItems.push(wrappedItem);
            this.recentContent.push(wrappedItem);
          }
        });

        this.logger.info(`Separated into ${this.commentaryItems.length} commentary and ${this.generictextItems.length} generictext items`);
        this.logger.debug(`Total recentContent length: ${this.recentContent.length}`);

        // Log final IDs in arrays
        this.logger.info('Final content IDs after processing:', this.recentContent.map(item =>
          item.commentary_result?.id || item.generictext_result?.id
        ));

        this.logger.debug(`Setting loading to false`);
        this.loading = false;
        this.cdr.detectChanges();

        const endTimestamp = new Date().toISOString();
        this.logger.debug(`[${endTimestamp}] === LOAD RECENT CONTENT END ===`);
      },
      error: (error) => {
        const errorTimestamp = new Date().toISOString();
        this.logger.error(`[${errorTimestamp}] === ERROR FETCHING CONTENT ===`);
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
