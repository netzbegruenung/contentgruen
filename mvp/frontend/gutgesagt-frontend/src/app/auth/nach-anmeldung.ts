import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NavigationEnd, Router } from '@angular/router';
import { combineLatest } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { AuthService } from './auth.service';
import { ANLASS_PARAM, NACH_ANMELDUNG_HINWEIS, istAnlass } from './anmeldeanlass';

const HINWEIS_DAUER_MS = 6000;

/**
 * Nach der Rueckkehr von der Anmeldung (Parameter ANLASS_PARAM): Angemeldete bekommen den
 * Satz zum Anlass, der Parameter verschwindet aus der Adresse, auch wenn jemand ohne
 * Anmeldung zurueckkam. Wie hilfeNachAnmeldung erst, wenn feststeht, wer da ist, und nach
 * der Art.-9-Einwilligung: Sonst laege der Hinweis ueber deren Seite.
 */
export function hinweisNachAnmeldung(destroyRef: DestroyRef): void {
  const router = inject(Router);
  const snackBar = inject(MatSnackBar);
  const auth = inject(AuthService);
  const einwilligung = inject(Art9EinwilligungService);
  // Nach Keycloak fuehrt die App das Rueckkehrziel aus dem sessionStorage noch einmal
  // aus (AppComponent): der Parameter kommt dann ein zweites Mal, der Satz nur einmal.
  let gezeigtFuer: string | null = null;
  const adresse$ = router.events.pipe(
    filter((e): e is NavigationEnd => e instanceof NavigationEnd),
    map((e) => router.parseUrl(e.urlAfterRedirects)),
  );
  combineLatest([adresse$, auth.userInfo$, einwilligung.geklaert$])
    .pipe(
      filter(
        ([adresse, info, geklaert]) =>
          adresse.queryParamMap.has(ANLASS_PARAM) && !!info && (!info.isAuthenticated || geklaert === info.userId),
      ),
      takeUntilDestroyed(destroyRef),
    )
    .subscribe(([adresse, info]) => {
      const anlass = adresse.queryParamMap.get(ANLASS_PARAM);
      // Gibt die Navigation false zurueck, hat eine andere sie abgeloest (etwa zur
      // Einwilligung); deren Rueckweg bringt den Parameter wieder und kommt hier erneut an.
      router
        .navigate([], { queryParams: { [ANLASS_PARAM]: null }, queryParamsHandling: 'merge', replaceUrl: true })
        .catch((fehler) => console.warn('Anlass-Parameter liess sich nicht aus der Adresse entfernen:', fehler));
      if (!info?.isAuthenticated || !istAnlass(anlass) || gezeigtFuer === info.userId) {
        return;
      }
      gezeigtFuer = info.userId;
      snackBar.open(NACH_ANMELDUNG_HINWEIS[anlass], 'OK', { duration: HINWEIS_DAUER_MS });
    });
}
