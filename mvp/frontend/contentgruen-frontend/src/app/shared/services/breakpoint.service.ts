import { Injectable } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';
import { APP_CONSTANTS } from '../constants/app.constants';

@Injectable({
  providedIn: 'root'
})
export class BreakpointService {

  // Observable for mobile breakpoint
  readonly isMobile$: Observable<boolean>;

  // Observable for tablet breakpoint
  readonly isTablet$: Observable<boolean>;

  // Observable for desktop breakpoint
  readonly isDesktop$: Observable<boolean>;

  // Custom breakpoint queries based on constants
  private readonly mobileQuery = `(max-width: ${APP_CONSTANTS.BREAKPOINTS.MOBILE}px)`;
  private readonly tabletQuery = `(min-width: ${APP_CONSTANTS.BREAKPOINTS.MOBILE + 1}px) and (max-width: ${APP_CONSTANTS.BREAKPOINTS.TABLET}px)`;
  private readonly desktopQuery = `(min-width: ${APP_CONSTANTS.BREAKPOINTS.DESKTOP}px)`;

  constructor(private breakpointObserver: BreakpointObserver) {
    // Initialize mobile observable
    this.isMobile$ = this.breakpointObserver.observe(this.mobileQuery)
      .pipe(
        map(result => result.matches),
        shareReplay(1)
      );

    // Initialize tablet observable
    this.isTablet$ = this.breakpointObserver.observe(this.tabletQuery)
      .pipe(
        map(result => result.matches),
        shareReplay(1)
      );

    // Initialize desktop observable
    this.isDesktop$ = this.breakpointObserver.observe(this.desktopQuery)
      .pipe(
        map(result => result.matches),
        shareReplay(1)
      );
  }

  // Synchronous check methods
  isMobile(): boolean {
    return this.breakpointObserver.isMatched(this.mobileQuery);
  }

  isTablet(): boolean {
    return this.breakpointObserver.isMatched(this.tabletQuery);
  }

  isDesktop(): boolean {
    return this.breakpointObserver.isMatched(this.desktopQuery);
  }

  // Check for handset (mobile or tablet)
  isHandset(): boolean {
    return this.breakpointObserver.isMatched([
      Breakpoints.Handset,
      Breakpoints.TabletPortrait
    ]);
  }

  // Get current breakpoint as string
  getCurrentBreakpoint(): string {
    if (this.isMobile()) return 'mobile';
    if (this.isTablet()) return 'tablet';
    if (this.isDesktop()) return 'desktop';
    return 'unknown';
  }
}
