import { Component, ChangeDetectionStrategy, OnInit, AfterViewInit } from '@angular/core';
import { SearchComponent } from '../search/search.component';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { RecentContentComponent } from '../recent-content/recent-content.component';
import { MetricsComponent } from '../metrics/metrics.component';
import { MetricsService } from '../services/metrics.service';
import { AboutTeaserComponent } from '../about-teaser/about-teaser.component';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Router, ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ContentRefreshService } from '../services/content-refresh.service';

@Component({
  selector: 'app-search-view',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ...SHARED_IMPORTS,
    SearchComponent,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    RecentContentComponent,
    MetricsComponent,
    AboutTeaserComponent,
  ],
  templateUrl: './search-view.component.html',
  styleUrls: ['./search-view.component.scss']
})
export class SearchViewComponent implements OnInit, AfterViewInit {
  contentCount$: Observable<number> | undefined;
  contentStats$: Observable<any> | undefined;
  userInfo: UserInfo | null = null;

  constructor(
    private navigationService: NavigationService,
    private logger: LoggingService,
    private metricsService: MetricsService,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private contentRefreshService: ContentRefreshService
  ) {
    this.logger.debug('SearchViewComponent created');
  }

  ngOnInit(): void {
    this.contentCount$ = this.metricsService.getMetrics().pipe(
      map(metrics => metrics.content_count || 0)
    );

    this.contentStats$ = this.metricsService.getMetrics();

    this.authService.userInfo$.subscribe((userInfo: UserInfo | null) => {
      this.userInfo = userInfo;
    });
  }

  ngAfterViewInit(): void {
    const timestamp = new Date().toISOString();
    this.logger.debug(`[${timestamp}] === SEARCH VIEW: ngAfterViewInit START ===`);

    // Handle query params for refresh
    this.route.queryParams.subscribe(params => {
      const paramTimestamp = new Date().toISOString();
      this.logger.debug(`[${paramTimestamp}] Query params received:`, params);

      if (params['refresh'] === 'true') {
        this.logger.info(`[${paramTimestamp}] === REFRESH QUERY PARAM DETECTED ===`);
        this.logger.debug('Will trigger content refresh after 100ms delay');

        setTimeout(() => {
          const triggerTimestamp = new Date().toISOString();
          this.logger.info(`[${triggerTimestamp}] === TRIGGERING CONTENT REFRESH FROM SEARCH VIEW ===`);
          this.contentRefreshService.triggerRefresh();
        }, 100);

        // Clear the refresh query param
        this.logger.debug('Clearing refresh query param');
        this.router.navigate([], {
          queryParams: { refresh: null },
          queryParamsHandling: 'merge',
          replaceUrl: true
        });
      }
    });

    // Handle fragment-based scrolling
    this.route.fragment.subscribe(fragment => {
      const fragTimestamp = new Date().toISOString();
      this.logger.debug(`[${fragTimestamp}] Fragment received:`, fragment);

      if (fragment === 'recent-content') {
        this.logger.info('Will scroll to recent-content after minimal delay for DOM rendering');

        // Small delay just for DOM to render, not for backend indexing
        setTimeout(() => {
          const scrollTimestamp = new Date().toISOString();
          const element = document.getElementById('recent-content');

          if (element) {
            this.logger.info(`[${scrollTimestamp}] === SCROLLING TO RECENT CONTENT ===`);
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
          } else {
            this.logger.error(`[${scrollTimestamp}] Could not find element with id 'recent-content'`);
          }
        }, 100);  // Minimal delay just for DOM rendering
      }
    });

    this.logger.debug('=== SEARCH VIEW: ngAfterViewInit END ===');
  }


  navigateToContributeView(): void {
    this.navigationService.navigateToContribute();
  }

  navigateToContribute(): void {
    this.logger.debug('Navigating to contribute');
    this.navigationService.navigateToContribute();
  }

  login(): void {
    this.logger.debug('Login requested from search view');
    this.authService.login();
  }

  loginToContribute(): void {
    this.logger.debug('Login requested from search view - navigating to contribute after login');
    // Navigate to login with /contribute as returnUrl since this is "Anmelden zum Beitragen"
    this.router.navigate(['/login'], { queryParams: { returnUrl: '/contribute' } });
  }

  getGenericTextCount(stats: any): number {
    if (!stats) return 0;
    // Calculate generictext count as: total content - (statements + commentaries)
    // This assumes content_count includes all content types
    const genericTextCount = (stats.content_count || 0) - ((stats.statement_count || 0) + (stats.commentary_count || 0));
    return genericTextCount > 0 ? genericTextCount : 0;
  }

  performExampleSearch(): void {
    const exampleQuery = 'Windräder töten die Vögel!';
    this.logger.debug('Performing example search:', exampleQuery);
    this.navigationService.navigateToResult(exampleQuery);
  }
}
