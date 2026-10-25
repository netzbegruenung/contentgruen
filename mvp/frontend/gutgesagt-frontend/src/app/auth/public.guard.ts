import { Injectable } from '@angular/core';
import { CanActivate } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class PublicGuard implements CanActivate {
  private checkSessionUrl = `${environment.baseUrl}/api/check-session`;

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  canActivate(): Observable<boolean> {
    // Try to check if user is authenticated, but allow access regardless
    return this.http.get(this.checkSessionUrl).pipe(
      map(() => {
        // User is authenticated - fetch user info
        this.authService.fetchUserInfo().subscribe();
        return true;
      }),
      catchError(() => {
        // User is not authenticated - still allow access
        this.authService.setUserInfo({
          isAuthenticated: false,
          userId: null,
          userName: null,
          claims: null
        });
        return of(true);
      })
    );
  }
}
