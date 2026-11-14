import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, distinctUntilChanged, map, shareReplay, switchMap, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { AuthService } from '../auth/auth.service';

/** Antwort von GET /api/v1/usage/punkte/status: die Schalter, ohne Personenbezug. */
export interface PunkteStatus {
  aktiv: boolean;
  abzeichen_sichtbar: boolean;
}

/**
 * Ist der Status nicht lesbar (aelteres Backend ohne den Endpunkt, Netzfehler), fragt
 * die App die Endpunkte selbst und merkt sich deren 404 wie zuvor.
 */
const STATUS_UNBEKANNT: PunkteStatus = { aktiv: true, abzeichen_sichtbar: true };

/**
 * So lange gilt der abgefragte Schalter-Status und ein 404 auf punkte, meilensteine oder
 * abzeichen-sichtbarkeit als Schalter aus; danach fragt die App wieder.
 */
export const SCHALTER_AUS_MERKEN_MS = 15 * 60 * 1000;

function noch(seit: number | null): boolean {
  return seit !== null && Date.now() - seit < SCHALTER_AUS_MERKEN_MS;
}
import type { Fassung } from '../shared/fassung';

export interface TrackUsageRequest {
  /** Die kopierte Fassung eines Kommentars (#355); fehlt bei anderen Beitragstypen. */
  fassung?: Fassung;
}

export interface TrackUsageResponse {
  success: boolean;
  message: string;
  usage_count: number;
}

export interface ContentUsageStats {
  usage_count: number;
}

export interface UserUsageStats {
  user_id: string;
  unique_contents_contributed: number;
  total_usage_count: number;
  top_content: Array<{
    content_id: string;
    usage_count: number;
  }>;
}

/** Ein Meilenstein mit Stand (#351); siehe GLOSSARY.md „Meilenstein“. */
export interface Meilenstein {
  kennung: string;
  name: string;
  /** „wirkung“ (Nutzung, Zustimmung) oder „unterstuetzung“ (Einwürfe). */
  art: 'wirkung' | 'unterstuetzung';
  schwelle: number;
  stand: number;
  erreicht: boolean;
}

/** Der eigene Punktestand je Stufe (ADR 0004, #352); siehe GLOSSARY.md „Punkte“. */
export interface Punktestand {
  /** Kleine, je Tag gedeckelte Punkte fürs Tun. */
  tun: number;
  quests: number;
  /** Nutzung und Zustimmung durch andere: der Hauptanteil. */
  wirkung: number;
  gesamt: number;
  /** false: Startkonto oder keine geltende Art.-9-Einwilligung; dann gibt es keine Punkte. */
  sammelt: boolean;
}

/** Ergebnis von getEigenePunkte bei einem Fehler außer 404: Der Stand ist unbekannt. */
export const PUNKTE_NICHT_GELADEN = 'nicht_geladen' as const;

/** Die Antwort auf die Frage, ob andere Angemeldete die Abzeichen sehen (#351). */
export interface AbzeichenSichtbarkeit {
  gefragt: boolean;
  zeigen: boolean | null;
  /** Die Frage (text) und, aufklappbar darunter, was die Einwilligung außerdem wissen muss. */
  aktueller_wortlaut: { kennung: string; text: string; mehr_dazu: string };
}

/** Ergebnis von gepostetMelden, wenn der Server die Rückmeldung nicht (mehr) anbietet. */
export const GEPOSTET_NICHT_ANGEBOTEN = 'nicht_angeboten' as const;

/** Antwort von GET/POST /users/me/gepostet (#643). */
export interface GepostetAntwort {
  /** Verschiedene Personen, die diese Kalenderwoche „Ja, gepostet“ gemeldet haben. */
  personen_diese_woche: number;
}

export interface BesuchResponse {
  nutzung_seit_letztem_besuch: number;
  /** Einwürfe anderer seit dem zuletzt gesehenen Stand (Zählerstand, kein Zeitpunkt). */
  neue_einwuerfe?: number;
  /** Wie viele Aussagen „Hier fehlt eine Antwort“ gerade zeigt; kein Stand, nicht „neu“. */
  unbeantwortete_aussagen?: number;
  /** Die Liste hat ihre Grenze erreicht: Es können mehr warten („50+“). */
  unbeantwortete_aussagen_mehr?: boolean;
}

export interface TrendingContent {
  trending: Array<{
    content_id: string;
    recent_uses: number;
    total_uses: number;
  }>;
}

