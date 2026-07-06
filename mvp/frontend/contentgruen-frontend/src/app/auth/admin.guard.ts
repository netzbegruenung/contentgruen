import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, of } from 'rxjs';
import { map, take } from 'rxjs/operators';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root',
})
export class AdminGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> {
    // Use cached user info from AuthService instead of making HTTP call
    return this.authService.userInfo$.pipe(
      take(1), // Take only the current value
      map((userInfo) => {
        // Check if user is authenticated AND is admin
        if (userInfo?.isAuthenticated && userInfo?.isAdmin) {
          return true;
        }

        // If not authenticated at all, redirect to login
        if (!userInfo?.isAuthenticated) {
          const returnUrl = state.url;
          this.router.navigate(['/login'], { queryParams: { returnUrl } });
          return false;
        }

        // User is authenticated but not admin - redirect to home
        this.router.navigate(['/search']);
        return false;
      })
    );
  }
}
