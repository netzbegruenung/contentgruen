import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatDividerModule } from '@angular/material/divider';
import { FormsModule } from '@angular/forms';
import { RouterOutlet } from '@angular/router';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { NavigationService } from './services/navigation.service';
import { LoggingService } from './services/logging.service';
import { AuthService, UserInfo } from './auth/auth.service';
import { MatDialog } from '@angular/material/dialog';
import { HelpDialogComponent } from './help-dialog/help-dialog.component';
import { FooterComponent } from "./footer/footer.component";
import { MobileMenuComponent } from './shared/components/mobile-menu/mobile-menu';
import { MobileHeaderComponent } from './shared/components/mobile-header/mobile-header.component';
import { RouteConfigService } from './shared/services/route-config.service';
import { Subject } from 'rxjs';
import { takeUntil, filter } from 'rxjs/operators';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';

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
    FormsModule,
    RouterOutlet,
    FooterComponent,
    MobileMenuComponent,
    MobileHeaderComponent
],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  title = 'ContentGrün';
  pageTitle: string = 'ContentGrün';
  showBackButton: boolean = false;
  private destroy$ = new Subject<void>();
  isMobile: boolean = false;
  isTablet: boolean = false;

  selectedProfilePictureUrl: string = '';
  anonymousAvatars: string[] = [
    'https://api.dicebear.com/7.x/initials/svg?seed=question&chars=%3F&backgroundColor=e0e0e0',
    'https://api.dicebear.com/7.x/shapes/svg?seed=anon&backgroundColor=e0e0e0'
  ];
  currentAnonymousIndex: number = 0;
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

  userInfo: UserInfo | null = null;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService,
    private navigationService: NavigationService,
    private logger: LoggingService,
    private dialog: MatDialog,
    private breakpointObserver: BreakpointObserver,
    private routeConfigService: RouteConfigService) {
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
    this.selectedProfilePictureUrl = this.anonymousAvatars[this.currentAnonymousIndex];

    // Subscribe to user info changes
    this.authService.userInfo$
      .pipe(takeUntil(this.destroy$))
      .subscribe((userInfo) => {
        this.userInfo = userInfo;
        // Update avatar based on authentication status
        this.updateAvatarForAuthStatus();
      });

    // Try to fetch initial user info but don't redirect on failure
    this.authService.fetchUserInfo()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (userInfo) => {
          // User is authenticated
          this.userInfo = userInfo;
          // Set proper profile picture for authenticated user
          this.setRandomProfilePicture();

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

  navigateToSearchView(): void {
    this.router.navigate(['/search']);
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

  private setRandomProfilePicture(): void {
    const sessionProfilePicture = sessionStorage.getItem('profilePicture');
    if (sessionProfilePicture) {
      // Use the session-stored profile picture
      this.selectedProfilePictureUrl = sessionProfilePicture;
      this.logger.debug('Using stored profile picture:', this.selectedProfilePictureUrl);
    } else {
      this.logger.debug('No stored profile picture, generating new one');
      this.regenerateProfilePicture();
    }
  }

  regenerateProfilePicture(): void {
    if (this.userInfo?.isAuthenticated) {
      // For logged-in users, randomly select from profile pictures
      const randomIndex = Math.floor(Math.random() * this.profilePictures.length);
      this.selectedProfilePictureUrl = this.profilePictures[randomIndex];
      this.logger.debug('Selected profile picture:', this.selectedProfilePictureUrl);
      sessionStorage.setItem('profilePicture', this.selectedProfilePictureUrl);
    } else {
      // For anonymous users, toggle between male/female anonymous avatars
      this.currentAnonymousIndex = (this.currentAnonymousIndex + 1) % this.anonymousAvatars.length;
      this.selectedProfilePictureUrl = this.anonymousAvatars[this.currentAnonymousIndex];
      sessionStorage.setItem('anonymousAvatar', this.selectedProfilePictureUrl);
    }
  }

  private updateAvatarForAuthStatus(): void {
    if (!this.userInfo?.isAuthenticated) {
      // Use anonymous avatar for logged-out users
      const storedAnonymous = sessionStorage.getItem('anonymousAvatar');
      if (storedAnonymous && this.anonymousAvatars.includes(storedAnonymous)) {
        this.selectedProfilePictureUrl = storedAnonymous;
        this.currentAnonymousIndex = this.anonymousAvatars.indexOf(storedAnonymous);
      } else {
        this.selectedProfilePictureUrl = this.anonymousAvatars[this.currentAnonymousIndex];
        sessionStorage.setItem('anonymousAvatar', this.selectedProfilePictureUrl);
      }
    } else {
      // Clear anonymous avatar from storage when logging in
      sessionStorage.removeItem('anonymousAvatar');
      // Use the stored or generate new avatar for logged-in users
      this.setRandomProfilePicture();
    }
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
