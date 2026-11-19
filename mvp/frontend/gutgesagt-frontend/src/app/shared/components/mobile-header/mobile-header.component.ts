import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, NavigationEnd } from '@angular/router';
import { NavigationService } from '../../../services/navigation.service';
import { RouteConfigService } from '../../services/route-config.service';
import { UserInfo } from '../../../auth/auth.service';
import { NEU_HINWEIS } from '../../../rundgang/rundgang-daten';
import { Subject } from 'rxjs';
import { takeUntil, filter } from 'rxjs/operators';

@Component({
  selector: 'app-mobile-header',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule
  ],
  templateUrl: './mobile-header.component.html',
  styleUrls: ['./mobile-header.component.css']
})
export class MobileHeaderComponent implements OnInit, OnDestroy {
  @Input() userInfo: UserInfo | null = null;
  @Input() selectedProfilePictureUrl: string = '';
  /** Neu-Punkt an „Beitragen“, bis Mitmachen beantwortet ist (#587). */
  @Input() beitragenNeu = false;
  readonly neuHinweis = NEU_HINWEIS;
  @Output() openMenu = new EventEmitter<void>();
  @Output() login = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();
  @Output() contribute = new EventEmitter<void>();

  pageTitle: string = 'Gut gesagt';
  showBackButton: boolean = false;
  showContributeButton: boolean = false;
  currentRoute: string = '';
  private destroy$ = new Subject<void>();

  /** Ab dieser Laenge passt der Titel in 28 px nicht neben drei runde Knoepfe. */
  static readonly LANGER_TITEL = 12;

  get titelLang(): boolean {
    return this.pageTitle.length > MobileHeaderComponent.LANGER_TITEL;
  }

  constructor(
    private router: Router,
    private navigationService: NavigationService,
    private routeConfigService: RouteConfigService
  ) {}

  ngOnInit(): void {
    // Subscribe to route changes
    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe((event: NavigationEnd) => {
        this.updateHeaderForRoute(event.urlAfterRedirects);
      });

    // Set initial state
    this.updateHeaderForRoute(this.router.url);
  }

  private updateHeaderForRoute(url: string): void {
    this.currentRoute = url;

    // Get configuration from route config service
    const config = this.routeConfigService.getRouteConfig(url);

    // Apply configuration
    this.pageTitle = config.mobilePageTitle ?? config.pageTitle;
    this.showBackButton = config.showBackButton;
    this.showContributeButton = config.showContributeButton;
  }

  /** Auf /login und /login/managed steht kein Anmelden-Knopf im Kopf (#644). */
  get aufAnmeldung(): boolean {
    return this.currentRoute.startsWith('/login');
  }

  goBack(): void {
    // Ziel kommt aus data.parent der aktiven Route (siehe NavigationService)
    this.navigationService.goBack();
  }

  /** Logo: zur Startseite ueber den NavigationService, damit offene Saetze gespeichert werden (#620). */
  startseite(event: Event): void {
    event.preventDefault();
    void this.navigationService.navigateHome();
  }

  openMobileMenu(): void {
    this.openMenu.emit();
  }

  /** Der Avatar gibt es nur angemeldet; er oeffnet das Menue (#644). */
  openUserMenu(): void {
    this.openMobileMenu();
  }

  /** "+" gibt es nur angemeldet (#644). */
  onContributeClick(): void {
    this.contribute.emit();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