/**
 * "Diese Woche oft genutzt" (#364): Beitraege in der Form von /content/recent,
 * meistgenutzte zuerst; leer, wenn es zu wenig Nutzung gab.
 */
export interface OftGenutztAntwort {
  results: any[];
}

@Injectable({
  providedIn: 'root'
})
export class UsageTrackingService {
  private apiUrl = `${environment.baseUrl}/api/v1/usage`;

  /**
   * Wann welcher Beitrag (je Fassung) zuletzt gezaehlt wurde - gegen das
   * Doppelzaehlen eines Doppeltipps (siehe trackContentUsage).
   */
  private recentCopies = new Map<string, number>();

  /** Je Kennung, ob „Ja, gepostet“ angeboten wird, soweit schon sicher bekannt (#643). */
  private gepostetStand = new Map<string, boolean>();

  /**
   * Seit wann die Punkte am Server als ausgeschaltet gelten: ``punkte`` oder
   * ``meilensteine`` antworteten 404 (UX-Review B20). So lange fragt die App nicht, auch
   * nicht im Takt der Punkte-Anzeige; ohne Punkte gibt es auch keine Sichtbarkeit der
   * Abzeichen. Nach SCHALTER_AUS_MERKEN_MS und bei einem Wechsel der Anmeldung fragt sie
   * wieder, damit ein eingeschalteter Schalter ohne Neuladen ankommt.
   */
  private punkteAusSeit: number | null = null;
  /** ``abzeichen-sichtbarkeit`` antwortete 404 (Schalter aus); wie oben. */
  private sichtbarkeitAusSeit: number | null = null;
  /** Der Schalter-Status, einmal abgefragt und geteilt; mit dem Zeitpunkt der Abfrage. */
  private status$?: Observable<PunkteStatus>;
  private statusSeit: number | null = null;

  constructor(
    private http: HttpClient,
    private loggingService: LoggingService,
    authService: AuthService,
  ) {
    authService.userInfo$
      .pipe(
        map((info) => (info?.isAuthenticated ? info.userId : null)),
        distinctUntilChanged(),
      )
      .subscribe(() => {
        this.punkteAusSeit = null;
        this.sichtbarkeitAusSeit = null;
        this.status$ = undefined;
      });
  }

  private get punkteAus(): boolean {
    return noch(this.punkteAusSeit);
  }

  private get sichtbarkeitAus(): boolean {
    return noch(this.sichtbarkeitAusSeit);
  }

  /**
   * Ob die Punkte eingeschaltet sind (UX-Review B20, Entscheidung Maintainer 13.11.2026):
   * einmal von ``GET /punkte/status`` (ohne Anmeldung lesbar), geteilt fuer punkte,
   * meilensteine und abzeichen-sichtbarkeit. So fragt die App diese nur bei eingeschaltetem
   * Schalter und laeuft nicht auf ihr 404. Gilt SCHALTER_AUS_MERKEN_MS und bis zum
   * naechsten Wechsel der Anmeldung; ein 404 ebenso, ein anderer Fehler nicht.
   */
  punkteStatus(): Observable<PunkteStatus> {
    if (!this.status$ || !noch(this.statusSeit)) {
      this.statusSeit = Date.now();
      this.status$ = this.http.get<PunkteStatus>(`${this.apiUrl}/punkte/status`).pipe(
        catchError((error) => {
          // Ein 404 (aelteres Backend ohne den Endpunkt) gilt wie der Status selbst
          // SCHALTER_AUS_MERKEN_MS; ein anderer Fehler nicht, dann fragt der naechste Abruf.
          if (error?.status !== 404) this.status$ = undefined;
          return of(STATUS_UNBEKANNT);
        }),
        shareReplay(1),
      );
    }
    return this.status$;
  }


