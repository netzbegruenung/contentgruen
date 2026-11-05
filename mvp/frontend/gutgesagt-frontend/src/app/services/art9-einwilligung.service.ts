import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { Observable, Subscription, of } from 'rxjs';
import { catchError, distinctUntilChanged, filter, map, switchMap, take } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { AuthService } from '../auth/auth.service';

/**
 * Ein Wortlaut der Art.-9-Einwilligung; die Kennung ist sein Stand-Datum, ein zweiter
 * Wortlaut vom selben Tag mit Suffix (z. B. 2026-11-05-b).
 */
export interface Art9Wortlaut {
  kennung: string;
  text: string;
}

/** Antwort von GET /api/v1/art9-einwilligung (api/v1/art9_einwilligung.py). */
export interface Art9EinwilligungStand {
  eingewilligt: boolean;
  /** Kennung des Wortlauts, dem die Person zugestimmt hat, auch nach einem Widerruf. */
  wortlaut: string | null;
  eingewilligt_am: string | null;
  widerrufen_am: string | null;
  aktueller_wortlaut: Art9Wortlaut;
}

/** Antworttext des Backends, wenn ein Endpunkt die Einwilligung verlangt (dependencies.py). */
export const ART9_EINWILLIGUNG_FEHLT = 'art9_einwilligung_fehlt';

export const EINWILLIGUNG_PFAD = '/einwilligung';

/**
 * Das Stand-Datum (JJJJ-MM-TT) aus der Kennung eines Wortlauts, ohne Suffix; null, wenn
 * sie nicht mit einem Datum beginnt. Die DatePipe wirft bei einer Kennung mit Suffix.
 */
export function wortlautDatum(kennung: string | null | undefined): string | null {
  const datum = kennung?.match(/^\d{4}-\d{2}-\d{2}/);
  return datum ? datum[0] : null;
}

/** Ob ein HTTP-Fehler die fehlende Art.-9-Einwilligung meldet (403 mit Kennzeichen). */
export function einwilligungFehlt(fehler: { status?: number; error?: any } | null | undefined): boolean {
  return fehler?.status === 403 && fehler?.error?.detail === ART9_EINWILLIGUNG_FEHLT;
}

/**
 * Seiten, von denen aus nicht auf die Einwilligung umgeleitet wird: die Seite selbst,
 * was sie verlinkt, und die Anmeldung.
 */
const OHNE_UMLEITUNG = [EINWILLIGUNG_PFAD, '/datenschutz', '/nutzungsbedingungen', '/impressum', '/login', '/einladung'];

/** Pfad ohne Query und Fragment, z. B. fuer den Vergleich mit OHNE_UMLEITUNG. */
function pfadVon(url: string): string {
  return url.split(/[?#]/)[0];
}

/**
 * Auf /einwilligung fuehren und danach an die jetzige Stelle zurueck; nicht von der
 * Seite selbst, von dem, was sie verlinkt, und von der Anmeldung aus. Eine Funktion
 * statt einer Methode, weil auch der Auth-Interceptor sie braucht und dort keinen
 * Dienst mit HttpClient holen soll.
 */
export function zurEinwilligungFuehren(router: Router): void {
  const hier = router.url ?? '/';
  const pfad = pfadVon(hier);
  if (OHNE_UMLEITUNG.some((seite) => pfad === seite || pfad.startsWith(`${seite}/`))) {
    return;
  }
  router.navigate([EINWILLIGUNG_PFAD], { queryParams: { returnUrl: hier } });
}

/**
 * Die Art.-9-Einwilligung (#489): Stand lesen, einwilligen, widerrufen.
 *
 * Nach dem Anmelden fragt ``starten`` einmal je Person und App-Start nach dem Stand
 * und fuehrt ohne Einwilligung auf /einwilligung. Wer dort ohne Einwilligung
 * weitergeht, wird erst beim naechsten App-Start wieder hingefuehrt; verlangt ein
 * Endpunkt sie vorher, zeigt der Auth-Interceptor einen Hinweis mit Knopf.
 */
@Injectable({ providedIn: 'root' })
export class Art9EinwilligungService implements OnDestroy {
  private readonly apiUrl = `${environment.baseUrl}/api/v1/art9-einwilligung`;
  private abo?: Subscription;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
  ) {}

  stand(): Observable<Art9EinwilligungStand> {
    return this.http.get<Art9EinwilligungStand>(this.apiUrl);
  }

  einwilligen(kennung: string): Observable<void> {
    return this.http.post<void>(this.apiUrl, { wortlaut: kennung });
  }

  widerrufen(): Observable<void> {
    return this.http.delete<void>(this.apiUrl);
  }

  /** Einmal beim App-Start aufrufen; weitere Aufrufe tun nichts. */
  starten(): void {
    if (this.abo) {
      return;
    }
    this.abo = this.authService.userInfo$
      .pipe(
        map((info) => (info?.isAuthenticated ? info.userId : null)),
        distinctUntilChanged(),
        filter((kennung): kennung is string => !!kennung),
        // Scheitert die Abfrage, nicht umleiten: Das Backend sperrt trotzdem, und der
        // Interceptor fuehrt dann hin.
        switchMap(() => this.stand().pipe(catchError(() => of(null)))),
        filter((stand): stand is Art9EinwilligungStand => !!stand && !stand.eingewilligt),
        // Laeuft gerade eine Navigation (etwa zurueck an die Stelle vor dem Anmelden),
        // erst ihr Ende abwarten, damit der Rueckweg dorthin fuehrt.
        switchMap(() => (this.router.getCurrentNavigation() ? this.navigationsEnde() : of(undefined))),
      )
      .subscribe(() => zurEinwilligungFuehren(this.router));
  }

  private navigationsEnde(): Observable<unknown> {
    return this.router.events.pipe(
      filter((e) => e instanceof NavigationEnd),
      take(1),
    );
  }

  ngOnDestroy(): void {
    this.abo?.unsubscribe();
    this.abo = undefined;
  }
}
