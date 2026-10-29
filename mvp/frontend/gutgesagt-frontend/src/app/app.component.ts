import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterOutlet } from '@angular/router';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { NavigationService } from './services/navigation.service';
import { LoggingService } from './services/logging.service';
import { AuthService, UserInfo } from './auth/auth.service';
import { RueckmeldungService } from './services/rueckmeldung.service';
import { ProfilbildService } from './services/profilbild.service';
import { MatDialog } from '@angular/material/dialog';
import { HelpDialogComponent } from './help-dialog/help-dialog.component';
import { FeedbackDialogComponent } from './shared/feedback/feedback-dialog.component';
import { FooterComponent } from "./footer/footer.component";
import { MobileMenuComponent } from './shared/components/mobile-menu/mobile-menu';
import { MobileHeaderComponent } from './shared/components/mobile-header/mobile-header.component';
import { RouteConfigService } from './shared/services/route-config.service';
import { Subject } from 'rxjs';
import { takeUntil, filter } from 'rxjs/operators';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { KETTEN_ICONS } from './shared/fangkorb-texte';
import { ROUTES } from './shared/constants/app.constants';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatTooltipModule,
    MatSidenavModule,
    MatDividerModule,
    MatMenuModule,
    FormsModule,
    RouterOutlet,
    RouterLink,
    FooterComponent,
    MobileMenuComponent,
    MobileHeaderComponent
],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  title = 'Gut gesagt';
  readonly kettenIcons = KETTEN_ICONS;
  readonly hierFehltEineAntwortPfad = ROUTES.HIER_FEHLT_EINE_ANTWORT;
  pageTitle: string = 'Gut gesagt';
  showBackButton: boolean = false;
  private destroy$ = new Subject<void>();
  isMobile: boolean = false;
  isTablet: boolean = false;

  selectedProfilePictureUrl: string = '';

  userInfo: UserInfo | null = null;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService,
    private navigationService: NavigationService,
    private logger: LoggingService,
    private dialog: MatDialog,
    private breakpointObserver: BreakpointObserver,
    private routeConfigService: RouteConfigService,
    private rueckmeldung: RueckmeldungService,
    private profilbild: ProfilbildService) {
    this.logger.debug('AppComponent created');
  }

  ngOnInit() {
    // Set up responsive breakpoint detection
    this.breakpointObserver.observe([
      '(max-width: 599px)',
      '(min-width: 600px) and (max-width: 959px)'
    ]).pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile = result.breakpoints['(max-width: 599px)'];
        this.isTablet = result.breakpoints['(min-width: 600px) and (max-width: 959px)'];
        this.logger.debug(`Device type - Mobile: ${this.isMobile}, Tablet: ${this.isTablet}`);
      });

    // Subscribe to route changes to update page title
    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe((event: NavigationEnd) => {
        this.updatePageTitle(event.urlAfterRedirects);
      });

    // Set initial page title
    this.updatePageTitle(this.router.url);

    // Set initial anonymous avatar while checking auth status
    this.selectedProfilePictureUrl = this.profilbild.profilbild(false);

    // Subscribe to user info changes
    this.authService.userInfo$
      .pipe(takeUntil(this.destroy$))
      .subscribe((userInfo) => {
        this.userInfo = userInfo;
        // Update avatar based on authentication status
        this.updateAvatarForAuthStatus();
      });

    // Rueckmeldung beim Anmelden, wie oft die eigenen Beitraege genutzt wurden (#349)
    this.rueckmeldung.starten();

    // Try to fetch initial user info but don't redirect on failure
    this.authService.fetchUserInfo()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (userInfo) => {
          // User is authenticated
          this.userInfo = userInfo;
          // Set proper profile picture for authenticated user
          this.selectedProfilePictureUrl = this.profilbild.profilbild(true);

          // Check if we have a stored return URL from login (including Keycloak)
          const returnUrl = sessionStorage.getItem('loginReturnUrl');
          if (returnUrl) {
            sessionStorage.removeItem('loginReturnUrl');
            // Navigate to the stored URL
            this.router.navigateByUrl(returnUrl);
          }
        },
        error: () => {
          // Set as anonymous user but don't redirect
          this.authService.setUserInfo({
            isAuthenticated: false,
            userId: null,
            userName: null,
            claims: null
          });
          // Ensure anonymous avatar is set
          this.updateAvatarForAuthStatus();
        },
      });
  }

  openHelpDialog() {
    this.dialog.open(HelpDialogComponent, {
      width: '80vw',
      maxWidth: '80vw',
      data: {} // Pass any data you need here
    });
  }

  openFeedbackDialog(): void {
    this.dialog.open(FeedbackDialogComponent, {
      width: '560px',
      maxWidth: '95vw',
    });
  }

  navigateToContributeView(): void {
    this.navigationService.navigateToContribute();
  }

  navigateToContributionsView(): void {
    this.navigationService.navigateToContributions();
  }

  navigateToRawInputView(): void {
    this.navigationService.navigateToRawInput();
  }

  navigateToRawInputListView(): void {
    this.navigationService.navigateToRawInputList();
  }

  /**
   * Der Pfeil im Desktop-Kopf. Frueher fuehrte er fest auf /search; jetzt eine
   * Ebene hoeher, nach dem Elternziel der Route - dieselbe Methode, die auch der
   * mobile Kopf ruft.
   */
  zurueck(): void {
    this.navigationService.goBack();
  }

  /** Erster Eintrag im mobilen Menue. */
  navigateToHome(): void {
    this.navigationService.navigateHome();
  }

  /**
   * Der Haus-Knopf im Desktop-Kopf - wie der Pfeil ueber den NavigationService,
   * damit eine Seite vorher zu Ende bringen kann, was sie angemeldet hat.
   */
  zurStartseite(): void {
    this.navigationService.navigateHome();
  }

  navigateToAdminDashboard(): void {
    this.router.navigate(['/admin/dashboard']);
  }

  login() {
    // Use current URL as return URL (unless already on login page)
    const currentUrl = this.router.url;
    // Don't set login pages as return URL
    const returnUrl = currentUrl.startsWith('/login') ? '/' : currentUrl;
    this.router.navigate(['/login'], { queryParams: { returnUrl } });
  }

  // Explicit method for login with a specific return URL
  loginWithReturnUrl(returnUrl: string) {
    // If already on login page, don't navigate again (preserves existing returnUrl)
    if (this.router.url.startsWith('/login')) {
      return;
    }
    this.router.navigate(['/login'], { queryParams: { returnUrl } });
  }

  logout() {
    this.authService.logout();
  }

  private updateAvatarForAuthStatus(): void {
    this.selectedProfilePictureUrl = this.profilbild.profilbild(!!this.userInfo?.isAuthenticated);
  }

  toggleMobileMenu(): void {
    if (this.sidenav) {
      this.sidenav.toggle();
    }
  }

  private updatePageTitle(url: string): void {
    const config = this.routeConfigService.getRouteConfig(url);
    this.pageTitle = config.pageTitle;
    this.showBackButton = config.showBackButton;
    this.logger.debug(`Updated page title to: ${this.pageTitle}, showBackButton: ${this.showBackButton}`);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
