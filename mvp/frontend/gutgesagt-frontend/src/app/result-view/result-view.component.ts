import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { NavigationService } from '../services/navigation.service';
import { Subscription, Observable, Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { SearchService } from '../services/search.service';
import { SearchResponse, GenerictextResult } from '../services/dtos/searchDtos';
import { CommentarySearchResultsComponent } from '../commentary-search-results/commentary-search-results.component';
import { GenerictextSearchResultsComponent } from '../generictext-search-results/generictext-search-results.component';
import { ResultCarouselComponent } from '../result-carousel/result-carousel.component';
import { KartenlisteComponent } from '../beitragskarte/kartenliste.component';
import { KartenDaten, ausSuchergebnis } from '../beitragskarte/karten-daten';
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
import { FORMULAR_PFAD, aussageParameter, istAussageId } from '../shared/formular-adresse';
import { typBeschreibung } from '../shared/content-type-registry';
import { BaseSearchResult } from '../services/dtos/commonDtos';
import { Thema } from '../services/dtos/themenDtos';
import { ThemenFilterComponent } from '../shared/themen/themen-filter.component';

// Dialog configuration constants
const HELP_DIALOG_CONFIG = {
  width: '800px',
  maxWidth: '90vw',
  maxHeight: '90vh',
  panelClass: 'help-dialog'
};

/** Die Abschnitte der Ergebnisseite: am Handy je ein Tab. */
type Ergebnisabschnitt = 'commentary' | 'generictext' | 'post';

/** Ob ein Treffer zum Themenfilter passt; ohne Filter passt jeder. */
function passtZuThema(treffer: BaseSearchResult, thema: string | null): boolean {
  return thema === null || (treffer.themen ?? []).some((t) => t.schluessel === thema);
}

/**
 * Die Themen aller Treffer, jedes einmal, in der Reihenfolge ihres ersten
 * Auftretens. Nur sie stehen im Filter: Ein Thema ohne Treffer liesse die Seite leer.
 */
export function themenDerTreffer(antwort: SearchResponse): Thema[] {
  const gesehen = new Map<string, Thema>();
  const alle: BaseSearchResult[] = [
    ...(antwort.commentary_search_results ?? []),
    ...(antwort.generictext_search_results ?? []),
    ...(antwort.post_search_results ?? []),
  ];
  for (const treffer of alle) {
    for (const thema of treffer.themen ?? []) {
      if (!gesehen.has(thema.schluessel)) {
        gesehen.set(thema.schluessel, thema);
      }
    }
  }
  return [...gesehen.values()];
}

/** Die Suchantwort mit nur den Treffern zum Thema, Zaehler passend dazu. */
export function nachThemaGefiltert(antwort: SearchResponse, thema: string | null): SearchResponse {
  if (thema === null) {
    return antwort;
  }
  const kommentare = (antwort.commentary_search_results ?? []).filter((t) => passtZuThema(t, thema));
  const hintergrund = (antwort.generictext_search_results ?? []).filter((t) => passtZuThema(t, thema));
  const posts = (antwort.post_search_results ?? []).filter((t) => passtZuThema(t, thema));
  return {
    ...antwort,
    commentary_search_results: kommentare,
    commentary_search_results_count: kommentare.length,
    generictext_search_results: hintergrund,
    generictext_search_results_count: hintergrund.length,
    post_search_results: posts,
    post_search_results_count: posts.length,
  };
}

@Component({
  selector: 'app-result-view',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    CommentarySearchResultsComponent,
    GenerictextSearchResultsComponent,
    ResultCarouselComponent,
    KartenlisteComponent,
    SearchComponent,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    MatDividerModule,
    MatChipsModule,
    LoadingSpinnerComponent,
    ErrorMessageComponent,
    ThemenFilterComponent
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

  // Einmal je Suchantwort umgerechnet, nicht im Template: neue Objekte bei jeder
  // Change Detection setzten die Karten zurueck (aufgeklappte Aussage, Kurz/Lang).
  kommentarKarten: KartenDaten[] = [];
  hintergrundKarten: KartenDaten[] = [];
  postKarten: KartenDaten[] = [];

  // Mobile navigation
  isMobile: boolean = false;
  isTablet: boolean = false;
  currentSection: Ergebnisabschnitt = 'commentary';
  hasCommentaryResults: boolean = false;
  hasGenerictextResults: boolean = false;
  hasPostResults: boolean = false;

  // Themenfilter: die Themen der Aussagen, ueber die die Treffer gefunden wurden.
  // `angezeigt` ist die Suchantwort mit nur den Treffern zum aktiven Thema.
  private antwort: SearchResponse | null = null;
  angezeigt: SearchResponse | null = null;
  themenDerTreffer: Thema[] = [];
  aktivesThema: string | null = null;

  // Erklaerzeile je Tab, derselbe Satz wie auf der Beitragen-Seite
  readonly kommentarErklaerung = typBeschreibung('commentary');
  readonly hintergrundErklaerung = typBeschreibung('generictext');
  readonly postErklaerung = typBeschreibung('post');

  // User authentication
  userInfo: UserInfo | null = null;

  // Popular topics for empty state suggestions
  popularTopics: string[] = ['Klimaschutz', 'Mobilität', 'Energie', 'Soziales', 'Digitalisierung', 'Bildung'];

  // Avatar properties
  selectedProfilePictureUrl: string = '';
  // Lokal ausgeliefert statt von der DiceBear-API, siehe
  // scripts/generate-avatars.mjs.
  anonymousAvatars: string[] = [
    '/avatars/anon-female.svg',
    '/avatars/anon-male.svg'
  ];
  profilePictures: string[] = [
    '/avatars/female1.svg',
    '/avatars/female2.svg',
    '/avatars/female3.svg',
    '/avatars/female4.svg',
    '/avatars/female5.svg',
    '/avatars/female6.svg',
    '/avatars/male1.svg',
    '/avatars/male2.svg',
    '/avatars/male3.svg',
    '/avatars/male4.svg',
    '/avatars/male5.svg',
    '/avatars/male6.svg',
  ];

  constructor(
    private searchService: SearchService,
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
        this.antwort = response;
        // Eine neue Suche beginnt ohne Filter.
        this.aktivesThema = null;
        this.themenDerTreffer = response ? themenDerTreffer(response) : [];
        this.anzeigen();
      });

    // Listen to query parameters and fetch results
    this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
      this.searchQuery = params['searchQuery'] || '';
      if (this.searchQuery) {
        this.performSearch();
      }
    });
  }

  /** Nach einem Thema filtern; null = alle. */
  nachThemaFiltern(thema: string | null): void {
    this.aktivesThema = thema;
    this.anzeigen();
  }

  /** Karten und Abschnitte aus der Suchantwort, gefiltert nach dem aktiven Thema. */
  private anzeigen(): void {
    const response = this.antwort ? nachThemaGefiltert(this.antwort, this.aktivesThema) : null;
    this.angezeigt = response;
    if (response) {
      this.hasCommentaryResults = response.commentary_search_results_count > 0;
      this.hasGenerictextResults = response.generictext_search_results_count > 0;
      this.kommentarKarten = (response.commentary_search_results ?? []).map((paket) => ausSuchergebnis(paket));
      this.hintergrundKarten = (response.generictext_search_results ?? []).map((paket) => ausSuchergebnis(paket));
      this.hasPostResults = (response.post_search_results_count ?? 0) > 0;
      this.postKarten = (response.post_search_results ?? []).map((paket) => ausSuchergebnis(paket));

      // Der erste Abschnitt mit Treffern: Kommentar, dann Hintergrundinfo, dann Post
      if (this.hasCommentaryResults) {
        this.currentSection = 'commentary';
      } else if (this.hasGenerictextResults) {
        this.currentSection = 'generictext';
      } else if (this.hasPostResults) {
        this.currentSection = 'post';
      }
    }
    this.cdr.markForCheck();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.queryParamsSubscription?.unsubscribe();
  }

  // Switch sections (for tab navigation)
  /** Irgendein Treffer, gleich welchen Typs. */
  get hatTreffer(): boolean {
    return this.hasCommentaryResults || this.hasGenerictextResults || this.hasPostResults;
  }

  switchToSection(section: Ergebnisabschnitt): void {
    this.currentSection = section;
    this.cdr.markForCheck();
  }

  /**
   * Neue Suche. Die Aussage zur Suchanfrage legt das Backend im Suchaufruf selbst
   * an und liefert ihre ID in der Antwort (statement_id) - die Ansicht ruft dafuer
   * nichts Eigenes mehr auf. Frueher tat sie das ueber /statement/*, und fuer
   * Anonyme endete das mit 401 und einem Sprung auf /login.
   */
  private performSearch(): void {
    // Ergebnisse und Aussage der vorigen Suche gelten nicht mehr - und zwar ab
    // sofort, nicht erst mit loading=true. Wer in diesem Fenster auf "hinzufuegen"
    // tippt, darf nicht an die alte Aussage antworten.
    this.stateService.neueSucheBeginnen();
    this.fetchSearchResults();
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

  /**
   * Nur bekannte, lokal ausgelieferte Avatare akzeptieren. In sessionStorage
   * kann noch eine alte DiceBear-CDN-URL aus einer frueheren Sitzung
   * liegen; die wuerde den Drittabruf sonst weiter ausloesen.
   */
  private isKnownAvatar(url: string | null): url is string {
    return !!url && (this.profilePictures.includes(url) || this.anonymousAvatars.includes(url));
  }

  private initializeAvatar(): void {
    const storedAvatar = sessionStorage.getItem('userAvatar');
    const storedAnonymous = sessionStorage.getItem('anonymousAvatar');

    if (this.userInfo?.isAuthenticated && this.isKnownAvatar(storedAvatar)) {
      this.selectedProfilePictureUrl = storedAvatar;
    } else if (!this.userInfo?.isAuthenticated && this.isKnownAvatar(storedAnonymous)) {
      this.selectedProfilePictureUrl = storedAnonymous;
    } else {
      this.updateAvatarForAuthStatus();
    }
  }

  private updateAvatarForAuthStatus(): void {
    if (!this.userInfo?.isAuthenticated) {
      const storedAnonymous = sessionStorage.getItem('anonymousAvatar');
      if (this.isKnownAvatar(storedAnonymous)) {
        this.selectedProfilePictureUrl = storedAnonymous;
      } else {
        const randomIndex = Math.floor(Math.random() * this.anonymousAvatars.length);
        this.selectedProfilePictureUrl = this.anonymousAvatars[randomIndex];
        sessionStorage.setItem('anonymousAvatar', this.selectedProfilePictureUrl);
      }
    } else {
      const storedAvatar = sessionStorage.getItem('userAvatar');
      if (this.isKnownAvatar(storedAvatar)) {
        this.selectedProfilePictureUrl = storedAvatar;
      } else {
        const randomIndex = Math.floor(Math.random() * this.profilePictures.length);
        this.selectedProfilePictureUrl = this.profilePictures[randomIndex];
        sessionStorage.setItem('userAvatar', this.selectedProfilePictureUrl);
      }
    }
  }

  /**
   * Ins Formular des Typs, als Antwort auf die Aussage dieser Suche: per ID, wo
   * die Suchantwort sie liefert, sonst mit dem Suchtext.
   */
  navigateToContribute(typ: 'commentary' | 'generictext'): void {
    const { searchResults, loading } = this.stateService.currentState;
    // Waehrend eine Suche laeuft, stehen noch die Ergebnisse der vorigen im Zustand.
    const ausAntwort = !loading && istAussageId(searchResults?.statement_id) ? searchResults!.statement_id : null;
    this.router.navigate([FORMULAR_PFAD[typ]], {
      queryParams: aussageParameter(ausAntwort, this.searchQuery),
    });
  }

  /**
   * Search for a specific topic
   */
  searchForTopic(topic: string): void {
    this.navigationService.navigateToResult(topic);
  }
}
