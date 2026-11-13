import { Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Observable, Subscription, fromEvent, of } from 'rxjs';
import { catchError, distinctUntilChanged, filter, map, switchMap, take, tap } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { Art9EinwilligungZustand } from './art9-einwilligung-zustand';
import { entwuerfeAufraeumen, entwuerfeLoeschen } from '../einwilligung/entwurf-vor-einwilligung';

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
  /** Wortlaut, zu dem die Person bewusst ohne Einwilligung weiterging (B2), am Konto; sonst null. */
  ohne_wortlaut?: string | null;
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
export function einwilligungFehlt(fehler: unknown): boolean {
  const f = fehler as { status?: number; error?: { detail?: unknown } | null } | null | undefined;
  return f?.status === 403 && f?.error?.detail === ART9_EINWILLIGUNG_FEHLT;
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

/** Ob ``url`` die Einwilligung selbst, eine von ihr verlinkte Seite oder die Anmeldung ist. */
export function ohneEinwilligungsUmleitung(url: string): boolean {
  const pfad = pfadVon(url);
  return OHNE_UMLEITUNG.some((seite) => pfad === seite || pfad.startsWith(`${seite}/`));
}

/**
 * Auf /einwilligung fuehren und danach an die jetzige Stelle zurueck; nicht von der
 * Seite selbst, von dem, was sie verlinkt, und von der Anmeldung aus. Eine Funktion
 * statt einer Methode, weil auch der Auth-Interceptor sie braucht und dort keinen
 * Dienst mit HttpClient holen soll.
 */
export function zurEinwilligungFuehren(router: Router): void {
  const hier = router.url ?? '/';
  if (ohneEinwilligungsUmleitung(hier)) {
    return;
  }
  router.navigate([EINWILLIGUNG_PFAD], { queryParams: { returnUrl: hier } });
}

/**
 * Frueher lag "ohne Einwilligung weiter" im localStorage unter diesem Schluessel. Seit
 * er am Konto liegt (``ohne_wortlaut`` im Stand, Entscheidung Maintainer 13.11.2026,
 * bis Paragraf 25 TDDDG geprueft ist), raeumt die App einen alten Eintrag einmal weg.
 */
export const ALTER_OHNE_SCHLUESSEL = 'gutgesagt-art9-ohne';

function alterOhneEintragWeg(): void {
  try {
    localStorage.removeItem(ALTER_OHNE_SCHLUESSEL);
  } catch {
    // Ohne Speicher gibt es auch keinen alten Eintrag.
  }
}

/**
 * Ob die App ohne Einwilligung auf /einwilligung fuehrt (UX-Review B2): nur, solange
 * die Person sich nicht entschieden hat. Wer widerrufen hat oder bewusst ohne
 * weitergegangen ist, sieht den Hinweis erst beim Beitragen. Ausnahme: Wer einem
 * frueheren Wortlaut zugestimmt hat, der nicht mehr zaehlt, wird zum neuen einmal
 * gefragt, auch wenn er zu einem noch aelteren schon ohne weitergegangen war.
 *
 * Ob sie ohne Einwilligung weiterging, sagt der Server (``ohne_wortlaut``).
 */
export function zurEinwilligungUmleiten(stand: Art9EinwilligungStand): boolean {
  const ohneBeiWortlaut = stand.ohne_wortlaut ?? null;
  if (stand.eingewilligt || stand.widerrufen_am) {
    return false;
  }
  if (ohneBeiWortlaut === null) {
    return true;
  }
  const frueherEingewilligt = !!stand.wortlaut;
  return frueherEingewilligt && ohneBeiWortlaut !== stand.aktueller_wortlaut.kennung;
}

/**
 * Die Art.-9-Einwilligung (#489): Stand lesen, einwilligen, widerrufen.
 *
 * Nach dem Anmelden fragt ``starten`` einmal je Person und App-Start nach dem Stand
 * und fuehrt beim ersten Mal ohne Einwilligung auf /einwilligung
 * (``zurEinwilligungUmleiten``). Wer dort ohne Einwilligung weitergeht oder
 * widerruft, wird nicht wieder hingefuehrt; Formulare zeigen dann einen
 * Hinweiskasten (``EinwilligungHinweisComponent``), und verlangt ein Endpunkt die
 * Einwilligung anderswo, zeigt der Auth-Interceptor einen Hinweis mit Knopf.
 */
@Injectable({ providedIn: 'root' })
export class Art9EinwilligungService implements OnDestroy {
  private readonly apiUrl = `${environment.baseUrl}/api/v1/art9-einwilligung`;
  private abo?: Subscription;
  private sichtbarAbo?: Subscription;
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
    private zustand: Art9EinwilligungZustand,
  ) {}

  stand(): Observable<Art9EinwilligungStand> {
    return this.http.get<Art9EinwilligungStand>(this.apiUrl);
  }

  einwilligen(kennung: string): Observable<void> {
    return this.http.post<void>(this.apiUrl, { wortlaut: kennung }).pipe(
      tap(() => {
        this.geklaertSetzen(this.kennung);
        this.zustand.setzen('eingewilligt');
      }),
    );
  }

  /**
   * Die Person geht bewusst ohne Einwilligung weiter: Der Server merkt sich das am
   * Konto mit dem Wortlaut, der dabei galt, und die App fuehrt beim naechsten Start
   * nicht wieder auf /einwilligung (B2). Eine Einwilligung hebt es auf.
   */
  ohneMerken(wortlaut: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/ohne`, { wortlaut });
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
        this.zustand.setzen('fehlt');
      }),
    );
  }

  /** Einmal beim App-Start aufrufen; weitere Aufrufe tun nichts. */
  starten(): void {
    if (this.abo) {
      return;
    }
    alterOhneEintragWeg();
    this.sichtbarkeitBeobachten();
    this.abo = this.authService.userInfo$
      .pipe(
        map((info) => (info?.isAuthenticated ? info.userId : null)),
        distinctUntilChanged(),
        tap((kennung) => {
          // Abmelden oder anderes Konto: begonnene Eingaben von vor der Einwilligung weg.
          // Nicht beim ersten Wert (null beim App-Start), sonst ginge ein Entwurf ueber ein
          // Neuladen verloren.
          // Sonst (App-Start, Anmelden): abgelaufene und die eines anderen Kontos weg,
          // auch nach einem Neuladen, das die vorige Kennung nicht mehr kennt.
          if (this.kennung !== null && this.kennung !== kennung) entwuerfeLoeschen();
          else entwuerfeAufraeumen(kennung);
          this.kennung = kennung;
          this.zustand.kennung = kennung;
          this.geklaertSetzen(null); // abgemeldet oder andere Person: neu klaeren
          this.zustand.setzen('unbekannt');
        }),
        filter((kennung): kennung is string => !!kennung),
        // Scheitert die Abfrage, nicht umleiten: Das Backend sperrt trotzdem, und der
        // Interceptor fuehrt dann hin.
        switchMap((kennung) =>
          this.stand().pipe(
            catchError(() => of(null)),
            tap((stand) => {
              if (!stand || stand.eingewilligt) this.geklaertSetzen(kennung);
              if (stand) this.zustand.setzen(stand.eingewilligt ? 'eingewilligt' : 'fehlt');
            }),
            map((stand) => !!stand && zurEinwilligungUmleiten(stand)),
          ),
        ),
        filter((umleiten) => umleiten),
        // Laeuft gerade eine Navigation (etwa zurueck an die Stelle vor dem Anmelden),
        // erst ihr Ende abwarten, damit der Rueckweg dorthin fuehrt.
        switchMap(() => (this.router.getCurrentNavigation() ? this.navigationsEnde() : of(undefined))),
      )
      .subscribe(() => zurEinwilligungFuehren(this.router));
  }

  /**
   * Zurueck im Tab: den Stand neu holen, damit eine Einwilligung aus einem anderen Tab
   * hier ankommt (Hinweiskasten weg) oder ein Widerruf dort hier sperrt. Leitet nicht um.
   */
  private sichtbarkeitBeobachten(): void {
    if (typeof document === 'undefined') return;
    this.sichtbarAbo = fromEvent(document, 'visibilitychange')
      .pipe(
        filter(() => document.visibilityState === 'visible' && !!this.kennung),
        switchMap(() => this.stand().pipe(catchError(() => of(null)))),
      )
      .subscribe((stand) => {
        if (!stand) return;
        this.zustand.setzen(stand.eingewilligt ? 'eingewilligt' : 'fehlt');
        if (stand.eingewilligt) this.geklaertSetzen(this.kennung);
      });
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
    this.sichtbarAbo?.unsubscribe();
    this.sichtbarAbo = undefined;
  }
}