  /**
   * Track that a content item was used (copied).
   *
   * Gegen den Doppeltipp genuegt die Sperre von zwei Sekunden je Beitrag
   * (recentCopies). Davor lag hier zusaetzlich ein Subject mit
   * ``debounceTime(500)`` und ``distinctUntilChanged()``. Beide Operatoren haben
   * Zaehlungen verschluckt, die haetten zaehlen muessen:
   * - ``distinctUntilChanged`` vergleicht mit der zuletzt durchgelassenen ID.
   *   Wer denselben Beitrag ein zweites Mal kopierte - eine Minute oder eine
   *   Stunde spaeter -, wurde nie gezaehlt, solange dazwischen nichts anderes
   *   kopiert wurde.
   * - ``debounceTime`` haelt nur den letzten Wert: Zwei verschiedene Beitraege
   *   innerhalb einer halben Sekunde ergaben eine einzige Zaehlung.
   *
   * Die Sperre gilt je Beitrag und Fassung: Kurz und gleich danach Lang zu kopieren
   * sind zwei Kopien, kein Doppeltipp.
   *
   * @param contentId - The ID of the content item
   * @param fassung - Die kopierte Fassung eines Kommentars (#355); sonst weglassen
   * @returns Observable that completes immediately (fire-and-forget)
   */
  trackContentUsage(contentId: string, fassung?: Fassung): Observable<any> {
    // Check if this content was recently copied (within 2 seconds)
    const now = Date.now();
    const sperre = fassung ? `${contentId}:${fassung}` : contentId;
    const lastCopyTime = this.recentCopies.get(sperre);

    if (lastCopyTime && (now - lastCopyTime) < 2000) {
      // Skip duplicate copy within 2 seconds
      this.loggingService.debug(`Skipping duplicate copy tracking for ${contentId}`);
      return of({ tracked: false, reason: 'duplicate' });
    }

    // Update the last copy time
    this.recentCopies.set(sperre, now);

    // Clean up old entries (older than 5 seconds)
    this.cleanupRecentCopies();

    this.performUsageTracking(contentId, fassung);

    // Return immediately without waiting
    return of({ tracked: true, queued: true });
  }

  /**
   * Perform the actual usage tracking.
   * @private
   */
  private performUsageTracking(contentId: string, fassung?: Fassung): void {
    const url = `${this.apiUrl}/content/${contentId}/usage`;
    const body: TrackUsageRequest = fassung ? { fassung } : {};

    // Fire the request but don't wait for response
    // Using catchError to handle failures silently
    this.http.post<TrackUsageResponse>(url, body)
      .pipe(
        tap(response => {
          if (response?.success) {
            this.loggingService.info(`Usage tracked for content ${contentId}: ${response.usage_count} uses`);
          }
        }),
        catchError(error => {
          // Log error but don't propagate it (fire-and-forget)
          this.loggingService.error(`Failed to track usage for content ${contentId}`, error);
          return of(null);
        })
      )
      .subscribe(); // Execute the request
  }

  /**
   * Clean up old entries from recent copies map to prevent memory leak.
   * @private
   */
  private cleanupRecentCopies(): void {
    const now = Date.now();
    const cutoff = now - 5000; // 5 seconds

    for (const [sperre, timestamp] of this.recentCopies.entries()) {
      if (timestamp < cutoff) {
        this.recentCopies.delete(sperre);
      }
    }
  }

