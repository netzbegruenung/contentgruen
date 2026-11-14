import { Component, ChangeDetectionStrategy, AfterViewInit, inject } from '@angular/core';
import { SearchComponent } from '../search/search.component';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NavigationService } from '../services/navigation.service';
import { LoggingService } from '../services/logging.service';
import { SHARED_IMPORTS } from '../shared/shared-imports';
import { RecentContentComponent } from '../recent-content/recent-content.component';
import { OftGenutztComponent } from '../oft-genutzt/oft-genutzt.component';
import { AboutTeaserComponent } from '../about-teaser/about-teaser.component';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { ContentRefreshService } from '../services/content-refresh.service';
import { typLabel } from '../shared/content-type-registry';
import { FANGKORB_KURZ, KETTEN_ICONS } from '../shared/fangkorb-texte';
import { STARTBEISPIEL } from '../shared/startbeispiel';
import { AuthService } from '../auth/auth.service';
import { map } from 'rxjs/operators';
import { RundgangBandComponent } from '../rundgang/rundgang-band.component';
import { SeitLetztemBesuchComponent } from '../seit-letztem-besuch/seit-letztem-besuch.component';

/**
 * Am Desktop mit Maus springt der Fokus beim Laden ins Suchfeld; auf Touch-Geraeten
 * nicht, sonst klappte sofort die Tastatur auf (#644).
 */
export const AUTOFOKUS_MEDIEN = '(min-width: 960px) and (hover: hover) and (pointer: fine)';

@Component({
  selector: 'app-search-view',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ...SHARED_IMPORTS,
    SearchComponent,
    MatButtonModule,
    MatIconModule,
    RouterLink,
    OftGenutztComponent,
    RecentContentComponent,
    AboutTeaserComponent,
    RundgangBandComponent,
    SeitLetztemBesuchComponent,
  ],
  templateUrl: './search-view.component.html',
  styleUrls: ['./search-view.component.scss']
})
export class SearchViewComponent implements AfterViewInit {
  readonly typLabel = typLabel;
  readonly fangkorbKurz = FANGKORB_KURZ;
  readonly kettenIcons = KETTEN_ICONS;
  readonly startbeispiel = STARTBEISPIEL;
  readonly autofokus = typeof window !== 'undefined' && !!window.matchMedia?.(AUTOFOKUS_MEDIEN).matches;
  /** Erst wenn feststeht, dass niemand angemeldet ist: kein Aufblitzen fuer Angemeldete. */
  readonly anonym$ = inject(AuthService).userInfo$.pipe(map((info) => info?.isAuthenticated === false));

  constructor(
    private navigationService: NavigationService,
    private logger: LoggingService,
    private router: Router,
    private route: ActivatedRoute,
    private contentRefreshService: ContentRefreshService
  ) {
    this.logger.debug('SearchViewComponent created');
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

  performExampleSearch(): void {
    // Dieselbe Aussage durchsucht der Rundgang „Antwort finden“ (#389, #601)
    const exampleQuery = STARTBEISPIEL;
    this.logger.debug('Performing example search:', exampleQuery);
    this.navigationService.navigateToResult(exampleQuery);
  }
}
