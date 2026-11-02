import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable } from 'rxjs';
import { filter, map, take } from 'rxjs/operators';
import { AuthService, UserInfo } from './auth.service';

@Injectable({
  providedIn: 'root',
})
export class AdminGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> {
    // Auf die erste echte Antwort warten: Beim Direktaufruf oder Neuladen ist
    // userInfo$ noch null, bis AppComponent /user-info beantwortet hat (#512).
    // Schlaegt die Abfrage fehl, setzt AppComponent einen Besucher, also kommt
    // immer ein Wert.
    return this.authService.userInfo$.pipe(
      filter((userInfo): userInfo is UserInfo => userInfo !== null),
      take(1),
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
