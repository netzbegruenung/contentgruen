// src/app/auth/auth.interceptor.ts
import { HttpRequest, HttpHandlerFn, HttpEvent, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PublicEndpoints } from '../shared/public-endpoints';
import { einwilligungFehlt, ohneEinwilligungsUmleitung, zurEinwilligungFuehren } from '../services/art9-einwilligung.service';
import { Art9EinwilligungZustand } from '../services/art9-einwilligung-zustand';
import { STILLE_ABFRAGE } from '../shared/selbst-nachladen';

export const EINWILLIGUNG_FEHLT_HINWEIS = 'Zum Beitragen und Bewerten brauchst du deine Einwilligung.';
const HINWEIS_DAUER_MS = 10000;

export const AuthInterceptor: HttpInterceptorFn = (req: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> => {
  const router = inject(Router);  // Inject Router for navigation
  const snackBar = inject(MatSnackBar);
  const einwilligungZustand = inject(Art9EinwilligungZustand);

  const modifiedRequest = req.clone({
    withCredentials: true,  // Ensures cookies are included also cross-origin
  });

  return next(modifiedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Check if the request is for a public endpoint. Hintergrund-Abfragen (Nachladen,
        // Zahl am Admin-Link) leiten nie um: Sonst risse eine abgelaufene Sitzung die
        // Person mitten beim Tippen auf /login.
        if (!PublicEndpoints.isPublicEndpoint(req.url) && !req.context.get(STILLE_ABFRAGE)) {
          // Redirect to login with current URL as return URL for protected endpoints
          const currentUrl = window.location.pathname + window.location.search;
          router.navigate(['/login'], { queryParams: { returnUrl: currentUrl } });
        }
      }
      // Ohne Art.-9-Einwilligung sperrt das Backend das Speichern (#489). Nicht von
      // selbst wegnavigieren, sonst ginge der Text im Formular verloren: ein Hinweis,
      // der auf Wunsch zur Einwilligung fuehrt und danach zurueck an diese Stelle.
      // Erst nach dem Fehlerzweig des Aufrufers: Oeffnet der selbst einen Hinweis,
      // ersetzte der sonst diesen, und der Knopf waere weg.
      // Hat die Seite einen eigenen Hinweiskasten (Formulare, B4), zeigt der den
      // Hinweis; ein zweiter als Snackbar waere doppelt. In den Blick holen ihn die
      // Formulare selbst, nur bei einer Aktion der Person, nie beim Speichern im
      // Hintergrund (Review zu #670).
      // Auf /einwilligung selbst (und was sie verlinkt) keine Snackbar: Ein spaeter 403,
      // etwa der Satz beim Verlassen von Destillieren, laege sonst ueber ihren Knoepfen,
      // und sein "Einwilligen" fuehrte nirgendwohin (Review zu #670).
      const einwilligungHier = einwilligungFehlt(error) && ohneEinwilligungsUmleitung(router.url ?? '/');
      if (einwilligungFehlt(error)) {
        einwilligungZustand.setzen('fehlt');
      }
      if (einwilligungFehlt(error) && !einwilligungZustand.hinweisDa && !einwilligungHier) {
        setTimeout(() =>
          snackBar
            .open(EINWILLIGUNG_FEHLT_HINWEIS, 'Einwilligen', { duration: HINWEIS_DAUER_MS })
            .onAction()
            .subscribe(() => zurEinwilligungFuehren(router)),
        );
      }
      return throwError(() => error);  // Pass error along to be handled if needed
    })
  );
};
