import { Component, DestroyRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
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
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { NavigationService } from './services/navigation.service';
import { LoggingService } from './services/logging.service';
import { AuthService, UserInfo } from './auth/auth.service';
import { RueckmeldungService } from './services/rueckmeldung.service';
import { Art9EinwilligungService, EINWILLIGUNG_PFAD } from './services/art9-einwilligung.service';
import { ProfilbildService } from './services/profilbild.service';
import { rueckkehrzielLesen, rueckkehrzielLoeschen } from './login/rueckkehrziel';
import { MatDialog } from '@angular/material/dialog';
import { hilfeOeffnen } from './help-dialog/help-dialog.component';
import { feedbackDialogOeffnen } from './shared/feedback/feedback-dialog.component';
import { profilbildDialogOeffnen } from './shared/profilbild/profilbild-dialog.component';
import { FooterComponent } from "./footer/footer.component";
import { MobileMenuComponent } from './shared/components/mobile-menu/mobile-menu';
import { FarbschemaKnopfComponent } from './shared/components/farbschema-knopf/farbschema-knopf.component';
import { MobileHeaderComponent } from './shared/components/mobile-header/mobile-header.component';
import { RouteConfigService } from './shared/services/route-config.service';
import { Subject } from 'rxjs';
import { takeUntil, filter } from 'rxjs/operators';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { DATENSCHUTZ_EINSTELLUNGEN, MENUE_ICONS } from './shared/fangkorb-texte';
import { ROUTES } from './shared/constants/app.constants';
import { RundgangComponent } from './rundgang/rundgang.component';
import { RundgangBandComponent } from './rundgang/rundgang-band.component';
import { RundgangService } from './rundgang/rundgang.service';
import { NEU_HINWEIS, RundgangId } from './rundgang/rundgang-daten';

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
    RouterLinkActive,
    FooterComponent,
    MobileMenuComponent,
    MobileHeaderComponent,
    RundgangComponent,
    RundgangBandComponent,
    FarbschemaKnopfComponent,
],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  title = 'Gut gesagt';
  readonly menueIcons = MENUE_ICONS;
  readonly datenschutzEinstellungen = DATENSCHUTZ_EINSTELLUNGEN;
  readonly neuHinweis = NEU_HINWEIS;
  readonly hierFehltEineAntwortPfad = ROUTES.HIER_FEHLT_EINE_ANTWORT;
  pageTitle: string = 'Gut gesagt';
  showBackButton: boolean = false;
  /** Auf dem Start steht der Skip-Link „Zur Suche“ (#644). */
  aufStart = false;
  /** Auf /login* fehlt der Kopfknopf "Anmelden": Man ist schon da (#645). */
  aufAnmeldeseite = false;
  private destroy$ = new Subject<void>();
  isMobile: boolean = false;
  isTablet: boolean = false;

  /** Laengere Titel setzt der Desktop-Kopf kleiner, damit sie in eine Zeile passen. */
  static readonly LANGER_TITEL = 16;

  get titelLang(): boolean {
    return this.pageTitle.length > AppComponent.LANGER_TITEL;
  }

  /** Unter 1200 px zeigt der Kopf die Textlinks als Icons; dann helfen Tooltips. */
  kopfSchmal = false;

  /** Kommt aus dem ProfilbildService: abgeleitet oder selbst gewaehlt (#437). */
  get selectedProfilePictureUrl(): string {
    return this.profilbild.bild();
  }

  userInfo: UserInfo | null = null;

  protected readonly rundgang = inject(RundgangService);
  private readonly destroyRef = inject(DestroyRef);

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
    private art9Einwilligung: Art9EinwilligungService,
    private profilbild: ProfilbildService) {
    this.logger.debug('AppComponent created');
  }

  ngOnInit() {
    // Set up responsive breakpoint detection
    this.breakpointObserver.observe([
      '(max-width: 599px)',
      '(min-width: 600px) and (max-width: 959px)',
      '(max-width: 1199px)'
    ]).pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.kopfSchmal = !!result.breakpoints['(max-width: 1199px)'];
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
    this.profilbild.setzePerson(null);

    // Subscribe to user info changes
    this.authService.userInfo$
      .pipe(takeUntil(this.destroy$))
      .subscribe((userInfo) => {
        this.userInfo = userInfo;
        this.profilbild.setzePerson(userInfo);
      });

    // Willkommen beim ersten Besuch, Mitmachen nach der ersten Anmeldung (#389)
    this.rundgang.beobachten(this.destroyRef);

    // Rueckmeldung beim Anmelden, wie oft die eigenen Beitraege genutzt wurden (#349)
    this.rueckmeldung.starten();

    // Nach dem Anmelden ohne Art.-9-Einwilligung auf /einwilligung (#489)
    this.art9Einwilligung.starten();

    // Try to fetch initial user info but don't redirect on failure
    this.authService.fetchUserInfo()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (userInfo) => {
          // User is authenticated
          this.userInfo = userInfo;
          this.profilbild.setzePerson(userInfo);

          // Check if we have a stored return URL from login (including Keycloak)
          const returnUrl = rueckkehrzielLesen();
          if (returnUrl) {
            rueckkehrzielLoeschen();
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
          this.profilbild.setzePerson(null);
        },
      });
  }

  openHelpDialog() {
    hilfeOeffnen(this.dialog);
  }

  /** Aus dem mobilen Menue; aus der Hilfe startet der Dialog selbst. */
  rundgangStarten(id: RundgangId): void {
    void this.rundgang.starten(id);
  }

  openProfilbildDialog(): void {
    profilbildDialogOeffnen(this.dialog);
  }

  openFeedbackDialog(): void {
    feedbackDialogOeffnen(this.dialog);
  }

  navigateToContributeView(): void {
    this.navigationService.navigateToContribute();
  }

  navigateToEinwilligung(): void {
    this.router.navigate([EINWILLIGUNG_PFAD]);
  }

  navigateToMeineBeitraege(): void {
    this.navigationService.navigateToMeineBeitraege();
  }

  navigateToEinwerfenView(): void {
    this.navigationService.navigateToEinwerfen();
  }

  navigateToFangkorbView(): void {
    this.navigationService.navigateToFangkorb();
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

  toggleMobileMenu(): void {
    if (this.sidenav) {
      this.sidenav.toggle();
    }
  }

  /** Skip-Link: Fokus ins Suchfeld, ohne die Adresse um #suche zu ergaenzen. */
  zurSuche(event: Event): void {
    event.preventDefault();
    document.getElementById('suche')?.focus();
  }

  private updatePageTitle(url: string): void {
    this.aufStart = url.split(/[?#]/)[0] === '/search';
    const config = this.routeConfigService.getRouteConfig(url);
    this.pageTitle = config.pageTitle;
    this.showBackButton = config.showBackButton;
    this.aufAnmeldeseite = url.split(/[?#]/)[0].startsWith(ROUTES.LOGIN);
    this.logger.debug(`Updated page title to: ${this.pageTitle}, showBackButton: ${this.showBackButton}`);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
