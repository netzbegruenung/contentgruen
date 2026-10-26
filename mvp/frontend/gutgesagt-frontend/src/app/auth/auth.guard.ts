import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  private checkSessionUrl = `${environment.baseUrl}/api/check-session`;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean> {
    return this.http.get(this.checkSessionUrl).pipe(
      map(() => true), // User is authenticated
      catchError(() => {
        // User is not authenticated - redirect to login with return URL
        const returnUrl = state.url;
        this.router.navigate(['/login'], { queryParams: { returnUrl } });
        return of(false); // Block route activation
      })
    );
  }
}