  /**
   * Get the usage count for a specific content item.
   *
   * @param contentId - The ID of the content item
   * @returns Observable with usage count
   */
  getContentUsage(contentId: string): Observable<ContentUsageStats> {
    const url = `${this.apiUrl}/content/${contentId}/usage`;

    return this.http.get<ContentUsageStats>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error(`Failed to get usage for content ${contentId}`, error);
          return of({ usage_count: 0 });
        })
      );
  }

  /**
   * Wie oft andere die Beitraege der angemeldeten Person genutzt haben.
   *
   * Die Kennung steht nicht im Pfad: das BFF reicht die Person aus der Anmeldung
   * weiter, und ein Pfad mit Kennung stuende in den Zugriffslogs der Webserver (#284).
   *
   * @returns Observable mit der Statistik, bei einem Fehler null
   */
  getEigeneNutzungsstatistik(): Observable<UserUsageStats | null> {
    const url = `${this.apiUrl}/users/me/usage-stats`;

    return this.http.get<UserUsageStats>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error('Eigene Nutzungsstatistik nicht geladen', error);
          return of(null);
        })
      );
  }

  /**
   * Der eigene Punktestand (#352), nur für die Person selbst. Solange die Punkte
   * ausgeschaltet sind, antwortet der Server 404, dann null: „Meine Beiträge“ zeigt
   * keine Punkte. Jeder andere Fehler (502, Zeitüberschreitung) heißt nur, dass der
   * Stand gerade unbekannt ist: PUNKTE_NICHT_GELADEN.
   */
  getEigenePunkte(): Observable<Punktestand | null | typeof PUNKTE_NICHT_GELADEN> {
    return this.punkteStatus().pipe(
      switchMap((status) =>
        !status.aktiv || this.punkteAus
          ? of(null)
          : this.http.get<Punktestand>(`${this.apiUrl}/users/me/punkte`).pipe(
              catchError((error) => {
                if (error?.status === 404) {
                  this.punkteAusSeit = Date.now();
                  return of(null);
                }
                this.loggingService.error('Eigene Punkte nicht geladen', error);
                return of(PUNKTE_NICHT_GELADEN);
              })
            )
      )
    );
  }

  /**
   * Die eigenen Meilensteine (#351), nur für die Person selbst. Solange die Punkte
   * ausgeschaltet sind, antwortet der Server 404; dann und bei jedem anderen Fehler
   * eine leere Liste, und „Meine Beiträge“ zeigt keine Meilensteine.
   */
  getEigeneMeilensteine(): Observable<Meilenstein[]> {
    return this.punkteStatus().pipe(
      switchMap((status) =>
        !status.aktiv || this.punkteAus
          ? of([])
          : this.http.get<{ meilensteine: Meilenstein[] }>(`${this.apiUrl}/users/me/meilensteine`).pipe(
              map((antwort) => antwort.meilensteine ?? []),
              catchError((error) => {
                if (error?.status === 404) {
                  this.punkteAusSeit = Date.now();
                } else {
                  this.loggingService.error('Eigene Meilensteine nicht geladen', error);
                }
                return of([]);
              })
            )
      )
    );
  }

  /**
   * Ob andere Angemeldete die eigenen Meilenstein-Abzeichen sehen (#351). Ohne die
   * Schalter antwortet der Server 404; dann und bei jedem Fehler null, und die Seite
   * fragt nicht.
   */
  getAbzeichenSichtbarkeit(): Observable<AbzeichenSichtbarkeit | null> {
    return this.punkteStatus().pipe(
      switchMap((status) =>
        !status.abzeichen_sichtbar || this.punkteAus || this.sichtbarkeitAus
          ? of(null)
          : this.http.get<AbzeichenSichtbarkeit>(`${this.apiUrl}/users/me/abzeichen-sichtbarkeit`).pipe(
              catchError((error) => {
                if (error?.status === 404) {
                  this.sichtbarkeitAusSeit = Date.now();
                } else {
                  this.loggingService.error('Sichtbarkeit der Abzeichen nicht geladen', error);
                }
                return of(null);
              })
            )
      )
    );
  }

  /**
   * Ob nach dem Kopieren „Ja, gepostet“ angeboten wird (#643): nur mit Schalter am
   * Server, angemeldet und mit Art.-9-Einwilligung (sonst 404, 401 oder 403). Ein Ja
   * und ein 404 (Schalter aus, Startkonto) gelten je Kennung bis zum Neuladen; ein 403
   * wird nicht gemerkt, die Einwilligung kann inzwischen da sein.
   */
  gepostetAngeboten(kennung: string): Observable<boolean> {
    const gemerkt = this.gepostetStand.get(kennung);
    if (gemerkt !== undefined) {
      return of(gemerkt);
    }
    return this.http.get<GepostetAntwort>(`${this.apiUrl}/users/me/gepostet`).pipe(
      map(() => true),
      tap(() => this.gepostetStand.set(kennung, true)),
      catchError((error) => {
        if (error?.status === 404) {
          this.gepostetStand.set(kennung, false);
        } else if (error?.status !== 401 && error?.status !== 403) {
          this.loggingService.error('Gepostet-Stand nicht geladen', error);
        }
        return of(false);
      }),
    );
  }

  /**
   * Ob „Ja, gepostet“ schon sicher angeboten wird; null, solange der Server nicht
   * gefragt wurde. Synchron, damit die Snackbar nach dem Kopieren sofort kommt.
   */
  gepostetBekannt(kennung: string): boolean | null {
    return this.gepostetStand.get(kennung) ?? null;
  }

  /**
   * „Ja, gepostet“ melden (#643): Der Server zählt die Person einmal je
   * Kalenderwoche. Liefert die Zahl der Personen dieser Woche, bei einem Fehler null.
   * Ein 403 (Einwilligung widerrufen) oder 404 (Schalter aus) heißt: nicht mehr
   * angeboten; dann vergisst der Dienst das gemerkte Ja und liefert NICHT_ANGEBOTEN.
   */
  gepostetMelden(kennung: string): Observable<number | null | typeof GEPOSTET_NICHT_ANGEBOTEN> {
    return this.http.post<GepostetAntwort>(`${this.apiUrl}/users/me/gepostet`, {}).pipe(
      map((antwort) => antwort.personen_diese_woche),
      catchError((error) => {
        if (error?.status === 403 || error?.status === 404) {
          this.gepostetStand.delete(kennung);
          return of(GEPOSTET_NICHT_ANGEBOTEN);
        }
        this.loggingService.error('Gepostet nicht gemeldet', error);
        return of(null);
      }),
    );
  }

  /** Ja oder Nein zur Sichtbarkeit speichern; true, wenn es geklappt hat. */
  setAbzeichenSichtbarkeit(zeigen: boolean, wortlaut: string): Observable<boolean> {
    return this.http
      .put(`${this.apiUrl}/users/me/abzeichen-sichtbarkeit`, { zeigen, wortlaut })
      .pipe(
        map(() => true),
        catchError((error) => {
          this.loggingService.error('Sichtbarkeit der Abzeichen nicht gespeichert', error);
          return of(false);
        })
      );
  }

  /**
   * Die Antwort des letzten besuchMelden dieses App-Starts; null, solange keine da ist.
   * Die Startseite zeigt sie in „Seit deinem letzten Besuch“, ohne selbst zu fragen:
   * Eine zweite Frage schriebe die gesehenen Stände fort und ergaebe 0.
   */
  readonly besuchStand$ = new BehaviorSubject<BesuchResponse | null>(null);

  /**
   * Meldet einen Besuch der angemeldeten Person und liefert, wie oft ihre Beitraege
   * seit dem letzten Besuch genutzt wurden (#349). POST, weil das Backend dabei den
   * gezeigten Stand fortschreibt; die Person kommt wie bei der Nutzungsstatistik
   * aus der Anmeldung, nicht aus dem Pfad.
   *
   * @returns Observable mit der Zahl, bei einem Fehler null
   */
  besuchMelden(): Observable<number | null> {
    // Ein neuer Besuch (auch nach einem Kontowechsel): Der alte Stand gilt nicht mehr.
    this.besuchStand$.next(null);
    return this.http.post<BesuchResponse>(`${this.apiUrl}/users/me/besuch`, {})
      .pipe(
        tap(antwort => this.besuchStand$.next(antwort)),
        map(antwort => antwort.nutzung_seit_letztem_besuch),
        catchError(error => {
          this.loggingService.error('Besuch nicht gemeldet', error);
          return of(null);
        })
      );
  }

  /**
   * Get currently trending content based on recent usage.
   *
   * @param limit - Maximum number of items to return (default: 10)
   * @returns Observable with trending content
   */
  getTrendingContent(limit: number = 10): Observable<TrendingContent> {
    const url = `${this.apiUrl}/trending?limit=${limit}`;

    return this.http.get<TrendingContent>(url)
      .pipe(
        catchError(error => {
          this.loggingService.error('Failed to get trending content', error);
          return of({ trending: [] });
        })
      );
  }

  /**
   * Die oft genutzten Beitraege der letzten sieben Tage. Ein Fehler liefert keine
   * Beitraege: Die Startseite laesst den Bereich dann weg, statt eine Fehlermeldung
   * zwischen Suche und Neuesten zu stellen.
   */
  getOftGenutzt(): Observable<OftGenutztAntwort> {
    return this.http.get<OftGenutztAntwort>(`${this.apiUrl}/trending/woche`)
      .pipe(
        catchError(error => {
          this.loggingService.error('Oft genutzte Beitraege nicht geladen', error);
          return of({ results: [] });
        })
      );
  }

  /**
   * Track usage with optimistic UI update.
   * Returns the optimistic count immediately while tracking in background.
   *
   * @param contentId - The ID of the content item
   * @param currentCount - The current usage count for optimistic update
   * @returns The optimistic new count
   */
  trackWithOptimisticUpdate(contentId: string, currentCount: number): number {
    // Fire tracking request in background
    this.trackContentUsage(contentId);

    // Return optimistic count immediately
    return currentCount + 1;
  }

  /**
   * Check if tracking is available (for offline detection).
   *
   * @returns True if online and tracking is available
   */
  isTrackingAvailable(): boolean {
    return navigator.onLine;
  }
}
