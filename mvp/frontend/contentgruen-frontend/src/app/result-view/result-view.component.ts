import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, Type, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { NavigationService } from '../services/navigation.service';
import { Subscription, Observable, Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { SearchService } from '../services/search.service';
import { StatementService } from '../services/statement.service';
import { SearchResponse, GenerictextResult } from '../services/dtos/searchDtos';
import { CommentarySearchResultsComponent } from '../commentary-search-results/commentary-search-results.component';
import { GenerictextSearchResultsComponent } from '../generictext-search-results/generictext-search-results.component';
import { CONTENT_TYPE_REGISTRY } from '../shared/content-type-registry';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { SearchComponent } from '../search/search.component';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { StateManagementService } from '../services/state-management.service';
import { LoadingSpinnerComponent } from '../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../shared/components/error-message/error-message.component';
import { LoggingService } from '../services/logging.service';
import { BreakpointObserver } from '@angular/cdk/layout';
import { AuthService, UserInfo } from '../auth/auth.service';
import { HelpDialogComponent } from '../help-dialog/help-dialog.component';

// Dialog configuration constants
const HELP_DIALOG_CONFIG = {
  width: '800px',
  maxWidth: '90vw',
  maxHeight: '90vh',
  panelClass: 'help-dialog'
};

@Component({
  selector: 'app-result-view',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    CommentarySearchResultsComponent,
    GenerictextSearchResultsComponent,
    ResultCarouselComponent,
    SearchComponent,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    MatDividerModule,
    MatChipsModule,
    LoadingSpinnerComponent,
    ErrorMessageComponent
  ],
  templateUrl: './result-view.component.html',
  styleUrls: ['./result-view.component.css'],
})
export class ResultViewComponent implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  searchQuery$: Observable<string>;
  searchResponse$: Observable<SearchResponse | null>;
  loading$: Observable<boolean>;
  error$: Observable<string | null>;

  searchQuery: string = '';
  searchResponse: SearchResponse | null = null;
  generictextSearchResults: GenerictextResult[] = [];
  loading: boolean = false;
  error: string = '';
  private queryParamsSubscription?: Subscription;
  private destroy$ = new Subject<void>();

  // Component types for carousels, sourced from the content-type registry.
  commentaryResultItemComponent: Type<any> = CONTENT_TYPE_REGISTRY['commentary'].resultComponent;
  generictextResultItemComponent: Type<any> = CONTENT_TYPE_REGISTRY['generictext'].resultComponent;

  // Mobile navigation
  isMobile: boolean = false;
  isTablet: boolean = false;
  currentSection: 'commentary' | 'generictext' = 'commentary';
  hasCommentaryResults: boolean = false;
  hasGenerictextResults: boolean = false;

  // User authentication
  userInfo: UserInfo | null = null;

  // Popular topics for empty state suggestions
  popularTopics: string[] = ['Klimaschutz', 'Mobilität', 'Energie', 'Soziales', 'Digitalisierung', 'Bildung'];

  // Avatar properties
  selectedProfilePictureUrl: string = '';
  anonymousAvatars: string[] = [
    'https://api.dicebear.com/7.x/avataaars/svg?seed=anon-female&backgroundColor=e0e0e0&mouth=smile&eyes=happy',
    'https://api.dicebear.com/7.x/avataaars/svg?seed=anon-male&backgroundColor=e0e0e0&mouth=smile&eyes=happy'
  ];
  profilePictures: string[] = [
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female1&backgroundColor=b6e3f4&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female2&backgroundColor=ffd5dc&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female3&backgroundColor=c0aede&mouth=twinkle&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female4&backgroundColor=ffdfbf&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female5&backgroundColor=d1f4e0&mouth=twinkle&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=female6&backgroundColor=ffc0cb&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male1&backgroundColor=aec6cf&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male2&backgroundColor=ffb6c1&mouth=twinkle&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male3&backgroundColor=ffd700&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male4&backgroundColor=98fb98&mouth=smile&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male5&backgroundColor=dda0dd&mouth=twinkle&eyes=happy",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=male6&backgroundColor=f0e68c&mouth=smile&eyes=happy",
  ];

  constructor(
    private searchService: SearchService,
    private statementService: StatementService,
    private navigationService: NavigationService,
    private stateService: StateManagementService,
    private logger: LoggingService,
    private authService: AuthService,
    private dialog: MatDialog,
    private router: Router,
    private route: ActivatedRoute,
    private breakpointObserver: BreakpointObserver,
    private cdr: ChangeDetectorRef
  ) {
    // Connect to state observables
    this.searchQuery$ = this.stateService.searchQuery$;
    this.searchResponse$ = this.stateService.searchResults$;
    this.loading$ = this.stateService.loading$;
    this.error$ = this.stateService.error$;
  }

  ngOnInit(): void {
    // Set up mobile and tablet detection
    this.breakpointObserver.observe(['(max-width: 599px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile = result.matches;
        this.cdr.markForCheck();
      });

    this.breakpointObserver.observe(['(min-width: 600px) and (max-width: 959px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isTablet = result.matches;
        this.cdr.markForCheck();
      });

    // Subscribe to user info changes
    this.authService.userInfo$
      .pipe(takeUntil(this.destroy$))
      .subscribe((userInfo) => {
        this.userInfo = userInfo;
        this.updateAvatarForAuthStatus();
        this.cdr.markForCheck();
      });

    // Initialize avatar
    this.initializeAvatar();

    // Monitor search results to determine available sections
    this.searchResponse$
      .pipe(takeUntil(this.destroy$))
      .subscribe(response => {
        if (response) {
          this.hasCommentaryResults = response.commentary_search_results_count > 0;
          this.hasGenerictextResults = response.generictext_search_results_count > 0;

          // Default to commentary if available, otherwise generictext
          if (this.hasCommentaryResults) {
            this.currentSection = 'commentary';
          } else if (this.hasGenerictextResults) {
            this.currentSection = 'generictext';
          }

          this.cdr.markForCheck();
        }
      });

    // Listen to query parameters and fetch results
    this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
      this.searchQuery = params['searchQuery'] || '';
      if (this.searchQuery) {
        this.performSearchWithStatement();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.queryParamsSubscription?.unsubscribe();
  }

  // Switch sections (for tab navigation)
  switchToSection(section: 'commentary' | 'generictext'): void {
    this.currentSection = section;
    this.cdr.markForCheck();
  }

  /**
   * Performs search and ensures a statement exists for the search query
   * This maintains the current behavior but with proper separation of concerns
   */
  private performSearchWithStatement(): void {
    // First, ensure the statement exists
    this.statementService.findOrCreateStatement(this.searchQuery, 'search_query').subscribe({
      next: (statementResponse) => {
        if (statementResponse.statement_was_new) {
          this.logger.info('Created new statement for search query:', statementResponse.statement_id);
        } else {
          this.logger.debug('Using existing statement:', statementResponse.statement_id);
        }

        // Store the statement ID in the search response for reference
        // This will be available when we get the search results
        this.stateService.setStatementId(statementResponse.statement_id);

        // Now perform the actual search
        this.fetchSearchResults();
      },
      error: (error) => {
        this.logger.error('Error creating statement for search, proceeding with search anyway', error);
        // Even if statement creation fails, we still perform the search
        this.fetchSearchResults();
      }
    });
  }

  /**
   * Fetch search results for the query entered by the user.
   */
  private fetchSearchResults(): void {
    this.searchService.search(this.searchQuery, 10).subscribe();
  }

  retrySearch = (): void => {
    this.fetchSearchResults();
  }

  navigateToStart(): void {
    this.navigationService.navigateToStart();
  }

  navigateToContributeView(): void {
    this.navigationService.navigateToContribute();
  }

  navigateToContributionsView(): void {
    this.navigationService.navigateToContributions();
  }

  login(): void {
    this.authService.login();
  }

  logout(): void {
    this.authService.logout();
  }

  toggleMobileMenu(): void {
    this.sidenav?.toggle();
  }

  openHelpDialog(): void {
    this.dialog.open(HelpDialogComponent, HELP_DIALOG_CONFIG);
  }

  handleContributeClick(): void {
    if (this.userInfo?.isAuthenticated) {
      this.navigateToContributeView();
    } else {
      this.login();
    }
  }

  getContributeButtonLabel(): string {
    return this.userInfo?.isAuthenticated ? 'Beitragen' : 'Anmelden zum Beitragen';
  }

  private initializeAvatar(): void {
    const storedAvatar = sessionStorage.getItem('userAvatar');
    const storedAnonymous = sessionStorage.getItem('anonymousAvatar');

    if (this.userInfo?.isAuthenticated && storedAvatar) {
      this.selectedProfilePictureUrl = storedAvatar;
    } else if (!this.userInfo?.isAuthenticated && storedAnonymous) {
      this.selectedProfilePictureUrl = storedAnonymous;
    } else {
      this.updateAvatarForAuthStatus();
    }
  }

  private updateAvatarForAuthStatus(): void {
    if (!this.userInfo?.isAuthenticated) {
      const storedAnonymous = sessionStorage.getItem('anonymousAvatar');
      if (storedAnonymous) {
        this.selectedProfilePictureUrl = storedAnonymous;
      } else {
        const randomIndex = Math.floor(Math.random() * this.anonymousAvatars.length);
        this.selectedProfilePictureUrl = this.anonymousAvatars[randomIndex];
        sessionStorage.setItem('anonymousAvatar', this.selectedProfilePictureUrl);
      }
    } else {
      const storedAvatar = sessionStorage.getItem('userAvatar');
      if (storedAvatar) {
        this.selectedProfilePictureUrl = storedAvatar;
      } else {
        const randomIndex = Math.floor(Math.random() * this.profilePictures.length);
        this.selectedProfilePictureUrl = this.profilePictures[randomIndex];
        sessionStorage.setItem('userAvatar', this.selectedProfilePictureUrl);
      }
    }
  }

  /**
   * Navigate to contribute view with specified panel
   */
  navigateToContribute(panel: 'commentary' | 'generictext'): void {
    const statementText = this.searchQuery;
    this.router.navigate(['/contribute'], { queryParams: { panel, searchQuery: statementText } });
  }

  /**
   * Search for a specific topic
   */
  searchForTopic(topic: string): void {
    this.navigationService.navigateToResult(topic);
  }
}
