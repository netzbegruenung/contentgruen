import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { MIT_KONTO_PFAD, ZIEL_PARAM } from '../mit-konto/vorschau-schritte';

/**
 * Routendaten-Schlüssel: Besucher sehen vor der Anmeldung erst „Das erwartet dich mit Konto“
 * (/mit-konto), statt direkt auf der Login-Auswahl zu landen. Gesetzt an den Einstiegen
 * ins Mitmachen (Einwerfen, Beitragen, Fangkorb); andere geschützte Seiten führen weiter
 * direkt zur Anmeldung.
 */
export const MIT_KONTO_VORSCHAU = 'mitKontoVorschau';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  private checkSessionUrl = `${environment.baseUrl}/api/check-session`;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean | UrlTree> {
    return this.http.get(this.checkSessionUrl).pipe(
      map(() => true), // User is authenticated
      catchError(() => {
        // Nicht angemeldet: zur Vorschau oder zur Anmeldung, das Ziel geht jeweils mit
        const ziel = state.url;
        if (route.data?.[MIT_KONTO_VORSCHAU]) {
          return of(this.router.createUrlTree([MIT_KONTO_PFAD], { queryParams: { [ZIEL_PARAM]: ziel } }));
        }
        return of(this.router.createUrlTree(['/login'], { queryParams: { returnUrl: ziel } }));
      })
    );
  }
}
