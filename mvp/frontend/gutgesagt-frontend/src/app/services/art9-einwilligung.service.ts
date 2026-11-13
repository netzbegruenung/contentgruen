import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Observable, Subscription, of } from 'rxjs';
import { catchError, distinctUntilChanged, filter, map, switchMap, take, tap } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { merkerEntfernen } from '../meine-beitraege/meilenstein-merker';

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

/** Laenger als das ist der erste Satz kein kurzes Label mehr; dann steht der ganze Wortlaut am Haekchen. */
export const WORTLAUT_LABEL_MAX = 300;

/**
 * Der erste Satz des Wortlauts, unveraendert, als Label am Haekchen (#620); der ganze
 * Wortlaut steht aufklappbar darunter. Ein Satz endet an ., ! oder ?, wenn danach ein
 * Grossbuchstabe oder ein Anfuehrungszeichen kommt: "Abs. 2" und "lit. a" trennen also
 * nicht. Ohne solches Satzende oder bei einem zu langen ersten Satz der ganze Text.
 */
export function wortlautErsterSatz(text: string): string {
  const ende = text.match(/[.!?](?=\s+[A-ZÄÖÜ„"])/);
  if (!ende || ende.index === undefined) {
    return text;
  }
  const satz = text.slice(0, ende.index + 1);
  return satz.length <= WORTLAUT_LABEL_MAX ? satz : text;
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
  /** Kennung der angemeldeten Person, sonst null. */
  private kennung: string | null = null;
  private readonly geklaertFuer = new BehaviorSubject<string | null>(null);
  /**
   * Kennung der angemeldeten Person, sobald feststeht, dass sie eingewilligt hat (oder
   * der Stand nicht abrufbar ist); sonst null. Bis dahin bietet die App keinen Rundgang
   * an (#587): Kein Angebot soll über oder vor der Einwilligung liegen.
   */
  readonly geklaert$ = this.geklaertFuer.asObservable();

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
  ) {}

  stand(): Observable<Art9EinwilligungStand> {
    return this.http.get<Art9EinwilligungStand>(this.apiUrl);
  }

  einwilligen(kennung: string): Observable<void> {
    return this.http.post<void>(this.apiUrl, { wortlaut: kennung }).pipe(tap(() => this.geklaertSetzen(this.kennung)));
  }

  /** Der jetzige Wert von ``geklaert$``. */
  geklaert(): string | null {
    return this.geklaertFuer.value;
  }

  private geklaertSetzen(kennung: string | null): void {
    if (this.geklaertFuer.value !== kennung) this.geklaertFuer.next(kennung);
  }

  /** Nach dem Widerruf gilt die Person nicht mehr als geklaert: kein Angebot ohne Einwilligung (#587). */
  widerrufen(): Observable<void> {
    return this.http.delete<void>(this.apiUrl).pipe(
      tap(() => {
        this.geklaertSetzen(null);
        // Ohne Einwilligung keine Meilensteine: ihr Merker im Browser geht mit (#351).
        merkerEntfernen(this.authService.getCurrentUserId());
      }),
    );
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
        tap((kennung) => {
          this.kennung = kennung;
          this.geklaertSetzen(null); // abgemeldet oder andere Person: neu klaeren
        }),
        filter((kennung): kennung is string => !!kennung),
        // Scheitert die Abfrage, nicht umleiten: Das Backend sperrt trotzdem, und der
        // Interceptor fuehrt dann hin.
        switchMap((kennung) =>
          this.stand().pipe(
            catchError(() => of(null)),
            tap((stand) => {
              if (!stand || stand.eingewilligt) this.geklaertSetzen(kennung);
              // Ohne Einwilligung keine Meilensteine: ein alter Merker in diesem Browser geht (#351).
              if (stand && !stand.eingewilligt) merkerEntfernen(kennung);
            }),
          ),
        ),
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
