import { HttpClient } from '@angular/common/http';
import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, UrlTree } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { ZIEL_PARAM, vorschauZiel } from './vorschau-schritte';

/**
 * Die Vorschau ist nur für Besucher: Wer angemeldet ist, geht gleich zum Ziel, statt eine
 * Seite über das Anmelden zu sehen. Besucher bekommen dieselben Anmeldedaten gesetzt wie
 * auf öffentlichen Seiten (PublicGuard).
 */
export const mitKontoVorschauGuard: CanActivateFn = (route: ActivatedRouteSnapshot): Observable<boolean | UrlTree> => {
  const http = inject(HttpClient);
  const router = inject(Router);
  const auth = inject(AuthService);
  return http.get(`${environment.baseUrl}/api/check-session`).pipe(
    map(() => router.parseUrl(vorschauZiel(route.queryParamMap.get(ZIEL_PARAM)))),
    catchError(() => {
      auth.setUserInfo({ isAuthenticated: false, userId: null, userName: null, claims: null });
      return of(true);
    }),
  );
};
