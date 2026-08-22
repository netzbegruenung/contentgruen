import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { Router, NavigationEnd } from '@angular/router';
import { NavigationService } from '../../../services/navigation.service';
import { RouteConfigService } from '../../services/route-config.service';
import { UserInfo } from '../../../auth/auth.service';
import { Subject } from 'rxjs';
import { takeUntil, filter } from 'rxjs/operators';

@Component({
  selector: 'app-mobile-header',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule
  ],
  templateUrl: './mobile-header.component.html',
  styleUrls: ['./mobile-header.component.css']
})
export class MobileHeaderComponent implements OnInit, OnDestroy {
  @Input() userInfo: UserInfo | null = null;
  @Input() selectedProfilePictureUrl: string = '';
  @Output() openMenu = new EventEmitter<void>();
  @Output() login = new EventEmitter<void>();
  @Output() loginToContribute = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();
  @Output() contribute = new EventEmitter<void>();
  @Output() contributions = new EventEmitter<void>();

  pageTitle: string = 'Gut gesagt';
  showBackButton: boolean = false;
  showContributeButton: boolean = false;
  showContributionsButton: boolean = false;
  currentRoute: string = '';
  private destroy$ = new Subject<void>();

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
    this.pageTitle = config.pageTitle;
    this.showBackButton = config.showBackButton;
    this.showContributeButton = config.showContributeButton;
    this.showContributionsButton = config.showContributionsButton;
  }

  goBack(): void {
    // Use navigation service for consistent back behavior
    this.navigationService.goBack();
  }

  openMobileMenu(): void {
    this.openMenu.emit();
  }

  openUserMenu(): void {
    // Quick user menu for avatar click
    // Could open a small menu with logout/profile options
    if (this.userInfo?.isAuthenticated) {
      // For now, just emit logout event
      // In future, could show a small menu
      this.openMobileMenu();
    } else {
      this.login.emit();
    }
  }

  onContributeClick(): void {
    if (this.userInfo?.isAuthenticated) {
      this.contribute.emit();
    } else {
      this.loginToContribute.emit();
    }
  }

  onContributionsClick(): void {
    this.contributions.emit();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
